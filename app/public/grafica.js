// Gráfica de series de tiempo en <canvas>, sin dependencias. Hora de Colombia en el eje X.
// uso: const g = new Grafica(contenedor, { series: [{ nombre, color, unidad, dec }] }); g.datos([[[t, v], …], …]);

const fmtHora = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit", hour12: false });
const fmtDia = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", day: "2-digit", month: "short" });
const fmtTodo = new Intl.DateTimeFormat("es-CO", {
  timeZone: "America/Bogota", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
});

function pasoBonito(rango, n) {
  const bruto = rango / n;
  const p = Math.pow(10, Math.floor(Math.log10(bruto)));
  const r = bruto / p;
  return (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * p;
}

export class Grafica {
  constructor(contenedor, opciones) {
    this.op = { alto: 220, ...opciones };
    this.cont = contenedor;
    this.cont.classList.add("grafica");
    this.cont.style.height = this.op.alto + "px";
    this.canvas = document.createElement("canvas");
    this.tip = document.createElement("div");
    this.tip.className = "tip";
    this.tip.hidden = true;
    this.cont.append(this.canvas, this.tip);
    this.series = this.op.series.map((s) => ({ ...s, puntos: [] }));
    this.raton = null;
    this.obs = new ResizeObserver(() => this.dibujar());
    this.obs.observe(this.cont);
    this.canvas.addEventListener("pointermove", (e) => {
      const r = this.canvas.getBoundingClientRect();
      this.raton = e.clientX - r.left;
      this.dibujar();
    });
    this.canvas.addEventListener("pointerleave", () => {
      this.raton = null;
      this.tip.hidden = true;
      this.dibujar();
    });
  }

  datos(listas) {
    listas.forEach((l, k) => {
      if (this.series[k]) this.series[k].puntos = l.filter((p) => p[1] !== null && Number.isFinite(p[1]));
    });
    this.dibujar();
  }

  agregar(t, valores, ventanaS) {
    valores.forEach((v, k) => {
      const s = this.series[k];
      if (!s || v === null || !Number.isFinite(v)) return;
      s.puntos.push([t, v]);
      if (ventanaS) while (s.puntos.length && s.puntos[0][0] < t - ventanaS) s.puntos.shift();
    });
    this.dibujar();
  }

  destruir() {
    this.obs.disconnect();
  }

  dibujar() {
    const dpr = window.devicePixelRatio || 1;
    const W = this.cont.clientWidth, H = this.cont.clientHeight;
    if (!W || !H) return;
    this.canvas.width = W * dpr;
    this.canvas.height = H * dpr;
    const c = this.canvas.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, W, H);
    const css = getComputedStyle(document.documentElement);
    const colTexto = css.getPropertyValue("--suave").trim();
    const colLinea = css.getPropertyValue("--linea").trim();

    const todos = this.series.flatMap((s) => s.puntos);
    if (!todos.length) {
      c.fillStyle = colTexto;
      c.font = "13px system-ui";
      c.textAlign = "center";
      c.fillText(this.op.vacio || "Sin datos en este rango", W / 2, H / 2);
      return;
    }
    let tMin = this.op.tMin ?? Math.min(...todos.map((p) => p[0]));
    let tMax = this.op.tMax ?? Math.max(...todos.map((p) => p[0]));
    if (tMax - tMin < 60) tMax = tMin + 60;
    let yMin = this.op.yMin ?? Math.min(...todos.map((p) => p[1]));
    let yMax = this.op.yMax ?? Math.max(...todos.map((p) => p[1]));
    if (this.op.cero) yMin = Math.min(0, yMin);
    if (yMax - yMin < 1e-9) {
      yMax += 1;
      yMin -= this.op.cero ? 0 : 1;
    }
    const paso = pasoBonito(yMax - yMin, 4);
    yMin = Math.floor(yMin / paso) * paso;
    yMax = Math.ceil(yMax / paso) * paso;

    const izq = 46, der = 10, arr = 10, aba = 24;
    const x = (t) => izq + ((t - tMin) / (tMax - tMin)) * (W - izq - der);
    const y = (v) => arr + (1 - (v - yMin) / (yMax - yMin)) * (H - arr - aba);

    c.font = "11px system-ui";
    c.fillStyle = colTexto;
    c.strokeStyle = colLinea;
    c.lineWidth = 1;
    c.textAlign = "right";
    c.textBaseline = "middle";
    const dec = paso < 1 ? Math.min(3, Math.ceil(-Math.log10(paso))) : 0;
    for (let v = yMin; v <= yMax + paso / 2; v += paso) {
      c.beginPath();
      c.moveTo(izq, y(v) + 0.5);
      c.lineTo(W - der, y(v) + 0.5);
      c.stroke();
      c.fillText(v.toFixed(dec), izq - 6, y(v));
    }
    c.textAlign = "center";
    c.textBaseline = "top";
    const span = tMax - tMin;
    const nx = Math.max(2, Math.floor((W - izq - der) / 80));
    for (let k = 0; k <= nx; k++) {
      const t = tMin + (span * k) / nx;
      const d = new Date(t * 1000);
      c.textAlign = k === nx ? "right" : "center";
      c.fillText(span > 2 * 86400 ? fmtDia.format(d) : fmtHora.format(d), x(t), H - aba + 6);
    }

    for (const s of this.series) {
      if (!s.puntos.length) continue;
      c.strokeStyle = s.color;
      c.lineWidth = 2;
      c.lineJoin = "round";
      c.beginPath();
      let antes = null;
      const hueco = this.op.hueco || Infinity;
      for (const [t, v] of s.puntos) {
        if (antes === null || t - antes > hueco) c.moveTo(x(t), y(v));
        else c.lineTo(x(t), y(v));
        antes = t;
      }
      c.stroke();
      if (s.relleno) {
        c.globalAlpha = 0.12;
        c.fillStyle = s.color;
        c.lineTo(x(s.puntos.at(-1)[0]), y(Math.max(yMin, 0)));
        c.lineTo(x(s.puntos[0][0]), y(Math.max(yMin, 0)));
        c.closePath();
        c.fill();
        c.globalAlpha = 1;
      }
    }

    if (this.raton !== null && this.raton >= izq) {
      const t = tMin + ((this.raton - izq) / (W - izq - der)) * span;
      c.strokeStyle = colTexto;
      c.setLineDash([3, 3]);
      c.beginPath();
      c.moveTo(this.raton + 0.5, arr);
      c.lineTo(this.raton + 0.5, H - aba);
      c.stroke();
      c.setLineDash([]);
      const filas = [];
      for (const s of this.series) {
        if (!s.puntos.length) continue;
        let mejor = s.puntos[0];
        for (const p of s.puntos) if (Math.abs(p[0] - t) < Math.abs(mejor[0] - t)) mejor = p;
        filas.push(`<span style="color:${s.color}">●</span> ${s.nombre}: <b>${mejor[1].toFixed(s.dec ?? 1)}</b> ${s.unidad || ""}`);
        c.fillStyle = s.color;
        c.beginPath();
        c.arc(x(mejor[0]), y(mejor[1]), 3.5, 0, 7);
        c.fill();
      }
      this.tip.innerHTML = `<div class="suave">${fmtTodo.format(new Date(t * 1000))}</div>${filas.join("<br>")}`;
      this.tip.hidden = false;
      const ancho = this.tip.offsetWidth;
      this.tip.style.left = Math.min(W - ancho - 4, Math.max(4, this.raton + 10)) + "px";
      this.tip.style.top = "6px";
    }
  }
}
