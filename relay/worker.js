// Приёмник заявок с сайта mobil-oil.uz.
// Живёт в Cloudflare Workers, токен бота хранится там же в секретах
// и в код никогда не попадает. Сайт отправляет обычную форму,
// воркер пересылает её в телеграм-группу и возвращает человека
// на страницу «спасибо» — поэтому на сайте по-прежнему нет JavaScript.

const SITE = 'https://mobil-oil.uz';

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return Response.redirect(SITE, 302);

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

    const source = (form.get('_form') || 'форма').toString();
    const lines = [`🔔 Заявка с сайта — ${source}`, ''];
    for (const [key, title] of Object.entries(titles)) {
      const value = (form.get(key) || '').toString().trim();
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
