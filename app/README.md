# App web del EVSE Monitor (Firebase)

Firebase en el plan Spark (gratis): **Authentication** para los usuarios y una cuenta por equipo, **Realtime Database** con reglas de seguridad para todo lo demás y **Hosting** para la página. Sin servidor propio ni paso de compilación (D24, D31). Diseño: tablero eléctrico futurista (D32, `../DESIGN.md`).

| Archivo | Qué es |
|---|---|
| `public/index.html`, `estilo.css` | página y sistema visual (riel DIN, módulos, pilotos, tema día/noche) |
| `public/app.js` | rutas y pantallas: entrar, equipos, panel, historial, alarmas, ajustes, perfil, administración |
| `public/fb.js` | capa de datos: SDK web de Firebase 13.4, órdenes con confirmación, alta de equipos y código de enlace, OTA en partes |
| `public/instrumentos.js` | mímico del circuito, medidor de aguja, selector K1, rodillos, termómetro, secuencia de encendido |
| `public/grafica.js` | gráficas en canvas (series y barras por día) |
| `database.rules.json` | reglas de seguridad por ruta (quién lee y escribe qué) |
| `firebase.json` | Hosting, reglas y emuladores |
| `pruebas/probar_reglas.mjs` | 64 casos contra el emulador (`npm run probar`) |

Comandos (dentro de `app\`):

```powershell
npm install
```

```powershell
npm run emular
```

```powershell
npm run probar
```

```powershell
npm run desplegar
```

`emular` levanta Authentication, Realtime Database y Hosting en tu PC (necesita Java 21 en el PATH); `probar` corre las pruebas de las reglas con el emulador abierto; `desplegar` publica las reglas y la app en tu proyecto (antes, `npx firebase login` y `npx firebase use --add`).

Paso a paso completo: [docs/software/GUIA_INSTALACION.md](../docs/software/GUIA_INSTALACION.md), parte B (publicar) y parte E (emulador y simulador). Rutas de la base: [docs/software/PROTOCOLO_MENSAJES.md](../docs/software/PROTOCOLO_MENSAJES.md).
