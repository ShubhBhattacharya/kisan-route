document.addEventListener('DOMContentLoaded', function () {

  /* ---------------- Topbar Left Navigation Setup ---------------- */
  var brand = document.querySelector('.topbar .brand');
  var topbarRight = document.querySelector('.topbar-right');
  var sideMenu = document.getElementById('sideMenu');

  if (topbarRight) {
    // 1. Remove top panel language selector if present
    var langSelect = topbarRight.querySelector('#langSelect');
    if (langSelect) {
      langSelect.remove();
    }

    // 2. Remove old right-side injected About button if it exists
    var oldAbout = document.getElementById('injectedTopbarAboutBtn');
    if (oldAbout) {
      oldAbout.remove();
    }
  }

  // 3. Inject Left-Side Navigation Group beside the brand logo (Desktop Only)
  if (brand && !document.getElementById('leftNavGroup')) {
    brand.style.marginRight = '12px';

    var navGroup = document.createElement('div');
    navGroup.id = 'leftNavGroup';
    navGroup.className = 'desktop-only-nav';
    
    navGroup.innerHTML = `
      <a href="/" class="btn-ghost"><span style="font-size: 14px;">🏠</span> Home</a>
      <a href="/farmer/login" class="btn-ghost"><span style="font-size: 14px;">🌾</span>Farmer</a>
      <a href="/cluster/login" class="btn-ghost"><span style="font-size: 14px;">🌐</span>Cluster</a>
      <a href="/driver/login" class="btn-ghost"><span style="font-size: 14px;">🚚</span>Driver</a>
      <a href="/wholesaler/login" class="btn-ghost"><span style="font-size: 14px;">🛒</span>Wholesaler</a>
      <a href="/about" class="btn-ghost"><span style="font-size: 14px;">ℹ️</span> About</a>
    `;

    brand.after(navGroup);
  }

  /* ---------------- Dynamic Blurred Image Background for Auth Pages ---------------- */
  var authSection = document.querySelector('.auth-section') || document.querySelector('.auth-card');
  if (authSection && !document.getElementById('authBlurredBg')) {
    var bgWrapper = document.createElement('div');
    bgWrapper.id = 'authBlurredBg';
    bgWrapper.className = 'auth-bg-wrapper';
    
    var pageText = authSection.innerText.toLowerCase();
    var path = window.location.pathname.toLowerCase();
    var bgImage = '/static/images/default_bg.jpg';

    if (pageText.includes('farmer') || path.includes('cluster')) {
      bgImage = '/static/images/farmer_bg.jpg';
    } else if (pageText.includes('customer') || pageText.includes('wholesaler')) {
      bgImage = '/static/images/customer_bg.jpg';
    } else if (pageText.includes('driver')) {
      bgImage = '/static/images/driver_bg.jpg';
    }

    bgWrapper.innerHTML = '<div class="auth-bg-inner" style="background-image: url(\'' + bgImage + '\');"></div>';
    document.body.appendChild(bgWrapper);
  }

  /* ---------------- Three-dot side menu toggle ---------------- */
  var menuToggle = document.getElementById('menuToggle');
  var overlay = document.getElementById('menuOverlay');

  function openMenu() {
    if (!sideMenu) return;
    sideMenu.classList.add('open');
    if (overlay) overlay.classList.add('visible');
    if (menuToggle) menuToggle.setAttribute('aria-expanded', 'true');
    sideMenu.setAttribute('aria-hidden', 'false');
  }

  function closeMenu() {
    if (!sideMenu) return;
    sideMenu.classList.remove('open');
    if (overlay) overlay.classList.remove('visible');
    if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
    sideMenu.setAttribute('aria-hidden', 'true');
  }

  if (menuToggle && sideMenu && overlay) {
    menuToggle.addEventListener('click', function () {
      sideMenu.classList.contains('open') ? closeMenu() : openMenu();
    });
    overlay.addEventListener('click', closeMenu);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMenu();
    });
  }

  /* ---------------- Chatbot ---------------- */
  var chatbotToggle = document.getElementById('chatbotToggle');
  var chatbotPanel = document.getElementById('chatbotPanel');
  var chatbotClose = document.getElementById('chatbotClose');
  var chatbotPrompts = document.getElementById('chatbotPrompts');
  var chatbotMessages = document.getElementById('chatbotMessages');
  var promptsLoaded = false;

  function openChatbot() {
    if (!chatbotPanel) return;
    chatbotPanel.removeAttribute('hidden');
    chatbotPanel.style.display = 'flex';
    if (chatbotToggle) chatbotToggle.setAttribute('aria-expanded', 'true');
    loadPrompts();
  }

  function closeChatbot() {
    if (!chatbotPanel) return;
    chatbotPanel.setAttribute('hidden', '');
    chatbotPanel.style.display = 'none';
    if (chatbotToggle) chatbotToggle.setAttribute('aria-expanded', 'false');
  }

  function loadPrompts() {
    if (promptsLoaded || !chatbotPrompts) return;
    fetch('/api/chatbot/prompts')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        promptsLoaded = true;
        (data.prompts || []).forEach(function (p) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'chatbot-prompt';
          btn.textContent = p;
          btn.addEventListener('click', function () { askChatbot(p); });
          chatbotPrompts.appendChild(btn);
        });
      })
      .catch(function () { /* Offline demo fallback */ });
  }

  function addMessage(text, who) {
    if (!chatbotMessages) return;
    var el = document.createElement('div');
    el.className = 'chat-msg ' + (who === 'user' ? 'chat-msg-user' : 'chat-msg-bot');
    el.textContent = text;
    chatbotMessages.appendChild(el);
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
  }

  function askChatbot(question) {
    addMessage(question, 'user');
    fetch('/api/chatbot/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) { addMessage(data.reply, 'bot'); })
      .catch(function () {
        addMessage('This demo assistant needs the Flask server running to answer.', 'bot');
      });
  }

  if (chatbotToggle && chatbotPanel) {
    chatbotToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var isClosed = chatbotPanel.hasAttribute('hidden') || chatbotPanel.style.display === 'none' || window.getComputedStyle(chatbotPanel).display === 'none';
      if (isClosed) {
        openChatbot();
      } else {
        closeChatbot();
      }
    });
  }

  if (chatbotClose) {
    chatbotClose.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      closeChatbot();
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && chatbotPanel && !chatbotPanel.hasAttribute('hidden')) {
      closeChatbot();
    }
  });

  /* ---------------- Voice Assistant ---------------- */
  var voiceBtn = document.getElementById('voiceBtn');
  var voiceCaption = document.getElementById('voiceCaption');
  if (voiceBtn) {
    var speaking = false;
    voiceBtn.addEventListener('click', function () {
      var text = voiceBtn.getAttribute('data-voice-text') || 'Welcome to Kisan Route.';

      if (speaking) {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        speaking = false;
        voiceBtn.setAttribute('aria-pressed', 'false');
        if (voiceCaption) voiceCaption.setAttribute('hidden', '');
        return;
      }

      if (voiceCaption) {
        voiceCaption.textContent = text;
        voiceCaption.removeAttribute('hidden');
      }
      voiceBtn.setAttribute('aria-pressed', 'true');

      if ('speechSynthesis' in window) {
        var utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1;
        utter.onend = function () {
          speaking = false;
          voiceBtn.setAttribute('aria-pressed', 'false');
        };
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utter);
        speaking = true;
      } else {
        speaking = false;
      }
    });
  }
});