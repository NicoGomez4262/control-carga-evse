// Gráficas en <canvas> sin dependencias: series de tiempo (hora de Colombia) y barras por día.
// const g = new Grafica(cont, { series: [{ nombre, color: "--verde", unidad, dec }], alto }); g.datos([[[t, v], …]]);

const fmtHora = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit", hour12: false });
const fmtDia = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", day: "numeric", month: "short" });
const fmtTodo = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
const fmtN = (v, d) => new Intl.NumberFormat("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);

function pasoBonito(rango, n) {
  const bruto = rango / n || 1;
  const p = Math.pow(10, Math.floor(Math.log10(bruto)));
  const r = bruto / p;
  return (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * p;
}
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || v;

export class Grafica {
  constructor(cont, op) {
    this.op = { alto: 200, barras: false, ...op };
    this.cont = cont;
    cont.classList.add("grafica");
    cont.style.height = this.op.alto + "px";
    this.canvas = document.createElement("canvas");
    this.tip = document.createElement("div");
    this.tip.className = "tip";
    this.tip.hidden = true;
    this.vacio = document.createElement("p");
    this.vacio.className = "vacio";
    this.vacio.textContent = op.vacio || "Sin datos en este rango.";
    this.vacio.hidden = true;
    cont.append(this.canvas, this.tip, this.vacio);
    this.series = this.op.series.map((s) => ({ ...s, puntos: [] }));
    this.raton = null;
    this.revelado = 0;
    this.obs = new ResizeObserver(() => this.dibujar());
    this.obs.observe(cont);
    this.canvas.addEventListener("pointermove", (e) => {
      this.raton = e.clientX - this.canvas.getBoundingClientRect().left;
      this.dibujar();
    });
    this.canvas.addEventListener("pointerleave", () => {
      this.raton = null;
      this.tip.hidden = true;
      this.dibujar();
    });
    this.tema = matchMedia("(prefers-color-scheme: dark)");
    this.alTema = () => this.dibujar();
    this.tema.addEventListener("change", this.alTema);
  }
  destruir() {
    this.obs.disconnect();
    this.tema.removeEventListener("change", this.alTema);
  }
  datos(listas, rango) {
    listas.forEach((l, k) => (this.series[k].puntos = l.filter((p) => Number.isFinite(p[1]))));
    this.rango = rango;
    const hay = this.series.some((s) => s.puntos.length);
    this.vacio.hidden = hay;
    // la curva se dibuja de izquierda a derecha la primera vez (cada vez que cambian los datos)
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      this.revelado = 1;
      return this.dibujar();
    }
    const t0 = performance.now();
    const paso = (t) => {
      const x = Math.min(1, (t - t0) / 700);
      this.revelado = 1 - Math.pow(1 - x, 4);
      this.dibujar();
      if (x < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }
  dibujar() {
    const { canvas, cont } = this;
    const dpr = window.devicePixelRatio || 1;
    const W = cont.clientWidth, H = cont.clientHeight;
    if (!W || !H) return;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    const c = canvas.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, W, H);
    const todos = this.series.flatMap((s) => s.puntos);
    if (!todos.length) return;
    const tinta2 = css("--tinta-3"), costura = css("--costura");
    const izq = 40, der = 10, arr = 12, aba = 24;
    let t1 = this.rango?.[0] ?? Math.min(...todos.map((p) => p[0]));
    let t2 = this.rango?.[1] ?? Math.max(...todos.map((p) => p[0]));
    if (t2 <= t1) t2 = t1 + 3600;
    let v1 = Math.min(...todos.map((p) => p[1])), v2 = Math.max(...todos.map((p) => p[1]));
    if (this.op.cero || this.op.barras) v1 = Math.min(0, v1);
    if (v2 - v1 < 1e-9) (v2 += 1), (v1 -= this.op.cero ? 0 : 1);
    const paso = pasoBonito(v2 - v1, 4);
    v1 = Math.floor(v1 / paso) * paso;
    v2 = Math.ceil(v2 / paso) * paso;
    const X = (t) => izq + ((t - t1) / (t2 - t1)) * (W - izq - der);
    const Y = (v) => arr + (1 - (v - v1) / (v2 - v1)) * (H - arr - aba);
    c.font = `500 11px Barlow, system-ui, sans-serif`;
    c.fillStyle = tinta2;
    c.strokeStyle = costura;
    c.lineWidth = 1;
    c.textAlign = "right";
    c.textBaseline = "middle";
    const dec = this.series[0].dec ?? 1;
    for (let v = v1; v <= v2 + paso / 2; v += paso) {
      const y = Math.round(Y(v)) + 0.5;
      c.beginPath();
      c.moveTo(izq, y);
      c.lineTo(W - der, y);
      c.stroke();
      c.fillText(fmtN(v, paso < 1 ? Math.min(dec, 2) : 0), izq - 6, y);
    }
    const largo = t2 - t1;
    const pasoT = largo <= 86400 * 1.1 ? 3 * 3600 : largo <= 8 * 86400 ? 86400 : 5 * 86400;
    c.textAlign = "center";
    c.textBaseline = "top";
    const inicio = Math.ceil((t1 + 5 * 3600) / pasoT) * pasoT - 5 * 3600;
    for (let t = inicio; t <= t2; t += pasoT) {
      const x = X(t);
      if (x < izq + 12 || x > W - der - 12) continue;
      c.fillText(pasoT < 86400 ? fmtHora.format(t * 1000) : fmtDia.format(t * 1000), x, H - aba + 7);
    }
    c.save();
    c.beginPath();
    c.rect(izq, 0, (W - izq - der) * this.revelado, H);
    c.clip();
    for (const s of this.series) {
      if (!s.puntos.length) continue;
      const col = css(s.color);
      if (this.op.barras) {
        const ancho = Math.max(3, ((W - izq - der) / Math.max(1, largo / 86400)) * 0.62);
        for (const [t, v] of s.puntos) {
          const x = X(t + 43200), y = Y(v), y0 = Y(0);
          c.fillStyle = col;
          c.globalAlpha = 0.9;
          const r = Math.min(3, ancho / 2);
          c.beginPath();
          c.roundRect(x - ancho / 2, y, ancho, Math.max(1, y0 - y), [r, r, 0, 0]);
          c.fill();
        }
        c.globalAlpha = 1;
        continue;
      }
      const hueco = s.hueco || Math.max(900, (largo / 600) * 4);
      c.lineWidth = 2;
      c.lineJoin = "round";
      c.strokeStyle = col;
      const grad = c.createLinearGradient(0, arr, 0, H - aba);
      grad.addColorStop(0, col + "38");
      grad.addColorStop(1, col + "00");
      let tramo = [];
      const cerrar = () => {
        if (!tramo.length) return;
        c.beginPath();
        tramo.forEach(([x, y], k) => (k ? c.lineTo(x, y) : c.moveTo(x, y)));
        c.stroke();
        if (s.relleno !== false) {
          c.lineTo(tramo.at(-1)[0], Y(Math.max(v1, 0)));
          c.lineTo(tramo[0][0], Y(Math.max(v1, 0)));
          c.closePath();
          c.fillStyle = grad;
          c.fill();
        }
        tramo = [];
      };
      let ant = null;
      for (const [t, v] of s.puntos) {
        if (ant !== null && t - ant > hueco) cerrar();
        tramo.push([X(t), Y(v)]);
        ant = t;
      }
      cerrar();
    }
    c.restore();
    if (this.raton !== null && this.raton >= izq) {
      const t = t1 + ((this.raton - izq) / (W - izq - der)) * (t2 - t1);
      const filas = [];
      let tx = null;
      for (const s of this.series) {
        if (!s.puntos.length) continue;
        let mejor = s.puntos[0];
        for (const p of s.puntos) if (Math.abs(p[0] - t) < Math.abs(mejor[0] - t)) mejor = p;
        tx = mejor[0];
        const x = X(this.op.barras ? mejor[0] + 43200 : mejor[0]), y = Y(mejor[1]);
        c.strokeStyle = tinta2;
        c.setLineDash([3, 3]);
        c.beginPath();
        c.moveTo(x + 0.5, arr);
        c.lineTo(x + 0.5, H - aba);
        c.stroke();
        c.setLineDash([]);
        c.fillStyle = css(s.color);
        c.beginPath();
        c.arc(x, y, 4, 0, 7);
        c.fill();
        filas.push(`<i class="muestra" style="background:${css(s.color)}"></i>${s.nombre}: <b>${fmtN(mejor[1], s.dec ?? 1)} ${s.unidad || ""}</b>`);
      }
      if (filas.length) {
        this.tip.hidden = false;
        this.tip.innerHTML = `<small>${this.op.barras ? fmtDia.format(tx * 1000) : fmtTodo.format(tx * 1000)}</small>${filas.join("<br>")}`;
        const x = X(tx);
        this.tip.style.left = Math.min(W - this.tip.offsetWidth - 4, Math.max(4, x - this.tip.offsetWidth / 2)) + "px";
      }
    }
  }
}
