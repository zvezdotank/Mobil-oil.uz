/* Google Analytics 4 для mobil-oil.uz.
 *
 * Сайт работает без JavaScript, это единственный скрипт на нём. Поэтому
 * он устроен так, чтобы ничего не ломать: пока идентификатор не вписан,
 * файл не грузит вообще ничего, а все обработчики висят на document —
 * им не важно, в каком порядке отрисовалась страница.
 *
 * Идентификатор берётся из счётчика в интерфейсе GA4 (Администратор →
 * Потоки данных → веб-поток), выглядит как G-XXXXXXXXXX. Он не секрет:
 * его и так видно в исходном коде любой страницы с аналитикой.
 */
var GA_ID = '';

(function () {
  'use strict';
  if (!GA_ID) return;                       // счётчик ещё не заведён — молчим

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;

  gtag('js', new Date());
  gtag('config', GA_ID, {
    // язык страницы уходит с каждым событием: видно, какая версия приносит заявки
    site_language: document.documentElement.lang || 'ru'
  });

  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA_ID);
  document.head.appendChild(s);

  /* Где на странице нажали — чтобы потом понять, какая кнопка работает.
     Идём вверх по дереву до первого узнаваемого блока. */
  var PLACES = [
    ['.bar', 'bottom_bar'],          // нижняя панель на телефоне
    ['.mgr', 'manager_card'],        // плавающая карточка менеджера
    ['.nextstep', 'brands_block'],   // блок «подбор по марке»
    ['.tfoot', 'price_table'],       // подвал таблицы с ценами
    ['.hero', 'hero'],               // первый экран
    ['.header', 'header'],
    ['.contacts', 'contacts'],
    ['.footer', 'footer']
  ];

  function placeOf(el) {
    for (var i = 0; i < PLACES.length; i++) {
      if (el.closest(PLACES[i][0])) return PLACES[i][1];
    }
    return 'other';
  }

  function send(name, params) {
    params = params || {};
    params.site_language = document.documentElement.lang || 'ru';
    gtag('event', name, params);
  }

  /* Один обработчик на все ссылки: работает и внутри <details>,
     которые раскрываются уже после загрузки. */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var place = placeOf(a);

    // переключатель языка: активная сторона — <span>, кликается только соседняя <a>
    if (a.closest('.lang')) {
      send('switch_language', {
        from: document.documentElement.lang || 'ru',
        to: a.getAttribute('hreflang') || 'ru'
      });
      return;
    }

    if (href.indexOf('tel:') === 0)            send('click_phone',     { placement: place });
    else if (href.indexOf('mailto:') === 0)    send('click_email',     { placement: place });
    else if (href.indexOf('t.me/') > -1)       send('click_telegram',  { placement: place });
    else if (href.indexOf('uzum.uz') > -1)     send('click_uzum',      { placement: place });
    else if (href.indexOf('instagram.com') > -1) send('click_instagram', { placement: place });
    else if (href.indexOf('yandex.com/maps') > -1) send('click_map',   { placement: place });
  }, true);

  /* Что человек раскрывал на странице. Событие toggle не всплывает,
     поэтому слушаем на этапе погружения — так один обработчик ловит все. */
  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d.open) return;                      // закрытие не считаем
    if (d.classList.contains('qa')) {
      var q = d.querySelector('summary');
      send('faq_open', { question: q ? q.textContent.replace('+', '').trim().slice(0, 90) : '' });
    } else if (d.closest('.mgr')) {
      send('manager_open', {});
    }
  }, true);

  /* Фильтр каталога: по какой группе товаров смотрят чаще. */
  document.addEventListener('change', function (e) {
    var i = e.target;
    if (!i || i.name !== 'filter') return;
    var l = document.querySelector('label[for="' + i.id + '"]');
    send('catalog_filter', { group: l ? l.textContent.trim() : i.id });
  }, true);

  /* Отправка формы. Имя формы лежит в скрытом поле _form — том же,
     что уходит в телеграм, так что заявки в GA и в группе называются
     одинаково и их можно сверить. */
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f || f.tagName !== 'FORM') return;
    var nameField = f.querySelector('input[name="_form"]');
    send('generate_lead', {
      form_name: nameField ? nameField.value : 'форма без имени',
      page_path: location.pathname
    });
  }, true);
})();
