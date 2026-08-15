// Приёмник заявок с сайта mobil-oil.uz.
// Живёт в Cloudflare Workers, токен бота хранится там же в секретах
// и в код никогда не попадает. Сайт отправляет обычную форму,
// воркер пересылает её в телеграм-группу и возвращает человека
// на страницу «спасибо» — поэтому на сайте по-прежнему нет JavaScript.

const SITE = 'https://mobil-oil.uz';

// Принимаем формы только со своего сайта: иначе адрес воркера найдут
// и завалят группу мусором. Приём из sales-hub/tools/telegram-worker.js.
const ALLOWED = ['https://mobil-oil.uz', 'https://www.mobil-oil.uz'];

// Телеграм ломается на несбалансированных тегах, поэтому чистим всё,
// что пришло от посетителя.
const esc = (v) => String(v || '').replace(/[<>&]/g, (c) => ({ '<': '‹', '>': '›', '&': '&amp;' }[c]));

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Разовая помощь при настройке: показывает ID групп, куда добавлен бот.
    // Работает только пока CHAT_ID не задан — после настройки сама отключается,
    // поэтому токен не нужно вбивать в адресную строку браузера.
    if (url.pathname === '/setup') {
      if (env.CHAT_ID) return new Response('Уже настроено: CHAT_ID задан.', { status: 403 });
      const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/getUpdates`);
      const data = await r.json();
      if (!data.ok) {
        return new Response('Телеграм отклонил токен. Проверьте BOT_TOKEN.\n\n' +
          JSON.stringify(data, null, 1), { headers: { 'content-type': 'text/plain; charset=utf-8' } });
      }
      const chats = {};
      for (const u of data.result || []) {
        const c = u.message?.chat || u.my_chat_member?.chat;
        if (c) chats[c.id] = `${c.title || c.username || c.first_name || ''} (${c.type})`;
      }
      const found = Object.entries(chats).map(([id, t]) => `${id}   ${t}`).join('\n');
      return new Response(
        found ? 'Найденные чаты:\n\n' + found + '\n\nВозьмите ID группы (с минусом) и выполните:\n  npx wrangler secret put CHAT_ID'
              : 'Чатов не видно. Добавьте бота в группу, напишите там любое сообщение и обновите страницу.',
        { headers: { 'content-type': 'text/plain; charset=utf-8' } });
    }

    if (request.method !== 'POST') return Response.redirect(SITE, 302);

    const from = request.headers.get('Origin') || request.headers.get('Referer') || '';
    if (!ALLOWED.some((o) => from.startsWith(o))) {
      return new Response('Forbidden', { status: 403 });
    }

    const form = await request.formData();

    // Ловушка для роботов: поле спрятано в вёрстке, человек его не заполнит.
    if (form.get('company_site')) return Response.redirect(SITE + '/spasibo.html', 303);

    const phone = (form.get('phone') || '').toString().trim();
    if (!phone) return Response.redirect(SITE + '/?error=phone', 303);

    const titles = {
      name: 'Контактное лицо',
      phone: 'Телефон',
      task: 'Что нужно',
      type: 'Тип техники',
      spec: 'Модель или допуск',
      volume: 'Объём в месяц',
      car: 'Марка и модель',
      mileage: 'Пробег',
    };

    const source = esc((form.get('_form') || 'форма').toString());
    const lines = [`🔔 Заявка с сайта — ${source}`, ''];
    for (const [key, title] of Object.entries(titles)) {
      const value = esc((form.get(key) || '').toString().trim());
      if (value) lines.push(`${title}: ${value}`);
    }
    lines.push('', new Date().toLocaleString('ru-RU', { timeZone: 'Asia/Tashkent' }));

    await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        chat_id: env.CHAT_ID,
        text: lines.join('\n'),
        disable_web_page_preview: true,
      }),
    });

    return Response.redirect(SITE + '/spasibo.html', 303);
  },
};
