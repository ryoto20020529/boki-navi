/* 簿記合格ナビ — shared script (no dependencies) */
(function () {
  'use strict';

  // 料金マスタ（税込・1時間あたり）。HTMLの料金表と必ず一致させること
  var PRICES = {
    boki3:   { name: '日商簿記3級',               online: 2000, offline: 2500 },
    boki2:   { name: '日商簿記2級',               online: 2600, offline: 3100 },
    boki1:   { name: '日商簿記1級',               online: 3500, offline: 4000 },
    waseda:  { name: '早稲田会計研究科（アカスク）', online: 4000, offline: 4500 }
  };
  var yen = function (n) { return n.toLocaleString('ja-JP'); };

  // ---- Mobile menu ----
  var menuBtn = document.querySelector('.menu-btn');
  var nav = document.getElementById('gnav');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('open');
        menuBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ---- Online / 対面 switch on price tables ----
  document.querySelectorAll('[data-mode-switch]').forEach(function (sw) {
    var target = document.getElementById(sw.getAttribute('data-mode-switch'));
    sw.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        sw.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
        btn.setAttribute('aria-pressed', 'true');
        if (target) target.setAttribute('data-mode', btn.value);
      });
    });
  });

  // ---- Monthly fee simulator ----
  var sim = document.getElementById('sim');
  if (sim) {
    var sService = sim.querySelector('#simService');
    var sCount = sim.querySelector('#simCount');
    var sCountOut = sim.querySelector('#simCountOut');
    var sMonthly = sim.querySelector('#simMonthly');
    var sDetail = sim.querySelector('#simDetail');
    var mode = 'online';
    var calc = function () {
      var p = PRICES[sService.value];
      var unit = p[mode];
      var n = parseInt(sCount.value, 10);
      sCountOut.textContent = n;
      sMonthly.textContent = yen(unit * n);
      sDetail.textContent = p.name + '（' + (mode === 'online' ? 'オンライン' : '対面') + '）' + yen(unit) + '円 × 月' + n + 'コマ';
    };
    sim.querySelectorAll('.seg button').forEach(function (b) {
      b.addEventListener('click', function () {
        sim.querySelectorAll('.seg button').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        mode = b.value;
        calc();
      });
    });
    sService.addEventListener('change', calc);
    sCount.addEventListener('input', calc);
    calc();
  }

  // ---- Sticky CTA (mobile): hero 通過後に表示、フォーム付近では隠す ----
  var sticky = document.querySelector('.sticky-cta');
  if (sticky) {
    var hero = document.querySelector('.hero, .sub-hero');
    var contact = document.getElementById('contact');
    var onScroll = function () {
      var y = window.scrollY;
      var heroEnd = hero ? hero.offsetTop + hero.offsetHeight - 80 : 400;
      var nearContact = contact && y + window.innerHeight > contact.offsetTop + 120 && y < contact.offsetTop + contact.offsetHeight;
      sticky.classList.toggle('show', y > heroEnd && !nearContact);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ---- Scroll reveal ----
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var targets = document.querySelectorAll('.reason, .course, .case, .tutor, .flow li, .worries li, .zero-list li');
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('visible'); obs.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    targets.forEach(function (el) { el.classList.add('reveal'); obs.observe(el); });
  }

  // ---- Contact form (Web3Forms) ----
  var form = document.getElementById('contactForm');
  if (!form) return;
  var WEB3FORMS_KEY = 'f1c86e88-7827-4301-9287-d58694f2aa48';

  // ?service=boki2 などで希望サービスを事前選択（科目別ページからの導線）
  var qs = new URLSearchParams(location.search).get('service');
  if (qs && form.service.querySelector('option[value="' + qs + '"]')) form.service.value = qs;

  var msg = form.message;
  var counter = document.getElementById('charCount');
  msg.addEventListener('input', function () {
    var c = msg.value.length;
    counter.textContent = c + ' / 1000文字';
    counter.className = 'char-count' + (c > 900 ? ' warn' : '');
  });

  var CONTACT_EMAIL = 'wasecpa.academy@gmail.com';
  var ERR_TEXT = {
    'err-name': 'お名前を入力してください',
    'err-email': '正しいメールアドレスを入力してください',
    'err-service': 'コースを選択してください',
    'err-message': 'ご相談内容を入力してください',
    'err-privacy': 'プライバシーポリシーへの同意が必要です'
  };
  // メッセージ類はHTMLに書かず、必要になった時だけ表示する（初回表示で誤解を生まないため）
  var showErr = function (id, show) {
    var el = document.getElementById(id);
    el.textContent = show ? ERR_TEXT[id] : '';
    el.hidden = !show;
  };

  var validate = function () {
    var ok = true;
    [
      { el: form.name, err: 'err-name', check: function (v) { return v.trim().length > 0; } },
      { el: form.email, err: 'err-email', check: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); } },
      { el: form.service, err: 'err-service', check: function (v) { return v !== ''; } },
      { el: form.message, err: 'err-message', check: function (v) { return v.trim().length > 0; } }
    ].forEach(function (f) {
      var good = f.check(f.el.value);
      f.el.classList.toggle('error', !good);
      f.el.setAttribute('aria-invalid', good ? 'false' : 'true');
      showErr(f.err, !good);
      if (!good) ok = false;
    });
    var consent = document.getElementById('privacyConsent');
    showErr('err-privacy', !consent.checked);
    if (!consent.checked) ok = false;
    return ok;
  };

  var errorBar = document.getElementById('errorBar');
  var formView = document.getElementById('formView');
  var successView = document.getElementById('successView');

  var mailtoHref = function () {
    var serviceLabel = form.service.value ? form.service.options[form.service.selectedIndex].text : '未選択';
    var body = 'お名前：' + form.name.value + '\nメールアドレス：' + form.email.value + '\nご希望のコース：' + serviceLabel +
      '\n受講形式：' + form.lesson_mode.value + '\n目標試験日：' + (form.exam_date.value || '未定') + '\n\nご相談内容：\n' + form.message.value;
    return 'mailto:' + CONTACT_EMAIL + '?subject=' + encodeURIComponent('【簿記合格ナビ】無料相談') + '&body=' + encodeURIComponent(body);
  };

  var showSendError = function () {
    var offline = navigator.onLine === false;
    errorBar.innerHTML =
      '<b>送信できませんでした</b>' +
      (offline ? 'インターネットに接続されていないようです。接続を確認してから、もう一度お試しください。' : '通信状況などにより、送信が完了しませんでした。') +
      '<ul><li>入力内容はそのまま残っています</li><li>少し時間をおいて「もう一度送信する」を押してください</li><li>繰り返し失敗する場合は、入力内容を入れたメールを作成できます</li></ul>' +
      '<div class="actions"><button type="button" class="retry">もう一度送信する</button><a class="mail"></a></div>';
    var mail = errorBar.querySelector('.mail');
    mail.textContent = 'メールで送る（入力内容つき）';
    mail.href = mailtoHref();
    errorBar.querySelector('.retry').addEventListener('click', function () {
      if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event('submit', { cancelable: true }));
    });
    errorBar.hidden = false;
    errorBar.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  var showSuccess = function () {
    successView.innerHTML =
      '<div class="ok" aria-hidden="true">✓</div><h3>送信が完了しました</h3>' +
      '<p>お問い合わせありがとうございます。<b>24時間以内</b>にご入力のメールアドレスへご返信します。</p>' +
      '<p class="small-note">返信が届かない場合は、迷惑メールフォルダをご確認いただくか ' + CONTACT_EMAIL + ' までご連絡ください。</p>' +
      '<button type="button" class="link-btn">別の内容で問い合わせる</button>';
    successView.querySelector('.link-btn').addEventListener('click', function () {
      successView.hidden = true; successView.innerHTML = '';
      formView.hidden = false;
    });
    formView.hidden = true;
    successView.hidden = false;
    successView.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (form._gotcha.value) return;
    if (!validate()) {
      var first = form.querySelector('.error, #privacyConsent:not(:checked)');
      if (first) first.focus();
      return;
    }
    var btn = document.getElementById('submitBtn');
    var spinner = document.getElementById('spinner');
    var label = document.getElementById('submitLabel');
    btn.disabled = true; spinner.style.display = 'block'; label.textContent = '送信中...';
    errorBar.hidden = true; errorBar.innerHTML = '';

    var serviceLabel = form.service.options[form.service.selectedIndex].text;
    fetch('https://api.web3forms.com/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        access_key: WEB3FORMS_KEY,
        subject: '【簿記合格ナビ】お問い合わせ：' + form.name.value + '様',
        from_name: '簿記合格ナビ お問い合わせフォーム',
        name: form.name.value,
        email: form.email.value,
        service: serviceLabel,
        lesson_mode: form.lesson_mode.value,
        exam_date: form.exam_date.value || '未定',
        message: form.message.value,
        page: location.pathname
      })
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.success) throw new Error(data.message);
      showSuccess();
      form.reset();
      counter.textContent = '0 / 1000文字';
    }).catch(showSendError).then(function () {
      btn.disabled = false; spinner.style.display = 'none'; label.textContent = '無料で相談を送信する';
    });
  });
})();
