// Notificaciones por Telegram (D30). El bot lo creas tú con @BotFather; su token va como secreto
// TELEGRAM_TOKEN del Worker y cada usuario pone su «chat id» en su perfil.

export async function telegram(env, chat, texto) {
  if (!env.TELEGRAM_TOKEN || !chat) return false;
  try {
    const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: chat, text: texto, disable_web_page_preview: true }),
    });
    return r.ok;
  } catch {
    return false;
  }
}

// Avisa a todos los usuarios con permiso sobre el equipo que tengan Telegram configurado.
export async function avisarEquipo(env, equipoId, texto) {
  if (!env.TELEGRAM_TOKEN) return 0;
  const { results } = await env.DB.prepare(
    `SELECT DISTINCT u.telegram_chat AS chat FROM usuarios u
     LEFT JOIN permisos p ON p.usuario_id = u.id AND p.equipo_id = ?
     WHERE u.telegram_chat IS NOT NULL AND u.telegram_chat != '' AND (p.equipo_id IS NOT NULL OR u.admin = 1)`,
  )
    .bind(equipoId)
    .all();
  let n = 0;
  for (const { chat } of results) if (await telegram(env, chat, texto)) n++;
  return n;
}
