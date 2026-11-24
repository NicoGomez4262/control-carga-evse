# Servidor y app web del EVSE Monitor

Cloudflare Workers (plan gratis): un Durable Object por equipo con los WebSocket del ESP32 y de los navegadores,
D1 (SQLite) para los datos y KV para el firmware de la OTA. La app web (`public/`) es HTML, CSS y JavaScript sin
dependencias.

| Archivo | Qué es |
|---|---|
| `src/index.js` | API REST, rutas del equipo y del navegador, limpieza diaria |
| `src/equipo.js` | Durable Object «Equipo» |
| `src/auth.js` | usuarios y sesiones |
| `migrations/` | esquema de D1 |
| `public/` | la app web |

Probar en el PC: `npm install`, `npm run db:local`, copiar `.dev.vars.example` como `.dev.vars` y `npm run dev`.
Publicar: [`docs/software/GUIA_INSTALACION.md`](../docs/software/GUIA_INSTALACION.md), parte B.
