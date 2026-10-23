# -*- coding: utf-8 -*-
"""F8: carrito de compras total (PCBWay + DigiKey + Sigma) en USD y COP.

Lee las líneas de bom_f7.LINEAS (la fuente única de la BOM) y los extras de abajo, y escribe:
- docs/fabricacion/Carrito_F8.html: la página del artifact (casillas para marcar lo comprado, guardadas en el
  `db` del artifact, documento `compras/estado`);
- docs/fabricacion/CARRITO_F8.md: el mismo resumen en texto para GitHub.

Precios: PCBWay del cotizador (20 oct 2026), LCSC del 19 oct (BOM de F7), DigiKey y Sigma revisados el 22 oct.
TRM del 22 oct 2026 (dolarhoy.co).

Uso: python docs/tools/carrito_f8.py
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bom_f7  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
FAB = RAIZ / "docs" / "fabricacion"
TRM = 3191.47
FECHA = "22 de octubre de 2026"

PCBWAY = [  # id, concepto, detalle, cantidad, US$ c/u, enlace
    ("pcb", "Fabricación de la PCB", "2 capas, FR-4 1,6 mm, 1 oz, HASL sin plomo, 130 × 100 mm, vías tapadas", 5,
     36.87 / 5, "https://www.pcbway.com/orderonline.aspx"),
    ("ensamble", "Ensamble turnkey (1 placa)", "Una cara: 57 referencias, 117 SMD + 9 THT (el stencil se cotiza con el ensamble)", 1, 29.00,
     "https://www.pcbway.com/pcb-assembly.html"),
    ("componentes", "Componentes que compra PCBWay (1 placa)", "126 piezas de LCSC, detalle abajo", 1, None,
     "https://www.pcbway.com/pcb-assembly.html"),
    ("envio", "Envío DHL a Colombia", "0,5 kg: US$ 74,41 menos US$ 30 de descuento (cotización del 22 oct); en el pedido del grupo se divide", 1, 44.41,
     "https://www.pcbway.com/"),
]
ARANCEL = 0.10   # envío urgente desde China por debajo de US$ 200 (estimado; confirmar en la cotización de DHL)
DIGIKEY = [
    ("k1", "K1 · PhotoMOS AQY414EHAX (Panasonic)", "255-6089-1-ND · se suelda a mano", 1, 3.29,
     "https://www.digikey.com/en/products/result?keywords=255-6089-1-ND"),
    ("k1_repuesto", "K1 de repuesto (recomendado)", "255-6089-1-ND · por si se daña al soldar", 1, 3.29,
     "https://www.digikey.com/en/products/result?keywords=255-6089-1-ND"),
]
SIGMA = [  # id, concepto, detalle, cantidad, COP c/u, enlace
    ("ct", "CT de J3 · YHDC SCT-013-000V", "Transformador de corriente 100 A : 50 mA (20 u. en stock)", 1, 35700,
     "https://www.sigmaelectronica.net/producto/sct-013-000/"),
    ("sonda", "Sonda de J4 · DS18B20 de 2 m", "SEN DS18B20 2M (43 u. en stock)", 1, 11900,
     "https://www.sigmaelectronica.net/producto/sen-ds18b20-2m/"),
    ("pila", "Pila de BT1 · CR2032", "13 u. en stock", 1, 3213, "https://www.sigmaelectronica.net/producto/cr2032/"),
]


def lineas_pcbway():
    out = []
    for ln in bom_f7.LINEAS:
        if len(ln) < 8 or ln[5] != "PCBWay":
            continue
        des = [d.strip() for d in ln[0].split(",")]
        lcsc = ln[4].replace("LCSC ", "")
        out.append(dict(designadores=", ".join(des), fabricante=ln[1], mpn=ln[2], lcsc=lcsc, cantidad=len(des),
                        usd=ln[6], subtotal=round(ln[6] * len(des), 4),
                        enlace=f"https://www.lcsc.com/product-detail/{lcsc}.html"))
    return out


def calcular():
    comp = lineas_pcbway()
    total_comp = round(sum(c["subtotal"] for c in comp), 2)
    pcbway = []
    for i, c, d, n, u, e in PCBWAY:
        u = total_comp if u is None else u
        pcbway.append(dict(id=i, concepto=c, detalle=d, cantidad=n, usd=round(u, 4), subtotal=round(u * n, 2), enlace=e))
    base = round(sum(x["subtotal"] for x in pcbway), 2)
    arancel = round(base * ARANCEL, 2)
    pcbway.append(dict(id="arancel", concepto="Arancel de importación (estimado)",
                       detalle="10 % sobre mercancía + envío; si el valor declarado pasa de US$ 200 se suma IVA 19 %",
                       cantidad=1, usd=arancel, subtotal=arancel, enlace=""))
    digikey = [dict(id=i, concepto=c, detalle=d, cantidad=n, usd=u, subtotal=round(u * n, 2), enlace=e)
               for i, c, d, n, u, e in DIGIKEY]
    sigma = [dict(id=i, concepto=c, detalle=d, cantidad=n, cop=u, subtotal_cop=u * n,
                  subtotal=round(u * n / TRM, 2), enlace=e) for i, c, d, n, u, e in SIGMA]
    tot = dict(pcbway=round(sum(x["subtotal"] for x in pcbway), 2), digikey=round(sum(x["subtotal"] for x in digikey), 2),
               sigma_cop=sum(x["subtotal_cop"] for x in sigma))
    tot["sigma"] = round(tot["sigma_cop"] / TRM, 2)
    tot["usd"] = round(tot["pcbway"] + tot["digikey"] + tot["sigma"], 2)
    tot["cop"] = round(tot["pcbway"] * TRM + tot["digikey"] * TRM + tot["sigma_cop"])
    return dict(trm=TRM, fecha=FECHA, pcbway=pcbway, componentes=comp, digikey=digikey, sigma=sigma, totales=tot)


def cop(v):
    return f"{round(v):,}".replace(",", ".")


def usd(v):
    return f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def markdown(d):
    t = d["totales"]
    L = [f"# Carrito total — EVSE Monitor (F8)", "",
         f"Precios al {d['fecha']}; TRM {usd(d['trm'])} COP/USD. Página interactiva con casillas: ver el enlace en "
         "`NEXT_SESSION.md`. Generado por `docs/tools/carrito_f8.py`.", "",
         "| Proveedor | US$ | COP |", "|---|---:|---:|",
         f"| PCBWay (PCB, ensamble, componentes, envío, arancel estimado) | {usd(t['pcbway'])} | {cop(t['pcbway'] * d['trm'])} |",
         f"| DigiKey (carrito del curso) | {usd(t['digikey'])} | {cop(t['digikey'] * d['trm'])} |",
         f"| Sigma Electrónica | {usd(t['sigma'])} | {cop(t['sigma_cop'])} |",
         f"| **Total** | **{usd(t['usd'])}** | **{cop(t['cop'])}** |", "", "## PCBWay", "",
         "| Concepto | Detalle | Cant. | US$ c/u | US$ |", "|---|---|---:|---:|---:|"]
    L += [f"| {x['concepto']} | {x['detalle']} | {x['cantidad']} | {usd(x['usd'])} | {usd(x['subtotal'])} |" for x in d["pcbway"]]
    L += ["", "## DigiKey (carrito del curso, ≤ US$ 50)", "", "| Concepto | Detalle | Cant. | US$ c/u | US$ |",
          "|---|---|---:|---:|---:|"]
    L += [f"| {x['concepto']} | {x['detalle']} | {x['cantidad']} | {usd(x['usd'])} | {usd(x['subtotal'])} |" for x in d["digikey"]]
    L += ["", "## Sigma Electrónica (Bogotá)", "", "| Concepto | Detalle | Cant. | COP c/u | COP |", "|---|---|---:|---:|---:|"]
    L += [f"| {x['concepto']} | {x['detalle']} | {x['cantidad']} | {cop(x['cop'])} | {cop(x['subtotal_cop'])} |" for x in d["sigma"]]
    L += ["", "Ya disponible, no se compra: U1 (RECOM R-78CK3.3-0.5, la del profesor).", "",
          "Supuestos: el precio de PCBWay es el del cotizador del 20 oct (el final sale al revisar los archivos); los "
          "componentes turnkey usan el precio de LCSC por unidad (PCBWay puede cobrar mínimos de compra en pasivos); el "
          "envío y el arancel son estimados.", "",
          "Pedido en grupo: el envío de PCBWay se divide entre quienes pidan en la misma cuenta (el total es el máximo, "
          "como si se pidiera solo) y DigiKey cobra US$ 100 fijos de envío a Colombia por todo el carrito del curso (tu "
          "parte no está sumada). Paso a paso: `docs/fabricacion/GUIA_PEDIDO.md`."]
    return "\n".join(L) + "\n"


PAGINA = r"""<title>Carrito EVSE Monitor</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
/* Hoja de pedido: banda de resumen arriba, una tabla por proveedor, casillas para marcar lo comprado */
:root {
  --bg: #f4f6f2; --panel: #ffffff; --fg: #17221b; --muted: #5d6b62; --line: #d6ddd5;
  --mask: #1f5a3a; --copper: #b4742a; --ok: #2f7d4a; --ok-bg: #e3f1e7;
  --display: "Barlow Semi Condensed", "Arial Narrow", sans-serif;
  --body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1612; --panel: #16211b; --fg: #e4ece6; --muted: #9aaba0; --line: #2a3a30;
  --mask: #5fb487; --copper: #e0a15a; --ok: #6fcf94; --ok-bg: #173323; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0f1612; --panel: #16211b; --fg: #e4ece6; --muted: #9aaba0; --line: #2a3a30;
  --mask: #5fb487; --copper: #e0a15a; --ok: #6fcf94; --ok-bg: #173323; color-scheme: dark }
* { box-sizing: border-box }
body { background: var(--bg); color: var(--fg); font: 16px/1.5 var(--body); margin: 0 }
.envoltura { max-width: 1040px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)) }
h1, h2 { font-family: var(--display); font-weight: 700; letter-spacing: .01em; text-wrap: balance; margin: 0 }
h1 { font-size: clamp(1.9rem, 4vw, 2.6rem) }
h2 { font-size: 1.45rem; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap }
h2 .sub { font: 600 .95rem var(--mono); color: var(--copper) }
.meta { color: var(--muted); margin: 6px 0 0 }
.resumen { margin-top: 22px; display: grid; grid-template-columns: 1.3fr repeat(3, 1fr); gap: 1px; background: var(--line);
  border: 1px solid var(--line); border-radius: 10px; overflow: hidden }
.resumen > div { background: var(--panel); padding: 14px 16px; min-width: 0 }
.resumen .eti { font: 600 .72rem var(--body); text-transform: uppercase; letter-spacing: .08em; color: var(--muted) }
.resumen .num { font: 600 1.35rem var(--mono); font-variant-numeric: tabular-nums; margin-top: 2px }
.resumen .cop { font: .9rem var(--mono); color: var(--muted); font-variant-numeric: tabular-nums }
.resumen .total { background: var(--mask); color: #fff }
.resumen .total .eti, .resumen .total .cop { color: rgba(255,255,255,.8) }
.progreso { margin-top: 14px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; color: var(--muted); font-size: .95rem }
.barra { flex: 1 1 220px; height: 8px; background: var(--line); border-radius: 99px; overflow: hidden }
.barra i { display: block; height: 100%; width: 0; background: var(--ok); transition: width .3s }
.estado { font: .8rem var(--mono); color: var(--muted) }
section { margin-top: 34px }
.tabla { overflow-x: auto; margin-top: 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel) }
table { width: 100%; border-collapse: collapse; min-width: 640px }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top }
th { font: 600 .72rem var(--body); text-transform: uppercase; letter-spacing: .07em; color: var(--muted) }
tr:last-child td { border-bottom: 0 }
td.n { font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap }
th.n { text-align: right }
.concepto { font-weight: 600 }
.detalle { color: var(--muted); font-size: .9rem }
tr.hecho td { background: var(--ok-bg) }
tr.hecho .concepto { text-decoration: line-through; text-decoration-color: var(--ok) }
input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--ok); cursor: pointer }
input[type=checkbox]:focus-visible { outline: 2px solid var(--copper); outline-offset: 2px }
a { color: var(--mask) } a:focus-visible { outline: 2px solid var(--copper) }
tfoot td { font-weight: 600 }
details { margin-top: 12px }
summary { cursor: pointer; font-weight: 600; color: var(--mask) }
.comp td, .comp th { padding: 6px 10px; font-size: .88rem }
.nota { margin-top: 30px; padding: 14px 16px; border-left: 3px solid var(--copper); background: var(--panel); color: var(--muted); font-size: .93rem }
.nota p { margin: 0 0 6px } .nota p:last-child { margin: 0 }
@media (max-width: 760px) { .resumen { grid-template-columns: 1fr 1fr } .resumen .total { grid-column: 1 / -1 } }
@media (prefers-reduced-motion: reduce) { .barra i { transition: none } }
</style>
<div class="envoltura">
  <header>
    <h1>Carrito EVSE Monitor</h1>
    <p class="meta" id="meta"></p>
  </header>
  <div class="resumen" id="resumen"></div>
  <div class="progreso"><span id="cuenta">0 de 0 comprados</span><div class="barra"><i id="barra"></i></div><span class="estado" id="estado">Cargando lo marcado…</span></div>
  <section><h2>PCBWay <span class="sub">un solo pedido: PCB + ensamble</span></h2><div class="tabla"><table id="t-pcbway"></table></div>
    <details><summary>Ver los 57 componentes que compra PCBWay (LCSC)</summary><div class="tabla"><table class="comp" id="t-comp"></table></div></details></section>
  <section><h2>DigiKey <span class="sub">carrito común del curso · ≤ US$ 50</span></h2><div class="tabla"><table id="t-digikey"></table></div></section>
  <section><h2>Sigma Electrónica <span class="sub">Bogotá · lo que va fuera de la placa</span></h2><div class="tabla"><table id="t-sigma"></table></div></section>
  <div class="nota" id="nota"></div>
</div>
<script id="datos" type="application/json">__DATOS__</script>
<script>
const D = JSON.parse(document.getElementById("datos").textContent);
const marcados = {};
const fmtUsd = v => "US$ " + v.toLocaleString("es-CO", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtCop = v => "$ " + Math.round(v).toLocaleString("es-CO") + " COP";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const items = [...D.pcbway, ...D.digikey, ...D.sigma];

document.getElementById("meta").textContent =
  `Precios al ${D.fecha} · TRM ${D.trm.toLocaleString("es-CO")} COP/USD · placa Rev 1.0, 130 × 100 mm`;
const T = D.totales;
document.getElementById("resumen").innerHTML = `
  <div class="total"><div class="eti">Total</div><div class="num">${fmtUsd(T.usd)}</div><div class="cop">${fmtCop(T.cop)}</div></div>
  <div><div class="eti">PCBWay</div><div class="num">${fmtUsd(T.pcbway)}</div><div class="cop">${fmtCop(T.pcbway * D.trm)}</div></div>
  <div><div class="eti">DigiKey</div><div class="num">${fmtUsd(T.digikey)}</div><div class="cop">${fmtCop(T.digikey * D.trm)}</div></div>
  <div><div class="eti">Sigma</div><div class="num">${fmtUsd(T.sigma)}</div><div class="cop">${fmtCop(T.sigma_cop)}</div></div>`;

function filas(lista, enCop) {
  const cab = `<thead><tr><th>Comprado</th><th>Concepto</th><th class="n">Cant.</th><th class="n">${enCop ? "COP c/u" : "US$ c/u"}</th><th class="n">${enCop ? "COP" : "US$"}</th><th>Enlace</th></tr></thead>`;
  const cuerpo = lista.map(x => `<tr id="f-${x.id}">
    <td><input type="checkbox" id="c-${x.id}" data-id="${x.id}" aria-label="Marcar comprado: ${esc(x.concepto)}"></td>
    <td><div class="concepto">${esc(x.concepto)}</div><div class="detalle">${esc(x.detalle)}</div></td>
    <td class="n">${x.cantidad}</td>
    <td class="n">${enCop ? Math.round(x.cop).toLocaleString("es-CO") : x.usd.toLocaleString("es-CO", {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
    <td class="n">${enCop ? Math.round(x.subtotal_cop).toLocaleString("es-CO") : x.subtotal.toLocaleString("es-CO", {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
    <td>${x.enlace ? `<a href="${esc(x.enlace)}" target="_blank" rel="noopener">abrir</a>` : ""}</td></tr>`).join("");
  const sub = enCop ? lista.reduce((a, x) => a + x.subtotal_cop, 0) : lista.reduce((a, x) => a + x.subtotal, 0);
  const pie = `<tfoot><tr><td></td><td>Subtotal</td><td></td><td></td><td class="n">${enCop ? Math.round(sub).toLocaleString("es-CO") : sub.toLocaleString("es-CO", {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td><td></td></tr></tfoot>`;
  return cab + "<tbody>" + cuerpo + "</tbody>" + pie;
}
document.getElementById("t-pcbway").innerHTML = filas(D.pcbway, false);
document.getElementById("t-digikey").innerHTML = filas(D.digikey, false);
document.getElementById("t-sigma").innerHTML = filas(D.sigma, true);
document.getElementById("t-comp").innerHTML = `<thead><tr><th>Designadores</th><th>Fabricante</th><th>MPN</th><th>LCSC</th><th class="n">Cant.</th><th class="n">US$ c/u</th><th class="n">US$</th></tr></thead><tbody>` +
  D.componentes.map(c => `<tr><td>${esc(c.designadores)}</td><td>${esc(c.fabricante)}</td><td><code>${esc(c.mpn)}</code></td>
    <td><a href="${esc(c.enlace)}" target="_blank" rel="noopener">${esc(c.lcsc)}</a></td><td class="n">${c.cantidad}</td>
    <td class="n">${c.usd.toFixed(4)}</td><td class="n">${c.subtotal.toFixed(2)}</td></tr>`).join("") + "</tbody>";
document.getElementById("nota").innerHTML = `
  <p><strong>Ya disponible, no se compra:</strong> U1, el regulador RECOM R-78CK3.3-0.5 del profesor.</p>
  <p><strong>Supuestos:</strong> PCB y ensamble salen del cotizador de PCBWay del 20 oct; el precio final llega cuando PCBWay revisa los archivos. Los componentes usan el precio de LCSC por unidad (PCBWay puede cobrar mínimos de compra en pasivos). Envío y arancel son estimados: confírmalos en la cotización de DHL.</p>
  <p><strong>Pedido en grupo:</strong> el envío de PCBWay se divide entre quienes pidan en la misma cuenta, así que el total de arriba es el máximo (como si pidieras solo). DigiKey cobra US$ 100 fijos de envío a Colombia por todo el carrito del curso; tu parte no está sumada. El paso a paso está en docs/fabricacion/GUIA_PEDIDO.md.</p>
  <p><strong>Archivos para subir:</strong> EVSE_Monitor_Gerber.zip, BOM_PCBWay.xlsx y PickPlace_PCBWay.csv (carpeta docs/fabricacion del repositorio).</p>`;

function pintar() {
  let n = 0;
  for (const x of items) {
    const v = !!marcados[x.id];
    const c = document.getElementById("c-" + x.id);
    if (c) c.checked = v;
    document.getElementById("f-" + x.id)?.classList.toggle("hecho", v);
    if (v) n++;
  }
  document.getElementById("cuenta").textContent = `${n} de ${items.length} comprados`;
  document.getElementById("barra").style.width = (100 * n / items.length) + "%";
}

let db = null, ref = null, pendiente = null, escribiendo = false;
const estado = t => { document.getElementById("estado").textContent = t; };
async function guardar() {
  if (!ref || escribiendo) return;
  escribiendo = true;
  try {
    while (pendiente) {
      const datos = pendiente; pendiente = null;
      await ref.set({marcados: datos, actualizado: new Date().toISOString()});
    }
    estado("Guardado");
  } catch (e) {
    estado(e && e.code === "invalid_argument" ? "Solo lectura: no puedes marcar en esta página" : "No se pudo guardar; vuelve a intentar");
  } finally { escribiendo = false; }
}
let reloj = null;
document.addEventListener("change", ev => {
  const id = ev.target?.dataset?.id;
  if (!id) return;
  marcados[id] = ev.target.checked;
  pintar();
  if (!ref) { estado("Sin guardado en esta vista: las marcas se pierden al cerrar"); return; }
  pendiente = {...marcados};
  estado("Guardando…");
  clearTimeout(reloj);
  reloj = setTimeout(guardar, 500);
});
pintar();
(async () => {
  try { db = window.claude ? await window.claude.use("db") : null; } catch (e) { db = null; }
  if (!db) { estado("Sin guardado en esta vista: las marcas se pierden al cerrar"); return; }
  ref = db.doc("compras/estado");
  ref.onSnapshot(s => {
    if (s.exists && !pendiente && !escribiendo) {
      const m = (s.data() || {}).marcados || {};
      for (const k of Object.keys(marcados)) delete marcados[k];
      Object.assign(marcados, m);
      pintar();
    }
    estado(s.exists ? "Marcas guardadas en la página" : "Aún no hay nada marcado");
  }, () => estado("No se pudo leer lo marcado"));
})();
</script>
"""


def main():
    d = calcular()
    FAB.mkdir(parents=True, exist_ok=True)
    datos = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    (FAB / "Carrito_F8.html").write_text(PAGINA.replace("__DATOS__", datos), encoding="utf-8")
    (FAB / "CARRITO_F8.md").write_text(markdown(d), encoding="utf-8")
    t = d["totales"]
    print(f"PCBWay US$ {t['pcbway']} · DigiKey US$ {t['digikey']} · Sigma {t['sigma_cop']} COP (US$ {t['sigma']}) · "
          f"total US$ {t['usd']} = {cop(t['cop'])} COP; componentes {len(d['componentes'])} líneas")


if __name__ == "__main__":
    main()
