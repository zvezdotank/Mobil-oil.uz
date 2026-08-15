// Relay for mobil-oil.uz contact forms -> Telegram group.
// Runs on Cloudflare Workers. The bot token lives in the Worker secrets
// and never touches the site source, which is public on GitHub Pages.
// The site posts a plain HTML form; this relay forwards it to Telegram
// and redirects the visitor to the thank-you page, so the site itself
// still needs no JavaScript.
//
// Secrets: BOT_TOKEN (from @BotFather), CHAT_ID (group id, starts with -)
//
// NB: every Russian string below is written as \uXXXX escapes on purpose.
// This file gets pasted into the Cloudflare editor through the clipboard,
// and that path has already mangled raw UTF-8 once. ASCII-only source
// cannot be corrupted that way.

const SITE = 'https://mobil-oil.uz';

// Accept forms only from our own site, otherwise the relay address gets
// found and the group is flooded with junk.
const ALLOWED = ['https://mobil-oil.uz', 'https://www.mobil-oil.uz'];

// Telegram chokes on unbalanced tags, so neutralise anything the visitor typed.
const esc = (v) => String(v || '').replace(/[<>&]/g, (c) => ({ '<': '\u2039', '>': '\u203a', '&': '&amp;' }[c]));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // One-off setup helper: prints the ids of chats the bot can see.
    // Works only while CHAT_ID is unset, so it switches itself off
    // and the token never has to be typed into a browser address bar.
    if (url.pathname === '/setup') {
      if (env.CHAT_ID) return new Response('Already configured: CHAT_ID is set.', { status: 403 });
      const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/getUpdates`);
      const data = await r.json();
      if (!data.ok) {
        return new Response(
          'Telegram rejected the token. Check the BOT_TOKEN secret.\n\n' + JSON.stringify(data, null, 1),
          { headers: { 'content-type': 'text/plain; charset=utf-8' } });
      }
      const chats = {};
      for (const u of data.result || []) {
        const c = u.message?.chat || u.my_chat_member?.chat;
        if (c) chats[c.id] = `${c.title || c.username || c.first_name || ''} (${c.type})`;
      }
      const found = Object.entries(chats).map(([id, t]) => `${id}   ${t}`).join('\n');
      return new Response(
        found ? 'Chats found:\n\n' + found + '\n\nTake the group id (the one with a minus) and add it as the CHAT_ID secret.'
              : 'No chats visible yet. Add the bot to the group, send any message there, then reload this page.',
        { headers: { 'content-type': 'text/plain; charset=utf-8' } });
    }

    if (request.method !== 'POST') return Response.redirect(SITE, 302);

    const from = request.headers.get('Origin') || request.headers.get('Referer') || '';
    if (!ALLOWED.some((o) => from.startsWith(o))) return new Response('Forbidden', { status: 403 });

    const form = await request.formData();

    // Honeypot: the field is hidden in the markup, a human never fills it.
    if (form.get('company_site')) return Response.redirect(SITE + '/spasibo.html', 303);

    const phone = (form.get('phone') || '').toString().trim();
    if (!phone) return Response.redirect(SITE + '/?error=phone', 303);

    const titles = {
      name: '\u041a\u043e\u043d\u0442\u0430\u043a\u0442\u043d\u043e\u0435 \u043b\u0438\u0446\u043e',
      phone: '\u0422\u0435\u043b\u0435\u0444\u043e\u043d',
      task: '\u0427\u0442\u043e \u043d\u0443\u0436\u043d\u043e',
      type: '\u0422\u0438\u043f \u0442\u0435\u0445\u043d\u0438\u043a\u0438',
      spec: '\u041c\u043e\u0434\u0435\u043b\u044c \u0438\u043b\u0438 \u0434\u043e\u043f\u0443\u0441\u043a',
      volume: '\u041e\u0431\u044a\u0451\u043c \u0432 \u043c\u0435\u0441\u044f\u0446',
      car: '\u041c\u0430\u0440\u043a\u0430 \u0438 \u043c\u043e\u0434\u0435\u043b\u044c',
      mileage: '\u041f\u0440\u043e\u0431\u0435\u0433'
    };

    const source = esc((form.get('_form') || '\u0444\u043e\u0440\u043c\u0430').toString());
    const lines = ['\ud83d\udd14 \u0417\u0430\u044f\u0432\u043a\u0430 \u0441 \u0441\u0430\u0439\u0442\u0430 \u2014 ' + source, ''];
    for (const [key, title] of Object.entries(titles)) {
      const value = esc((form.get(key) || '').toString().trim());
      if (value) lines.push(`${title}: ${value}`);
    }
    lines.push('', new Date().toLocaleString('ru-RU', { timeZone: 'Asia/Tashkent' }));

    await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: env.CHAT_ID, text: lines.join('\n'), disable_web_page_preview: true }),
    });

    return Response.redirect(SITE + '/spasibo.html', 303);
  },
};
