"""Simulador del EVSE Monitor: habla el mismo protocolo que el firmware (docs/software/PROTOCOLO_MENSAJES.md)
para desarrollar y probar la app sin la placa.

Simula un vehículo que carga a 16 A (a la tensión nominal de la configuración), la sonda que se calienta con la
corriente, sesiones, límites, horario, PARAR, alarmas, el búfer sin internet (con «--sin-internet N») y la OTA.

Uso:
    python -m pip install -r tools/simulador/requirements.txt
    python tools/simulador/simulador.py --id evse-01 --token TOKEN                       # contra «npm run dev» (ws://localhost:8787)
    python tools/simulador/simulador.py --servidor wss://evse.ejemplo.com --id evse-01 --token TOKEN

Teclas (escribe y Enter): p = pulsar PARAR · l = mantener PARAR 3 s (soltar) · c = calentar la sonda ·
d = desconectar o conectar el vehículo · r = cortar la conexión 20 s · q = salir
"""

import argparse
import asyncio
import hashlib
import json
import math
import random
import sys
import threading
import time
import urllib.request

import websockets

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
        self.buf = []          # [(seq, registro)]
        self.seq = 0
        self.seq_srv = 0
        self.vivo = False
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
        if self.reset != "encendido" and self.reset != "software":
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

    # ---------------------------------------------------------------- mensajes
    def tel(self):
        m = self.med
        return {"t": "tel", "ts": int(time.time()), "v": round(m["v"], 2), "i": round(m["i"], 3), "p": round(m["p"]),
                "pf": m["pf"], "f": m["f"], "es": round(self.e_ses, 3), "et": round(self.e_tot, 3), "ses": self.ses,
                "sini": self.ses_ini, "dur": int(time.time() - self.ses_ini) if self.ses else 0, "pmax": round(self.p_max),
                "tsn": round(self.t_sonda, 1), "tam": round(self.t_amb, 1), "hum": 48, "k1": int(self.k1),
                "perm": int(self.permiso), "mot": self.mot, "al": sorted(self.alarmas), "nr": sorted(self.sin_rec),
                "rssi": random.randint(-68, -58), "heap": 180000, "up": int(time.time() - self.t0),
                "pend": max(0, self.seq - self.seq_srv)}

    def hola(self):
        return {"t": "hola", "fw": self.fw, "id": self.a.id, "reset": self.reset, "mac": "AA:BB:CC:00:11:22",
                "cfgv": self.cfg_v, "seq_min": self.buf[0]["s"] if self.buf else 0, "seq_max": self.seq,
                "up": int(time.time() - self.t0), "hora": int(time.time()), "ota_pend": 0}


async def ejecutar(args):
    eq = Equipo(args)
    teclas = asyncio.Queue()
    bucle = asyncio.get_running_loop()

    def leer_teclado():
        for linea in sys.stdin:
            bucle.call_soon_threadsafe(teclas.put_nowait, linea.strip().lower())

    threading.Thread(target=leer_teclado, daemon=True).start()
    cortar_hasta = time.time() + args.sin_internet
    url = args.servidor.rstrip("/") + "/api/dispositivo/ws"
    cab = {"Authorization": f"Bearer {args.id}:{args.token}"}

    async def simular():
        ult = time.time()
        while True:
            await asyncio.sleep(1)
            t = time.time()
            eq.paso(t - ult)
            ult = t
            while not teclas.empty():
                k = teclas.get_nowait()
                if k == "p":
                    if not eq.parar:
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
                    nonlocal cortar_hasta
                    cortar_hasta = time.time() + 20
                    print("  se corta la conexión 20 s")
                elif k == "q":
                    raise SystemExit

    async def conexion():
        while True:
            espera = cortar_hasta - time.time()
            if espera > 0:
                print(f"  sin internet {espera:.0f} s más (los registros se acumulan: {eq.seq - eq.seq_srv})")
                await asyncio.sleep(espera)
            try:
                try:
                    ws = await websockets.connect(url, additional_headers=cab, ping_interval=None)
                except TypeError:  # websockets < 14
                    ws = await websockets.connect(url, extra_headers=cab, ping_interval=None)
            except Exception as e:  # noqa: BLE001
                print(f"  no conecta ({e}); reintento en 5 s")
                await asyncio.sleep(5)
                continue
            print(f"Conectado a {url}")
            await sesion(ws)
            print("Desconectado")
            await asyncio.sleep(3)

    async def sesion(ws):
        await ws.send(json.dumps(eq.hola()))
        conocido = False
        en_vuelo = 0
        ult_tel = ult_ping = 0

        async def recibir():
            nonlocal conocido, en_vuelo
            async for txt in ws:
                if txt == "pong":
                    continue
                m = json.loads(txt)
                t = m.get("t")
                if t == "bienvenida":
                    eq.seq_srv = m.get("seq", 0)
                    eq.vivo = m.get("vivo", False)
                    conocido = True
                    if eq.reset == "ota":
                        await ws.send(json.dumps({"t": "ota", "fase": "ok", "pct": 100, "msg": "firmware confirmado", "ver": eq.fw}))
                        eq.reset = "software"
                    await ws.send(json.dumps({"t": "cfg", "v": eq.cfg_v, "c": eq.cfg}))
                    await ws.send(json.dumps(eq.tel()))
                elif t == "regack":
                    eq.seq_srv = max(eq.seq_srv, m.get("hasta", 0))
                    en_vuelo = 0
                elif t == "vivo":
                    eq.vivo = m.get("on", False)
                    print(f"  app {'abierta' if eq.vivo else 'cerrada'}: telemetría cada {2 if eq.vivo else eq.cfg['tel_s']} s")
                elif t == "cfg":
                    eq.cfg.update(m.get("c", {}))
                    eq.cfg_v = m.get("v", eq.cfg_v)
                    eq.evento("config", 0, eq.cfg_v)
                    print(f"  configuración v{eq.cfg_v}: {json.dumps(eq.cfg)}")
                    await ws.send(json.dumps({"t": "cfg", "v": eq.cfg_v, "c": eq.cfg}))
                elif t == "orden":
                    await orden(ws, m)

        async def orden(ws, m):
            o, oid, a = m.get("o"), m.get("id"), m.get("a") or {}
            print(f"  orden: {o} {a or ''}")
            ok, msg, datos = True, "", None
            if o == "permitir":
                eq.permiso, eq.limite, eq.mot = True, False, ""
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
                await ws.send(json.dumps(eq.tel()))
                msg = "estado enviado"
            elif o == "cal_leer":
                datos = {"calibrada": False, "ugain": 0x6720, "igain_n": 0x7530, "uoffset": 0, "ioffset_n": 0, "poffset_n": 0,
                         "qoffset_n": 0, "ngain": 0, "nphi": 0, "plconst_h": 0x15, "plconst_l": 0xD174, "pstart": 0x08BD,
                         "mmode": 0x9022, "chip": {"sysstatus": "0000", "calstart": "8765", "adjstart": "8765"},
                         "v": eq.med["v"], "i": eq.med["i"], "p": eq.med["p"], "pf": eq.med["pf"]}
                msg = "calibración actual (simulada)"
            elif o in ("cal_auto", "cal_escribir", "cal_fabrica"):
                msg = "calibración simulada aplicada"
            elif o == "reiniciar":
                await ws.send(json.dumps({"t": "ack", "id": oid, "ok": True, "msg": "reiniciando"}))
                await reiniciar(ws, "software")
                return
            elif o == "ota":
                await ws.send(json.dumps({"t": "ack", "id": oid, "ok": True, "msg": "descargando el firmware"}))
                await ota(ws, a)
                return
            else:
                ok, msg = False, "orden desconocida"
            r = {"t": "ack", "id": oid, "ok": ok, "msg": msg}
            if datos:
                r["datos"] = datos
            await ws.send(json.dumps(r))
            await ws.send(json.dumps(eq.tel()))

        async def ota(ws, a):
            base = args.servidor.replace("ws://", "http://").replace("wss://", "https://").rstrip("/")
            req = urllib.request.Request(f"{base}/api/dispositivo/firmware/{a['ver']}", headers=cab)
            try:
                datos = await asyncio.to_thread(lambda: urllib.request.urlopen(req, timeout=30).read())
            except Exception as e:  # noqa: BLE001
                await ws.send(json.dumps({"t": "ota", "fase": "error", "pct": 0, "msg": str(e), "ver": a["ver"]}))
                return
            for pct in (25, 50, 75, 100):
                await ws.send(json.dumps({"t": "ota", "fase": "descargando", "pct": pct, "msg": "", "ver": a["ver"]}))
                await asyncio.sleep(0.3)
            sha = hashlib.sha256(datos).hexdigest()
            if a.get("sha") and sha != a["sha"]:
                await ws.send(json.dumps({"t": "ota", "fase": "error", "pct": 0, "msg": "SHA-256 no coincide", "ver": a["ver"]}))
                return
            await ws.send(json.dumps({"t": "ota", "fase": "listo", "pct": 100, "msg": "reiniciando con el firmware nuevo", "ver": a["ver"]}))
            eq.fw = a["ver"]
            await reiniciar(ws, "ota")

        async def reiniciar(ws, motivo):
            print(f"  reinicio ({motivo})")
            eq.reset = motivo
            eq.t0 = time.time()
            eq.k1, eq.mot = False, "arranque"
            eq.evento("k1", 0, 0, 0)
            eq.evento("arranque", 0, 3, 0)
            await ws.close()

        rx = asyncio.create_task(recibir())
        try:
            while not rx.done():
                await asyncio.sleep(0.5)
                if time.time() < cortar_hasta:
                    await ws.close()
                    break
                t = time.time()
                if t - ult_ping >= 30:
                    ult_ping = t
                    await ws.send("ping")
                periodo = 2 if eq.vivo else eq.cfg["tel_s"]
                if conocido and t - ult_tel >= periodo:
                    ult_tel = t
                    await ws.send(json.dumps(eq.tel()))
                if conocido and not en_vuelo and eq.seq > eq.seq_srv:
                    lote = [r for r in eq.buf if r["s"] > eq.seq_srv][:20]
                    if lote:
                        en_vuelo = lote[-1]["s"]
                        await ws.send(json.dumps({"t": "reg", "r": lote, "hasta": en_vuelo}))
        except websockets.ConnectionClosed:
            pass
        finally:
            rx.cancel()

    await asyncio.gather(simular(), conexion())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--servidor", default="ws://localhost:8787", help="ws://localhost:8787 o wss://tu-dominio")
    p.add_argument("--id", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--rapido", type=float, default=1.0, help="acelera la energía y los tiempos de la sesión (p. ej. 60)")
    p.add_argument("--bateria", type=float, default=20.0, help="kWh que necesita el vehículo para llenarse")
    p.add_argument("--sin-internet", type=float, default=0, help="arranca sin conexión durante N s (prueba el búfer)")
    args = p.parse_args()
    try:
        asyncio.run(ejecutar(args))
    except (KeyboardInterrupt, SystemExit):
        print("Fin del simulador.")


if __name__ == "__main__":
    main()
