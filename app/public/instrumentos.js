// Instrumentos del tablero: diagrama mímico, medidor de aguja, selector giratorio, registro de rodillos,
// termómetro de barra y anunciador. SVG y CSS hechos a mano, sin dependencias.

const NS = "http://www.w3.org/2000/svg";
const quieto = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const fmtN = (v, d) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);

// ------------------------------------------------------------------ íconos (trazo 1,75 px, 24 × 24)
const P = {
  panel: "M4 14a8 8 0 0 1 16 0M12 14l4-4M7.5 18h9",
  historial: "M4 19V5M4 19h16M8 15l3-4 3 2 5-6",
  alarmas: "M5 17h14l-1.5-2V11a5.5 5.5 0 0 0-11 0v4L5 17zM10 20a2 2 0 0 0 4 0",
  ajustes: "M5 6h9M18 6h1M5 12h3M12 12h7M5 18h11M20 18h-1M14 4v4M8 10v4M16 16v4",
  usuario: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0",
  admin: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3zM9 12l2 2 4-4",
  salir: "M10 5H5v14h5M14 8l4 4-4 4M18 12H9",
  copiar: "M9 9h10v10H9zM5 15V5h10",
  bajar: "M12 4v11M7 10l5 5 5-5M5 20h14",
  subir: "M12 20V9M7 14l5-5 5 5M5 4h14",
  rayo: "M13 3L5 13h6l-1 8 8-10h-6l1-8z",
  enlace: "M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1",
  mas: "M12 5v14M5 12h14",
  atras: "M15 5l-7 7 7 7",
  equipo: "M5 4h14v16H5zM9 8h6M9 12h2M13 12h2M9 16h6",
  tema: "M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z",
  check: "M5 12l5 5 9-10",
  x: "M6 6l12 12M18 6L6 18",
  reloj: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
  termo: "M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0z",
  pausa: "M9 6v12M15 6v12",
  play: "M8 5l11 7-11 7z",
  alto: "M8.5 3h7L21 8.5v7L15.5 21h-7L3 15.5v-7zM12 8v5M12 16.5v.01",
  telegram: "M21 4L3 11l6 2 2 6 3-4 5 4 2-15zM9 13l9-6",
};
export function icono(n, clase = "") {
  return `<svg class="ico ${clase}" viewBox="0 0 24 24" aria-hidden="true"><path d="${P[n] || ""}"/></svg>`;
}

// ------------------------------------------------------------------ diagrama mímico RED → F → K1 → J2 → VE
export function mimico() {
  const el = document.createElement("div");
  el.className = "mimico";
  el.innerHTML = `
  <svg viewBox="0 0 360 104" role="img" aria-label="Diagrama del circuito de carga">
    <g class="bus">
      <path class="tramo t1" d="M38 44H80"/><path class="tramo t2" d="M104 44H146"/>
      <path class="tramo t3" d="M188 44H232"/><path class="tramo t4" d="M276 44H306"/>
      <path class="flujo f1" d="M38 44H80"/><path class="flujo f2" d="M104 44H146"/>
      <path class="flujo f3" d="M188 44H232"/><path class="flujo f4" d="M276 44H306"/>
    </g>
    <g class="nodo red"><circle cx="22" cy="44" r="15"/><path d="M13 44c3-7 6-7 9 0s6 7 9 0"/></g>
    <g class="nodo fusible"><rect x="80" y="38" width="24" height="12" rx="3"/><path d="M80 44h24"/></g>
    <g class="nodo k1"><circle class="borne" cx="146" cy="44" r="3.5"/><circle class="borne" cx="188" cy="44" r="3.5"/>
      <path class="cuchilla" d="M146 44H186"/></g>
    <g class="nodo evse"><rect x="232" y="30" width="44" height="28" rx="6"/><path d="M246 44h16M254 37v14" class="tenue"/></g>
    <g class="nodo ve"><path d="M308 50v-6l7-9h22l8 9h7v6h-4M320 50h20" /><circle cx="316" cy="52" r="4"/><circle cx="344" cy="52" r="4"/></g>
    <g class="rotulos">
      <text x="22" y="82" text-anchor="middle" class="r-red">RED</text><text x="22" y="96" text-anchor="middle" class="v-red">—</text>
      <text x="92" y="82" text-anchor="middle">F1</text>
      <text x="167" y="24" text-anchor="middle" class="r-k1">K1</text><text x="167" y="82" text-anchor="middle" class="v-k1">—</text>
      <text x="254" y="82" text-anchor="middle">J2 · EVSE</text>
      <text x="330" y="82" text-anchor="middle">VE</text><text x="330" y="96" text-anchor="middle" class="v-ve">—</text>
    </g>
  </svg>`;
  return el;
}

export function pintarMimico(el, e, vnom) {
  const conRed = e && Number.isFinite(e.v) && e.v > 40;
  const k1 = !!e?.k1;
  const i = Number(e?.i) || 0;
  const p = Math.max(0, Number(e?.p) || 0);
  const corre = conRed && k1 && i >= 0.3;
  el.classList.toggle("con-red", conRed);
  el.classList.toggle("k1-on", k1);
  el.classList.toggle("corre", corre && !quieto());
  const max = (vnom >= 200 ? 240 : 120) * 32;
  el.style.setProperty("--dur", `${(2.6 - Math.min(1, p / max) * 2).toFixed(2)}s`);
  el.querySelector(".v-red").textContent = conRed ? `${fmtN(e.v, 0)} V` : "sin medida";
  el.querySelector(".v-k1").textContent = k1 ? "cerrado" : "abierto";
  el.querySelector(".v-ve").textContent = corre ? `${fmtN(i, 1)} A` : "en reposo";
}

// ------------------------------------------------------------------ medidor de aguja (240°) con resorte amortiguado
const A0 = 150, BARRIDO = 240;
const polar = (cx, cy, r, ang) => [cx + r * Math.cos((ang * Math.PI) / 180), cy + r * Math.sin((ang * Math.PI) / 180)];
function arco(cx, cy, r, a1, a2) {
  const [x1, y1] = polar(cx, cy, r, a1), [x2, y2] = polar(cx, cy, r, a2);
  return `M${x1.toFixed(2)} ${y1.toFixed(2)}A${r} ${r} 0 ${a2 - a1 > 180 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

// Escalas del medidor de potencia (kW): de 100 W a 100 kW. «paso» = marcas mayores; debajo de 1 kW se rotula en W.
export const ESCALAS_P = [
  { max: 0.1, paso: 0.02, u: "W" },
  { max: 0.25, paso: 0.05, u: "W" },
  { max: 0.5, paso: 0.1, u: "W" },
  { max: 1, paso: 0.2, u: "W" },
  { max: 2, paso: 0.5, u: "kW" },
  { max: 4, paso: 1, u: "kW" },
  { max: 8, paso: 1, u: "kW" },
  { max: 20, paso: 5, u: "kW" },
  { max: 50, paso: 10, u: "kW" },
  { max: 100, paso: 20, u: "kW" },
];

export class Medidor {
  constructor(escala) {
    this.el = document.createElement("div");
    this.el.className = "medidor";
    const e = typeof escala === "number" ? ESCALAS_P.find((x) => x.max >= escala) || ESCALAS_P.at(-1) : escala;
    this.max = e.max;
    this.pasoM = e.paso;
    this.u = e.u;
    this.val = 0;
    this.obj = 0;
    this.vel = 0;
    this.pico = 0;
    this.dibujarEscala();
    this.paso = this.paso.bind(this);
  }
  dibujarEscala() {
    const cx = 120, cy = 120, R = 96, max = this.max;
    const n = Math.round(max / this.pasoM); // marcas mayores; entre cada par, una menor
    const rotulo = (v) => (this.u === "W" ? String(Math.round(v * 1000)) : fmtN(v, v % 1 ? 1 : 0));
    let marcas = "";
    for (let k = 0; k <= n * 2; k++) {
      const a = A0 + (BARRIDO * k) / (n * 2);
      const mayor = k % 2 === 0;
      const [x1, y1] = polar(cx, cy, R - (mayor ? 14 : 8), a), [x2, y2] = polar(cx, cy, R - 2, a);
      marcas += `<line class="${mayor ? "mayor" : "menor"}" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"/>`;
      if (mayor) {
        const [tx, ty] = polar(cx, cy, R - 28, a);
        marcas += `<text x="${tx.toFixed(1)}" y="${(ty + 4).toFixed(1)}" text-anchor="middle">${rotulo((k / 2) * this.pasoM)}</text>`;
      }
    }
    marcas += `<text class="unidad" x="${cx}" y="${cy + 30}" text-anchor="middle">${this.u}</text>`; // debajo del eje: la aguja no lo tapa
    this.el.innerHTML = `<svg viewBox="0 0 240 176" aria-hidden="true">
      <path class="pista" d="${arco(cx, cy, R + 8, A0, A0 + BARRIDO)}"/>
      <path class="valor" d=""/>
      <g class="escala">${marcas}</g>
      <path class="pico" d="M0 0l-5-9h10z"/>
      <g class="aguja"><line x1="0" y1="0" x2="${R - 6}" y2="0"/><circle r="9"/><circle class="centro" r="3.5"/></g>
    </svg>`;
    this.cx = cx;
    this.cy = cy;
    this.R = R;
    this.svgValor = this.el.querySelector(".valor");
    this.aguja = this.el.querySelector(".aguja");
    this.marcaPico = this.el.querySelector(".pico");
    this.aplicar(0);
  }
  // Cambia de escala sin que la aguja salte: conserva el ángulo y la deja ir con su resorte al valor nuevo.
  escala(e) {
    if (e.max === this.max) return;
    const f = this.val / this.max;
    this.max = e.max;
    this.pasoM = e.paso;
    this.u = e.u;
    this.val = f * this.max;
    this.dibujarEscala();
    if (!quieto() && this.el.animate) this.el.querySelector(".escala").animate([{ opacity: 0 }, { opacity: 1 }], { duration: 450, easing: "ease-out" });
    this.ir(this.obj, this.pico);
  }
  ir(kw, pico) {
    this.obj = Math.max(0, Math.min(this.max * 1.04, kw || 0));
    this.pico = pico || 0;
    if (quieto()) {
      this.val = this.obj;
      this.vel = 0;
      return this.aplicar(this.val);
    }
    if (!this.corriendo) {
      this.corriendo = true;
      this.t = performance.now();
      requestAnimationFrame(this.paso);
    }
    // si el navegador frena los cuadros (pestaña en segundo plano), la aguja igual llega a su valor
    clearTimeout(this.respaldo);
    this.respaldo = setTimeout(() => {
      if (performance.now() - this.t > 400) {
        this.corriendo = false;
        this.val = this.obj;
        this.vel = 0;
        this.aplicar(this.obj);
      }
    }, 1200);
  }
  paso(t) {
    const dt = Math.min(0.05, (t - this.t) / 1000);
    this.t = t;
    // resorte un poco subamortiguado: la aguja se pasa apenas y se asienta, como un instrumento de bobina móvil
    const k = 38, c = 9.5;
    this.vel += (k * (this.obj - this.val) - c * this.vel) * dt;
    this.val += this.vel * dt;
    this.aplicar(this.val);
    if (Math.abs(this.obj - this.val) < 0.001 && Math.abs(this.vel) < 0.001) {
      this.corriendo = false;
      this.aplicar(this.obj);
      return;
    }
    requestAnimationFrame(this.paso);
  }
  aplicar(v) {
    const f = Math.max(0, Math.min(1.04, v / this.max));
    const a = A0 + BARRIDO * f;
    this.aguja.setAttribute("transform", `translate(${this.cx} ${this.cy}) rotate(${a.toFixed(2)})`);
    this.svgValor.setAttribute("d", f > 0.002 ? arco(this.cx, this.cy, this.R + 8, A0, Math.min(A0 + BARRIDO, a)) : "");
    const fp = Math.max(0, Math.min(1, this.pico / this.max));
    const [px, py] = polar(this.cx, this.cy, this.R + 20, A0 + BARRIDO * fp);
    this.marcaPico.setAttribute("transform", `translate(${px.toFixed(1)} ${py.toFixed(1)}) rotate(${(A0 + BARRIDO * fp + 90).toFixed(1)})`);
    this.marcaPico.style.opacity = this.pico > this.max * 0.02 ? 1 : 0;
  }
}

// ------------------------------------------------------------------ selector giratorio de dos posiciones (K1)
export function selector() {
  const el = document.createElement("div");
  el.className = "selector";
  el.innerHTML = `
    <div class="perilla-marco">
      <svg class="anillo" viewBox="0 0 120 120" aria-hidden="true">
        <circle class="pista" cx="60" cy="60" r="54"/>
        <path class="luz det" d="${arco(60, 60, 54, 196, 248)}"/>
        <path class="luz per" d="${arco(60, 60, 54, 292, 344)}"/>
        <circle class="espera" cx="60" cy="60" r="54"/>
      </svg>
      <button class="perilla" type="button" role="switch" aria-checked="false" aria-label="Permiso de carga">
        <span class="agarre"></span>
      </button>
    </div>
    <div class="posiciones">
      <button type="button" class="pos det" data-o="detener">Detener</button>
      <button type="button" class="pos per" data-o="permitir">Permitir</button>
    </div>`;
  return el;
}

export function pintarSelector(el, { permiso, k1, esperando, bloqueado }) {
  el.classList.toggle("en-per", !!permiso);
  el.classList.toggle("k1-on", !!k1);
  el.classList.toggle("esperando", !!esperando);
  el.classList.toggle("bloqueado", !!bloqueado);
  const b = el.querySelector(".perilla");
  b.setAttribute("aria-checked", permiso ? "true" : "false");
  for (const x of el.querySelectorAll("button")) x.disabled = !!bloqueado || !!esperando;
}

// ------------------------------------------------------------------ registro de rodillos (energía total)
export function rodillos(el, valor, dec = 1) {
  const txt = Number.isFinite(valor) ? valor.toFixed(dec).padStart(7 + dec, "0") : "–".repeat(8);
  if (!el.firstChild || el.dataset.n !== String(txt.length)) {
    el.innerHTML = [...txt]
      .map((c) => (c === "." ? `<span class="coma">,</span>` : `<span class="rueda"><span class="tira">${"0123456789".split("").map((d) => `<i>${d}</i>`).join("")}</span></span>`))
      .join("");
    el.dataset.n = String(txt.length);
  }
  const ruedas = el.querySelectorAll(".rueda .tira");
  let k = 0;
  for (const c of txt) {
    if (c === ".") continue;
    const d = Number(c);
    ruedas[k].style.transform = `translateY(${Number.isFinite(d) ? -d : 0}em)`;
    ruedas[k].parentElement.classList.toggle("dec", k >= ruedas.length - dec);
    k++;
  }
  el.setAttribute("aria-label", Number.isFinite(valor) ? `${fmtN(valor, dec)} kWh` : "sin dato");
}

// ------------------------------------------------------------------ termómetro de barra con marca de corte
export function termometro(el, t, corte) {
  const ok = Number.isFinite(t);
  const f = ok ? Math.max(0, Math.min(1, t / 100)) : 0;
  el.style.setProperty("--f", f.toFixed(3));
  el.style.setProperty("--corte", (Math.max(0, Math.min(100, corte || 60)) / 100).toFixed(3));
  el.dataset.nivel = !ok ? "nada" : t >= corte ? "mal" : t >= corte - 10 ? "aviso" : "bien";
}

// ------------------------------------------------------------------ número que corre hasta su valor nuevo
const tweens = new WeakMap();
export function numero(el, v, dec, sufijo = "") {
  if (!el) return;
  if (!Number.isFinite(v)) {
    el.textContent = "—";
    el.dataset.v = "";
    return;
  }
  const de = Number(el.dataset.v);
  el.dataset.v = String(v);
  if (!Number.isFinite(de) || quieto() || de === v || el.dataset.v === "") {
    el.textContent = fmtN(v, dec) + sufijo;
    return;
  }
  const t0 = performance.now(), dur = 420;
  const id = {};
  tweens.set(el, id);
  const paso = (t) => {
    if (tweens.get(el) !== id) return;
    const x = Math.min(1, (t - t0) / dur);
    const e = 1 - Math.pow(2, -10 * x);
    el.textContent = fmtN(de + (v - de) * (x >= 1 ? 1 : e), dec) + sufijo;
    if (x < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// ------------------------------------------------------------------ secuencia de encendido (una vez por vista)
export function encender(raiz) {
  if (quieto() || !raiz.animate) return;
  const mods = [...raiz.querySelectorAll(".mod")];
  const anims = [];
  // si el navegador no corre las animaciones (pestaña en segundo plano), el tablero queda visible igual
  setTimeout(() => anims.forEach((a) => a.playState !== "finished" && a.finish()), 1800);
  mods.forEach((m, k) =>
    anims[k] = m.animate(
      [{ opacity: 0, transform: "translateY(10px) scale(.985)", filter: "blur(2px)" }, { opacity: 1, transform: "none", filter: "none" }],
      { duration: 520, delay: 40 * k, easing: "cubic-bezier(.16,1,.3,1)", fill: "backwards" },
    ),
  );
  [...raiz.querySelectorAll(".piloto")].forEach((p, k) =>
    p.animate([{ filter: "brightness(1)" }, { filter: "brightness(2.2)", offset: 0.4 }, { filter: "brightness(1)" }], {
      duration: 380, delay: 220 + 70 * k, easing: "ease-out",
    }),
  );
}
