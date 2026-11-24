"""Simulador del EVSE Monitor: habla con Firebase igual que el firmware (docs/software/PROTOCOLO_MENSAJES.md)
para desarrollar y probar la app sin la placa.

Simula un vehículo que carga a 16 A (a la tensión nominal de la configuración), la sonda que se calienta con la
corriente, sesiones, límites, horario, PARAR, alarmas, el búfer sin internet (con «--sin-internet N») y la OTA.

Uso:
    python -m pip install -r tools/simulador/requirements.txt
    python tools/simulador/simulador.py --enlace "EVSE1.…"          # el código sale en la app (Ajustes → Enlace)

Con el emulador de Firebase («npm run emular» en app/) el código de enlace trae la dirección del emulador y el
simulador lo reconoce solo.

Teclas (escribe y Enter): p = pulsar PARAR · l = mantener PARAR 3 s (soltar) · c = calentar la sonda ·
d = desconectar o conectar el vehículo · r = cortar la conexión 20 s · q = salir
"""

import argparse
import base64
import hashlib
import json
import math
import queue
import random
import sys
import threading
import time
import urllib.parse

import requests

FW = "1.0.0-sim"
ALARMAS = ["temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar", "amb_falla", "sin_hora",
           "reinicio", "sin_calibrar", "temp_aviso"]
TEXTOS = {
    "temp_sonda": "Sobretemperatura en la sonda", "temp_amb": "Sobretemperatura en la placa",
    "sonda_falla": "Sonda DS18B20 sin respuesta", "medidor_falla": "Falla del medidor ATM90E26",
    "red_baja": "Tensión de red baja", "parar": "PARAR pulsado", "amb_falla": "Sensor de ambiente sin respuesta",
    "sin_hora": "Sin hora (sin NTP ni RTC)", "reinicio": "Reinicio inesperado", "sin_calibrar": "Medidor sin calibrar",
    "temp_aviso": "Sonda cerca del límite de temperatura",
}
GRAVES = {"temp_sonda", "temp_amb", "sonda_falla", "medidor_falla", "red_baja", "parar", "reinicio"}
CONFIG = {"vnom": 240, "tarifa": 900, "tz": -300, "tmax_sonda": 60, "tmax_amb": 60, "t_hist": 10, "sonda_req": True,
          "arranque": "restaurar", "lim_kwh": 0, "lim_min": 0, "lim_cop": 0, "horario": {"on": False, "v": []},
          "i_inicio": 1, "fin_min": 10, "inv_ct": False, "tel_s": 15, "reg_carga_s": 30, "reg_reposo_s": 300}
ORDEN_VENCE_S = 120
MIRANDO_S = 45


def leer_enlace(codigo):
    codigo = codigo.strip()
    if not codigo.startswith("EVSE1."):
        raise SystemExit("El código de enlace empieza por «EVSE1.»: cópialo completo desde la app.")
    b = codigo[6:].replace("-", "+").replace("_", "/")
    b += "=" * (-len(b) % 4)
    d = json.loads(base64.b64decode(b))
    return d["d"].rstrip("/"), d["k"], d["e"], d["c"]


class Firebase:
    """Lo mismo que src/fb.cpp: inicio de sesión, REST y flujo (Server-Sent Events)."""

    def __init__(self, db, apikey, correo, clave, auth_emulador):
        u = urllib.parse.urlsplit(db)
        self.base = f"{u.scheme}://{u.netloc}"
        self.ns = urllib.parse.parse_qs(u.query).get("ns", [None])[0]
        local = u.hostname in ("127.0.0.1", "localhost")
        self.login_url = (f"http://{auth_emulador}/identitytoolkit.googleapis.com" if local else
                          "https://identitytoolkit.googleapis.com") + f"/v1/accounts:signInWithPassword?key={apikey}"
        self.correo, self.clave = correo, clave
        self.token, self.uid, self.vence = None, None, 0
        self.s = requests.Session()

    def entrar(self):
        r = requests.post(self.login_url, json={"email": self.correo, "password": self.clave, "returnSecureToken": True},
                          timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"inicio de sesión: {r.json().get('error', {}).get('message', r.status_code)}")
        d = r.json()
        self.token, self.uid = d["idToken"], d["localId"]
        self.vence = time.time() + int(d.get("expiresIn", 3600)) - 300

    def con_sesion(self):
        return self.token and time.time() < self.vence

    def url(self, ruta):
        q = {"auth": self.token}
        if self.ns:
            q["ns"] = self.ns
        return f"{self.base}/{ruta}.json?{urllib.parse.urlencode(q)}"

    def pedir(self, metodo, ruta, cuerpo=None, espera=15):
        r = self.s.request(metodo, self.url(ruta), data=None if cuerpo is None else json.dumps(cuerpo), timeout=espera)
        if r.status_code == 401:
            self.token = None
        if r.status_code != 200:
            raise RuntimeError(f"{metodo} /{ruta}: HTTP {r.status_code} {r.text[:120]}")
        return r.json()

    def flujo(self, ruta, cola, parar):
        """Hilo: deja en `cola` los eventos («put»/«patch», datos) hasta que `parar` se activa o se corta."""
        try:
            with requests.get(self.url(ruta), headers={"Accept": "text/event-stream"}, stream=True,
                              timeout=(10, 90)) as r:
                if r.status_code != 200:
                    cola.put(("error", f"flujo: HTTP {r.status_code}"))
                    return
                tipo, datos = None, ""
                for linea in r.iter_lines(chunk_size=1, decode_unicode=True):  # sin búfer: cada evento llega al instante
                    if parar.is_set():
                        return
                    if linea is None:
                        continue
                    if linea == "":
                        if tipo in ("put", "patch"):
                            cola.put((tipo, json.loads(datos)))
                        elif tipo in ("auth_revoked", "cancel"):
                            cola.put(("error", f"flujo: {tipo}"))
                            return
                        tipo, datos = None, ""
                    elif linea.startswith("event:"):
                        tipo = linea[6:].strip()
                    elif linea.startswith("data:"):
                        datos += linea[5:].lstrip()
        except Exception as e:  # noqa: BLE001
            cola.put(("error", f"flujo: {e}"))
        cola.put(("error", "flujo: se cerró"))


class Equipo:
    def __init__(self, args):
        self.a = args
        self.cfg = dict(CONFIG)
        self.cfg_v = 0
        self.permiso = True
        self.parar = False
        self.limite = False
        self.k1 = False
        self.mot = "arranque"
        self.t0 = time.time()
        self.vehiculo = True
        self.calentar = False
        self.t_sonda = 26.0
        self.t_amb = 29.0
        self.trip = False
        self.frio_desde = None
        self.alarmas = set()
        self.sin_rec = set()
        self.e_tot = 1234.5
        self.ses = 0
        self.ses_cont = 0
        self.ses_ini = 0
        self.e_ses = 0.0
        self.p_max = 0.0
        self.ultima_i = time.time()
        self.i_desde = None
        self.med = {"v": 0, "i": 0, "p": 0, "pf": 1, "f": 60}
        self.buf = []          # registros del «búfer de la flash»
        self.seq = 0
        self.seq_srv = 0
        self.fw = FW
        self.reset = "encendido"
        self.ult_reg = 0
        self.evento("arranque", 0, 1, 0)

    # ---------------------------------------------------------------- búfer
    def registro(self, r):
        self.seq += 1
        r = {"s": self.seq, "ts": int(time.time()), "k1": int(self.k1), "mot": self.mot, **r}
        self.buf.append(r)
        if len(self.buf) > 100000:
            self.buf.pop(0)

    def evento(self, c, n, val, x=0, alarma=None):
        r = {"k": "e", "c": c, "n": n, "val": val, "x": x}
        if alarma:
            r["a"] = alarma
            r["txt"] = TEXTOS[alarma]
        self.registro(r)
        print(f"  [evento] {c} {alarma or ''} {val}")

    def muestra(self):
        m = self.med
        self.registro({"k": "m", "v": round(m["v"], 2), "i": round(m["i"], 3), "p": round(m["p"]), "pf": m["pf"],
                       "f": m["f"], "es": round(self.e_ses, 3), "et": round(self.e_tot, 3),
                       "tsn": round(self.t_sonda, 1), "tam": round(self.t_amb, 1), "hum": 48})

    # ---------------------------------------------------------------- un segundo de simulación
    def paso(self, dt):
        ahora = time.time()
        vnom = self.cfg["vnom"]
        v = vnom * (1 + 0.01 * math.sin(ahora / 37)) + random.uniform(-0.3, 0.3)
        lleno = self.ses and self.e_ses >= self.a.bateria
        i = (16 + random.uniform(-0.2, 0.2)) if (self.k1 and self.vehiculo and not lleno) else 0.0
        pf = 0.99 if i else 1.0
        p = v * i * pf
        self.med = {"v": v, "i": i, "p": p, "pf": pf, "f": round(60 + random.uniform(-0.03, 0.03), 2)}
        kwh = p * dt * self.a.rapido / 3.6e6
        self.e_tot += kwh
        if self.ses:
            self.e_ses += kwh
            self.p_max = max(self.p_max, p)
        # temperatura de la sonda: sube con la corriente (más rápido con «c»)
        objetivo = 26 + (i / 16) * (40 if self.calentar else 12)
        self.t_sonda += (objetivo - self.t_sonda) * min(1, dt * (0.08 if self.calentar else 0.01))
        self.t_amb += ((29 + i / 8) - self.t_amb) * min(1, dt * 0.01)

        # sesión
        if i >= 0.3:
            self.ultima_i = ahora
        if not self.ses:
            if self.k1 and i >= self.cfg["i_inicio"]:
                self.i_desde = self.i_desde or ahora
                if ahora - self.i_desde >= 10:
                    self.ses_cont += 1
                    self.ses, self.ses_ini, self.e_ses, self.p_max = self.ses_cont, int(ahora), 0.0, 0.0
                    self.evento("sesion_inicio", 0, self.ses)
            else:
                self.i_desde = None
        else:
            dur = ahora - self.ses_ini
            c = self.cfg
            if ahora - self.ultima_i >= c["fin_min"] * 60 / self.a.rapido:
                self.cerrar("sin_corriente")
            elif c["lim_kwh"] and self.e_ses >= c["lim_kwh"]:
                self.limite_alcanzado(1)
            elif c["lim_min"] and dur * self.a.rapido >= c["lim_min"] * 60:
                self.limite_alcanzado(2)
            elif c["lim_cop"] and self.e_ses * c["tarifa"] >= c["lim_cop"]:
                self.limite_alcanzado(3)

        # protecciones (como en src/control.cpp)
        c = self.cfg
        if self.t_sonda >= c["tmax_sonda"]:
            self.trip, self.frio_desde = True, None
        elif self.trip:
            if self.t_sonda <= c["tmax_sonda"] - c["t_hist"]:
                self.frio_desde = self.frio_desde or ahora
                if ahora - self.frio_desde >= 300 / self.a.rapido:
                    self.trip = False
            else:
                self.frio_desde = None
        al = set()
        if self.trip:
            al.add("temp_sonda")
        if self.parar:
            al.add("parar")
        if not self.trip and self.t_sonda >= c["tmax_sonda"] - 10:
            al.add("temp_aviso")
        if self.reset not in ("encendido", "software", "ota"):
            al.add("reinicio")
        for a in al - self.alarmas:
            self.evento("alarma", 2 if a in GRAVES else 1, ALARMAS.index(a), int(self.t_sonda * 10), alarma=a)
            if a in GRAVES:
                self.sin_rec.add(a)
        for a in self.alarmas - al:
            self.evento("alarma_fin", 0, ALARMAS.index(a), alarma=a)
        self.alarmas = al

        arrancado = ahora - self.t0 >= 10 and not (c["arranque"] == "detenida" and self.mot == "arranque")
        if self.trip:
            mot = "temperatura"
        elif self.parar:
            mot = "parar"
        elif self.limite:
            mot = "limite"
        elif not self.en_horario():
            mot = "horario"
        elif not arrancado:
            mot = "arranque"
        elif not self.permiso:
            mot = "app"
        else:
            mot = ""
        k1 = mot == ""
        cambio = k1 != self.k1
        self.mot = mot
        if cambio:
            self.k1 = k1
            self.evento("k1", 0, int(k1), 0)
            self.muestra()

        periodo = c["reg_carga_s"] if (self.ses or i >= c["i_inicio"]) else c["reg_reposo_s"]
        if ahora - self.ult_reg >= periodo:
            self.ult_reg = ahora
            self.muestra()

    def en_horario(self):
        h = self.cfg["horario"]
        if not h.get("on") or not h.get("v"):
            return True
        local = time.time() + self.cfg["tz"] * 60
        dow = int((local // 86400 + 4) % 7)
        minuto = int((local % 86400) // 60)
        for w in h["v"]:
            ini = int(w["i"][:2]) * 60 + int(w["i"][3:])
            fin = int(w["f"][:2]) * 60 + int(w["f"][3:])
            if ini < fin:
                if w["d"] >> dow & 1 and ini <= minuto < fin:
                    return True
            else:
                if w["d"] >> dow & 1 and minuto >= ini:
                    return True
                if w["d"] >> ((dow + 6) % 7) & 1 and minuto < fin:
                    return True
        return False

    def cerrar(self, mf):
        self.registro({"k": "s", "num": self.ses, "ini": self.ses_ini, "fin": int(time.time()), "kwh": round(self.e_ses, 3),
                       "pmax": round(self.p_max), "mf": mf})
        print(f"  [sesión] cerrada nº {self.ses}: {self.e_ses:.3f} kWh ({mf})")
        self.ses, self.e_ses, self.p_max = 0, 0.0, 0.0

    def limite_alcanzado(self, tipo):
        self.limite = True
        self.evento("limite", 0, tipo)
        self.cerrar("limite")

    # ---------------------------------------------------------------- lo que sube a Firebase
    def estado(self, vivo, ota):
        m = self.med
        e = {"ts": {".sv": "timestamp"}, "hora": int(time.time()), "v": round(m["v"], 2), "i": round(m["i"], 3),
             "p": round(m["p"]), "pf": m["pf"], "f": m["f"], "es": round(self.e_ses, 3), "et": round(self.e_tot, 3),
             "ses": self.ses, "sini": self.ses_ini, "dur": int(time.time() - self.ses_ini) if self.ses else 0,
             "pmax": round(self.p_max), "tsn": round(self.t_sonda, 1), "tam": round(self.t_amb, 1), "hum": 48,
             "k1": int(self.k1), "perm": int(self.permiso), "mot": self.mot, "al": sorted(self.alarmas),
             "nr": sorted(self.sin_rec), "rssi": random.randint(-68, -58), "heap": 180000,
             "up": int(time.time() - self.t0), "pend": max(0, self.seq - self.seq_srv), "cfg_v": self.cfg_v,
             "cal": False, "fw": self.fw, "mac": "AA:BB:CC:00:11:22", "ip": "192.168.1.50", "reset": self.reset,
             "vivo": int(vivo)}
        if ota:
            e["ota"] = ota
        return e

    def config_json(self):
        return {**self.cfg, "v": self.cfg_v, "por": "equipo"}


def mapear(eq_id, r, tarifa):
    """Registro del búfer → (ruta, objeto), igual que llenar() en src/red.cpp."""
    base = {"k1": r["k1"], "mot": r["mot"]}
    ts = r["ts"]
    if r["k"] == "m":
        o = {k: r[k] for k in ("v", "i", "p", "pf", "f", "es", "et", "tsn", "tam", "hum")}
        return f"mediciones/{eq_id}/{ts}", {**o, **base}
    if r["k"] == "e":
        o = {"ts": ts, "c": r["c"], "n": r["n"], "val": r["val"], "x": r["x"]}
        if r.get("a"):
            o["a"], o["txt"] = r["a"], r["txt"]
        return f"eventos/{eq_id}/{ts:010d}-{r['s'] % 1000000:06d}", {**o, **base}
    o = {"num": r["num"], "ini": r["ini"], "fin": r["fin"], "kwh": r["kwh"], "pmax": r["pmax"], "mf": r["mf"],
         "cop": round(r["kwh"] * tarifa)}
    return f"sesiones/{eq_id}/{r['ini'] or r['num']}", {**o, **base}


class Red:
    def __init__(self, eq, fb, args):
        self.eq, self.fb, self.a = eq, fb, args
        self.id = None
        self.nombre = ""
        self.enlinea = False
        self.cola = queue.Queue()
        self.parar_flujo = threading.Event()
        self.vivo_hasta = 0
        self.ult_tel = 0
        self.pend = []
        self.hechas = []
        self.cfg_subir = False
        self.ota_pedida = None
        self.ota = None          # estado de la OTA para /estado
        self.ota_borrar = False
        self.tg = None
        self.cortar_hasta = time.time() + args.sin_internet
        self.prox_intento = 0

    def vivo(self):
        return time.time() < self.vivo_hasta

    # ---------------------------------------------------------------- conexión
    def conectar(self):
        if not self.fb.con_sesion():
            self.fb.entrar()
            print(f"  sesión iniciada ({self.fb.correo})")
        if not self.id:
            self.id = self.fb.pedir("GET", f"dispositivos/{self.fb.uid}")
            if not isinstance(self.id, str):
                raise RuntimeError("esta cuenta no está asignada a ningún equipo")
            self.nombre = self.fb.pedir("GET", f"equipos/{self.id}/nombre") or ""
        s = self.fb.pedir("GET", f"subido/{self.id}") or 0
        self.eq.seq_srv = min(s, self.eq.seq)
        self.parar_flujo = threading.Event()
        self.cola = queue.Queue()
        threading.Thread(target=self.fb.flujo, args=(f"entrada/{self.id}", self.cola, self.parar_flujo),
                         daemon=True).start()
        self.enlinea = True
        self.ult_tel = 0
        print(f"En línea: equipo «{self.id}» ({self.nombre})")
        if self.eq.reset == "ota":
            self.ota = {"fase": "ok", "pct": 100, "msg": f"firmware {self.eq.fw} instalado y confirmado", "ver": self.eq.fw}

    def desconectar(self, motivo):
        self.parar_flujo.set()
        if self.enlinea:
            print(f"Desconectado: {motivo}")
        self.enlinea = False
        self.vivo_hasta = 0
        self.prox_intento = time.time() + 3

    # ---------------------------------------------------------------- flujo de /entrada/{id}
    def tocar(self, ruta, v):
        if ruta in ("/", ""):
            if not isinstance(v, dict):
                self.cfg_subir, self.tg, self.ota_pedida = True, None, None
                return
            if v.get("config") is None:
                self.cfg_subir = True
            if v.get("telegram") is None:
                self.tg = None
            for k, x in v.items():
                self.tocar("/" + k, x)
            return
        partes = ruta.strip("/").split("/")
        primero, resto = partes[0], partes[1:]
        if primero == "config":
            self.remota_config(v if not resto else self.fb.pedir("GET", f"entrada/{self.id}/config"))
        elif primero == "ordenes":
            if not resto and isinstance(v, dict):
                for k, x in v.items():
                    self.encolar(k, x)
            elif len(resto) == 1:
                self.encolar(resto[0], v)
        elif primero == "mirando":
            ms = v or 0
            edad = time.time() * 1000 - ms
            if ms and edad <= MIRANDO_S * 1000:
                if not self.vivo():
                    self.ult_tel = 0
                    print("  la app está abierta: telemetría cada 2 s")
                self.vivo_hasta = time.time() + MIRANDO_S - max(0, edad) / 1000
        elif primero == "ota":
            self.ota_evaluar(v if not resto else self.fb.pedir("GET", f"entrada/{self.id}/ota"))
        elif primero == "telegram":
            self.tg = v if not resto else self.fb.pedir("GET", f"entrada/{self.id}/telegram")

    def manejar(self, tipo, d):
        ruta, data = d.get("path", "/"), d.get("data")
        if tipo == "put":
            self.tocar(ruta, data)
        elif tipo == "patch" and isinstance(data, dict):
            for k, x in data.items():
                self.tocar(("" if ruta == "/" else ruta) + "/" + k, x)

    def remota_config(self, c):
        if not isinstance(c, dict):
            self.cfg_subir = True
            return
        v = c.get("v", 0)
        if v > self.eq.cfg_v:
            for k in CONFIG:
                if k in c:
                    self.eq.cfg[k] = c[k]
            if not isinstance(self.eq.cfg.get("horario"), dict):
                self.eq.cfg["horario"] = {"on": False, "v": []}
            self.eq.cfg["horario"].setdefault("v", [])
            self.eq.cfg_v = v
            self.eq.evento("config", 0, v)
            print(f"  configuración v{v} aplicada")
            self.cfg_subir = True
        elif v < self.eq.cfg_v:
            self.cfg_subir = True

    def encolar(self, oid, o):
        if not isinstance(o, dict) or oid in self.hechas or any(p[0] == oid for p in self.pend):
            return
        self.pend.append((oid, o))

    def ota_evaluar(self, v):
        if not isinstance(v, dict) or not v.get("ver"):
            self.ota_pedida = None
            return
        if v["ver"] == self.eq.fw:
            self.ota_borrar = True
            if not self.ota or self.ota.get("fase") != "ok":
                self.ota = {"fase": "ok", "pct": 100, "msg": f"versión {v['ver']} instalada", "ver": v["ver"]}
            return
        if not self.ota_pedida:
            self.ota_pedida = v

    # ---------------------------------------------------------------- órdenes
    def responder(self, oid, ok, msg, datos=None):
        r = {"ok": ok, "msg": msg, "ts": {".sv": "timestamp"}}
        if datos:
            r["datos"] = datos
        self.fb.pedir("PUT", f"respuestas/{self.id}/{oid}", r)
        self.fb.pedir("DELETE", f"entrada/{self.id}/ordenes/{oid}")
        print(f"  [orden] {'bien' if ok else 'NO'}: {msg}")

    def ejecutar(self, oid, m):
        eq = self.eq
        self.hechas = (self.hechas + [oid])[-16:]
        o, a, ts = m.get("o"), m.get("a") or {}, m.get("ts", 0)
        print(f"  orden: {o} {a or ''}")
        if ts and abs(time.time() * 1000 - ts) > ORDEN_VENCE_S * 1000:
            return self.responder(oid, False, "orden vencida: llegó al equipo más de 2 min después")
        datos = None
        if o == "permitir":
            eq.permiso, eq.limite = True, False
            msg = "permitida, pero PARAR sigue enclavado" if eq.parar else "carga permitida"
        elif o == "detener":
            eq.permiso, msg = False, "carga detenida"
        elif o == "reconocer":
            eq.sin_rec.clear()
            eq.reset = "encendido"
            msg = "alarmas reconocidas"
        elif o == "soltar_parar":
            eq.parar = False
            eq.evento("orden_local", 0, 3)
            msg = "PARAR liberado"
        elif o == "estado":
            msg = "estado enviado"
        elif o == "cal_leer":
            datos = {"calibrada": False, "ugain": 0x6720, "igain_n": 0x7530, "uoffset": 0, "ioffset_n": 0, "poffset_n": 0,
                     "qoffset_n": 0, "ngain": 0, "nphi": 0, "plconst_h": 0x15, "plconst_l": 0xD174, "pstart": 0x08BD,
                     "mmode": 0x9022, "chip": {"sysstatus": "0000", "calstart": "8765", "adjstart": "8765"},
                     "v": eq.med["v"], "i": eq.med["i"], "p": eq.med["p"], "pf": eq.med["pf"]}
            msg = "calibración actual (simulada)"
        elif o in ("cal_auto", "cal_escribir", "cal_fabrica"):
            msg = "calibración simulada aplicada"
        elif o == "telegram_probar":
            ok = bool(self.tg and self.tg.get("token") and self.tg.get("chat"))
            return self.responder(oid, ok, "mensaje simulado (el simulador no escribe a Telegram)" if ok
                                  else "falta el token o el chat de Telegram")
        elif o == "reiniciar":
            self.responder(oid, True, "reiniciando")
            return self.reiniciar("software")
        else:
            return self.responder(oid, False, f"orden desconocida: {o}")
        self.responder(oid, True, msg, datos)
        self.ult_tel = 0

    def reiniciar(self, motivo):
        print(f"  reinicio ({motivo})")
        eq = self.eq
        eq.reset = motivo
        eq.t0 = time.time()
        eq.k1, eq.mot = False, "arranque"
        eq.evento("k1", 0, 0, 0)
        eq.evento("arranque", 0, 3, 0)
        self.desconectar("reinicio")

    def hacer_ota(self):
        v, self.ota_pedida = self.ota_pedida, None
        eq = self.eq

        def informe(fase, pct, msg=""):
            self.ota = {"fase": fase, "pct": pct, "msg": msg, "ver": v["ver"]}
            self.fb.pedir("PUT", f"estado/{self.id}/ota", self.ota)
            print(f"  [ota] {fase} {pct}% {msg}")

        if eq.k1 and eq.med["i"] >= eq.cfg["i_inicio"]:
            informe("error", 0, "hay una carga en curso: detenla o espera a que termine")
            self.ota_borrar = True
            return
        datos = b""
        informe("descargando", 0)
        for n in range(v["partes"]):
            parte = base64.b64decode(self.fb.pedir("GET", f"firmware/{v['clave']}/partes/{n}", espera=30))
            datos += parte
            pct = len(datos) * 100 // v["tam"]
            if n % max(1, v["partes"] // 4) == 0:
                informe("descargando", pct)
        if len(datos) != v["tam"] or hashlib.sha256(datos).hexdigest() != v["sha"].lower():
            informe("error", 0, "SHA-256 no coincide" if len(datos) == v["tam"] else "tamaño inesperado")
            self.ota_borrar = True
            return
        informe("listo", 100, "reiniciando con el firmware nuevo")
        eq.fw = v["ver"]
        self.reiniciar("ota")

    # ---------------------------------------------------------------- trabajo en línea
    def trabajar(self):
        fb, eq = self.fb, self.eq
        while not self.cola.empty():
            tipo, d = self.cola.get_nowait()
            if tipo == "error":
                return self.desconectar(d)
            self.manejar(tipo, d)
        if self.cfg_subir:
            fb.pedir("PUT", f"entrada/{self.id}/config", eq.config_json())
            self.cfg_subir = False
        if self.ota_borrar:
            fb.pedir("DELETE", f"entrada/{self.id}/ota")
            self.ota_borrar = False
        if self.pend:
            self.ejecutar(*self.pend.pop(0))
            if not self.enlinea:
                return
        periodo = 2 if self.vivo() else eq.cfg["tel_s"]
        if time.time() - self.ult_tel >= periodo:
            self.ult_tel = time.time()
            fb.pedir("PUT", f"estado/{self.id}", eq.estado(self.vivo(), self.ota))
        if eq.seq > eq.seq_srv:
            lote = [r for r in eq.buf if r["s"] > eq.seq_srv][:40]
            if lote:
                d = dict(mapear(self.id, r, eq.cfg["tarifa"]) for r in lote)
                d[f"subido/{self.id}"] = lote[-1]["s"]
                fb.pedir("PATCH", "", d)
                eq.seq_srv = lote[-1]["s"]
        if self.ota_pedida:
            self.hacer_ota()

    def paso(self):
        if time.time() < self.cortar_hasta:
            if self.enlinea:
                self.desconectar("sin internet (simulado)")
            return
        try:
            if not self.enlinea:
                if time.time() < self.prox_intento:
                    return
                self.conectar()
            elif not self.fb.con_sesion():
                self.fb.entrar()
                self.desconectar("renovación del token")
                return
            self.trabajar()
        except Exception as e:  # noqa: BLE001
            print(f"  error de red: {e}; reintento en 5 s")
            self.desconectar(str(e))
            self.prox_intento = time.time() + 5


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--enlace", required=True, help="código de enlace de la app (empieza por EVSE1.)")
    p.add_argument("--auth-emulador", default="127.0.0.1:9099", help="dirección del emulador de Authentication")
    p.add_argument("--rapido", type=float, default=1.0, help="acelera la energía y los tiempos de la sesión (p. ej. 60)")
    p.add_argument("--bateria", type=float, default=20.0, help="kWh que necesita el vehículo para llenarse")
    p.add_argument("--sin-internet", type=float, default=0, help="arranca sin conexión durante N s (prueba el búfer)")
    args = p.parse_args()
    db, apikey, correo, clave = leer_enlace(args.enlace)
    fb = Firebase(db, apikey, correo, clave, args.auth_emulador)
    eq = Equipo(args)
    red = Red(eq, fb, args)
    print(f"Simulador del EVSE Monitor · {db} · {correo}")

    teclas = queue.Queue()
    threading.Thread(target=lambda: [teclas.put(l.strip().lower()) for l in sys.stdin], daemon=True).start()
    ult = time.time()
    try:
        while True:
            time.sleep(0.5)
            t = time.time()
            if t - ult >= 1:
                eq.paso(t - ult)
                ult = t
            while not teclas.empty():
                k = teclas.get_nowait()
                if k == "p" and not eq.parar:
                    eq.parar = True
                    eq.evento("orden_local", 2, 1)
                elif k == "l":
                    eq.parar = False
                    eq.evento("orden_local", 0, 2)
                elif k == "c":
                    eq.calentar = not eq.calentar
                    print(f"  sonda {'calentándose' if eq.calentar else 'normal'}")
                elif k == "d":
                    eq.vehiculo = not eq.vehiculo
                    print(f"  vehículo {'conectado' if eq.vehiculo else 'desconectado'}")
                elif k == "r":
                    red.cortar_hasta = time.time() + 20
                    print("  se corta la conexión 20 s")
                elif k == "q":
                    raise SystemExit
            red.paso()
    except (KeyboardInterrupt, SystemExit):
        print("Fin del simulador.")


if __name__ == "__main__":
    main()
