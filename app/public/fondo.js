// Fondo vivo del tablero: partículas que suben despacio y, de vez en cuando, un pulso de energía que recorre
// una «pista» en ángulo recto, como en una PCB. El resplandor que respira desde el centro va en CSS (body::before).
// Muy tenue y detrás de todo. Con «reducir movimiento» queda quieto; con la pestaña oculta no dibuja nada.

const quieto = matchMedia("(prefers-reduced-motion: reduce)");
const lienzo = document.createElement("canvas");
lienzo.className = "fondo-vivo";
lienzo.setAttribute("aria-hidden", "true");
document.body.prepend(lienzo);
const c = lienzo.getContext("2d");

let W = 0, H = 0, dpr = 1, raf = 0, previo = 0, proxPista = 0, leidoEn = 0;
let parts = [], pistas = [], col = { verde: "#34d27b", azul: "#5b9bff", ambar: "#f2b233", noche: true };

const azar = (a, b) => a + Math.random() * (b - a);

function leerColores() {
  const s = getComputedStyle(document.documentElement);
  const v = (n, d) => s.getPropertyValue(n).trim() || d;
  const fondo = v("--fondo", "#0e1317");
  // fondo oscuro = noche: más brillo; de día las partículas van más suaves
  const n = parseInt(fondo.replace("#", "").slice(0, 2), 16);
  col = { verde: v("--verde", "#34d27b"), azul: v("--azul", "#5b9bff"), ambar: v("--ambar", "#f2b233"), noche: !(n > 128) };
}

function particula(y) {
  const r = Math.random();
  return {
    x: azar(0, W),
    y: y ?? azar(0, H),
    r: azar(0.6, 1.9),
    vy: azar(6, 18), // px/s hacia arriba
    fase: azar(0, Math.PI * 2),
    a: azar(0.18, 0.55),
    c: r < 0.55 ? "verde" : r < 0.9 ? "azul" : "ambar",
  };
}

function medir() {
  dpr = Math.min(1.5, window.devicePixelRatio || 1);
  W = innerWidth;
  H = innerHeight;
  lienzo.width = Math.round(W * dpr);
  lienzo.height = Math.round(H * dpr);
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const n = Math.round(Math.min(70, Math.max(22, (W * H) / 26000)));
  parts = Array.from({ length: n }, () => particula());
  leerColores();
}

// Una pista: 3–5 tramos horizontales y verticales sobre una rejilla de 56 px; el pulso la recorre con estela.
function nuevaPista() {
  const g = 56;
  let x = Math.round(azar(0, W) / g) * g, y = Math.round(azar(H * 0.15, H * 0.9) / g) * g;
  const pts = [[x, y]];
  let horiz = Math.random() < 0.5;
  for (let k = 0, n = 3 + Math.floor(Math.random() * 3); k < n; k++) {
    const largo = g * (1 + Math.floor(Math.random() * 3)) * (Math.random() < 0.5 ? -1 : 1);
    if (horiz) x += largo;
    else y += largo;
    pts.push([x, y]);
    horiz = !horiz;
  }
  let total = 0;
  const seg = pts.slice(1).map((p, k) => {
    const l = Math.hypot(p[0] - pts[k][0], p[1] - pts[k][1]);
    total += l;
    return l;
  });
  return { pts, seg, total, d: 0, v: azar(170, 260), c: Math.random() < 0.6 ? "verde" : "azul", fin: 0 };
}

function punto(p, d) {
  let k = 0;
  while (k < p.seg.length && d > p.seg[k]) d -= p.seg[k++];
  if (k >= p.seg.length) return p.pts[p.pts.length - 1];
  const [x1, y1] = p.pts[k], [x2, y2] = p.pts[k + 1], t = d / p.seg[k];
  return [x1 + (x2 - x1) * t, y1 + (y2 - y1) * t];
}

function dibujar(t) {
  const dt = previo ? Math.min(0.05, (t - previo) / 1000) : 0;
  previo = t;
  if (t - leidoEn > 2000) {
    leerColores(); // el tema (día/noche) puede cambiar
    leidoEn = t;
  }
  c.clearRect(0, 0, W, H);
  const k = col.noche ? 1 : 0.55;

  for (const p of parts) {
    p.y -= p.vy * dt;
    p.fase += dt * 0.8;
    if (p.y < -8) Object.assign(p, particula(H + 8));
    const x = p.x + Math.sin(p.fase) * 6;
    const brillo = p.a * k * (0.75 + 0.25 * Math.sin(p.fase * 1.7));
    c.globalAlpha = brillo * 0.35;
    c.fillStyle = col[p.c];
    c.beginPath();
    c.arc(x, p.y, p.r * 3.2, 0, Math.PI * 2); // halo
    c.fill();
    c.globalAlpha = brillo;
    c.beginPath();
    c.arc(x, p.y, p.r, 0, Math.PI * 2);
    c.fill();
  }

  if (t > proxPista && pistas.length < 2) {
    pistas.push(nuevaPista());
    proxPista = t + azar(2600, 5600);
  }
  c.lineCap = "round";
  for (const p of pistas) {
    p.d += p.v * dt;
    const cola = 110;
    const fin = Math.min(p.d, p.total), ini = Math.max(0, p.d - cola);
    if (ini >= p.total) p.fin = 1;
    // la pista, apenas visible
    c.globalAlpha = 0.07 * k;
    c.strokeStyle = col[p.c];
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(...p.pts[0]);
    for (const q of p.pts.slice(1)) c.lineTo(...q);
    c.stroke();
    // la estela del pulso: varios trazos cada vez más brillantes hacia la cabeza
    for (let s = 0; s < 6; s++) {
      const a = ini + ((fin - ini) * s) / 6, b = ini + ((fin - ini) * (s + 1)) / 6;
      c.globalAlpha = (0.08 + 0.1 * s) * k;
      c.lineWidth = 1 + s * 0.25;
      c.beginPath();
      c.moveTo(...punto(p, a));
      c.lineTo(...punto(p, b));
      c.stroke();
    }
    if (p.d < p.total) {
      const [hx, hy] = punto(p, fin);
      c.globalAlpha = 0.75 * k;
      c.fillStyle = col[p.c];
      c.beginPath();
      c.arc(hx, hy, 1.8, 0, Math.PI * 2);
      c.fill();
      c.globalAlpha = 0.18 * k;
      c.beginPath();
      c.arc(hx, hy, 7, 0, Math.PI * 2);
      c.fill();
    }
  }
  pistas = pistas.filter((p) => !p.fin);
  c.globalAlpha = 1;
  raf = requestAnimationFrame(dibujar);
}

function arrancar() {
  cancelAnimationFrame(raf);
  previo = 0;
  if (document.hidden) return;
  if (quieto.matches) {
    // sin movimiento: una sola imagen fija de partículas
    previo = performance.now();
    dibujar(previo);
    cancelAnimationFrame(raf);
    return;
  }
  raf = requestAnimationFrame(dibujar);
}

let tRes = 0;
addEventListener("resize", () => {
  clearTimeout(tRes);
  tRes = setTimeout(() => (medir(), arrancar()), 200);
});
document.addEventListener("visibilitychange", arrancar);
quieto.addEventListener?.("change", arrancar);
medir();
arrancar();
