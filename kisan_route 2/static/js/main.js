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
    var navGroup = document.createElement('div');
    navGroup.id = 'leftNavGroup';
    navGroup.className = 'desktop-only-nav';
    
    navGroup.innerHTML = `
      <a href="/" class="btn-ghost"><span style="font-size: 14px;">🏠</span> Home</a>
      <a href="/farmer/login" class="btn-ghost"><span style="font-size: 14px;">🌾</span> Farmer</a>
      <a href="/cluster/login" class="btn-ghost"><span style="font-size: 14px;">🤝</span> Cluster</a>
      <a href="/customer/login" class="btn-ghost"><span style="font-size: 14px;">🛒</span> Customer</a>
      <a href="/driver/login" class="btn-ghost"><span style="font-size: 14px;">🚚</span> Driver</a>
      <a href="/wholesaler/login" class="btn-ghost"><span style="font-size: 14px;">🏬</span> Wholesaler</a>
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
    var bgImage = '/static/images/background.jpg';

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
    
    var urlRegex = /(https?:\/\/[^\s]+)/g;
    if (who === 'bot' && urlRegex.test(text)) {
      el.innerHTML = '';
      var parts = text.split(urlRegex);
      parts.forEach(function(part) {
        if (part.match(urlRegex)) {
          var a = document.createElement('a');
          a.href = part;
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          a.textContent = part;
          a.style.color = '#1b5e20';
          a.style.fontWeight = '700';
          a.style.textDecoration = 'underline';
          a.style.wordBreak = 'break-all';
          el.appendChild(a);

          if (part.indexOf('youtu') !== -1) {
            var btnContainer = document.createElement('div');
            btnContainer.style.marginTop = '8px';
            var ytBtn = document.createElement('a');
            ytBtn.href = part;
            ytBtn.target = '_blank';
            ytBtn.rel = 'noopener noreferrer';
            ytBtn.textContent = '▶️ Watch App Demo on YouTube (वीडियो देखें)';
            ytBtn.style.display = 'inline-block';
            ytBtn.style.background = '#e53935';
            ytBtn.style.color = '#ffffff';
            ytBtn.style.padding = '6px 12px';
            ytBtn.style.borderRadius = '8px';
            ytBtn.style.fontSize = '12px';
            ytBtn.style.fontWeight = '700';
            ytBtn.style.textDecoration = 'none';
            ytBtn.style.boxShadow = '0 2px 6px rgba(229,57,53,0.3)';
            btnContainer.appendChild(ytBtn);
            el.appendChild(btnContainer);
          }
        } else {
          var lines = part.split('\n');
          lines.forEach(function(line, idx) {
            if (idx > 0) el.appendChild(document.createElement('br'));
            el.appendChild(document.createTextNode(line));
          });
        }
      });
    } else {
      var lines = text.split('\n');
      lines.forEach(function(line, idx) {
        if (idx > 0) el.appendChild(document.createElement('br'));
        el.appendChild(document.createTextNode(line));
      });
    }
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

  /* ---------------- Intelligent AI Voice Assistant ---------------- */
  (function initKisanVoiceAssistant() {
    var voiceBtn = document.getElementById('voiceBtn');
    var voiceCaption = document.getElementById('voiceCaption');
    var headerTitle = document.getElementById('krVoiceHeaderTitle');
    var liveDot = document.getElementById('krVoiceLiveDot');
    var waveBox = document.getElementById('krVoiceWave');
    var contentBox = document.getElementById('krVoiceContent');
    var actionWrap = document.getElementById('krVoiceActionWrap');
    var closeBtn = document.getElementById('krVoiceCloseBtn');

    if (!voiceBtn) return;

    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recognition = null;
    var isListening = false;
    var isSpeaking = false;
    var navTimeout = null;

    // Preload speech synthesis voices (fixes Chrome voice loading delay)
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = function () {
          window.speechSynthesis.getVoices();
        };
      }
    }

    function setVisualState(state, text) {
      if (!voiceCaption) return;

      if (state === 'hidden') {
        voiceCaption.setAttribute('hidden', '');
        voiceBtn.setAttribute('aria-pressed', 'false');
        voiceBtn.classList.remove('kr-voice-listening', 'kr-voice-speaking');
        if (waveBox) waveBox.style.display = 'none';
        if (actionWrap) actionWrap.style.display = 'none';
        return;
      }

      voiceCaption.removeAttribute('hidden');

      if (state === 'listening') {
        voiceBtn.setAttribute('aria-pressed', 'true');
        voiceBtn.classList.add('kr-voice-listening');
        voiceBtn.classList.remove('kr-voice-speaking');
        if (headerTitle) headerTitle.textContent = 'Listening / सुन रहे हैं...';
        if (liveDot) liveDot.style.background = '#ef4444';
        if (waveBox) waveBox.style.display = 'flex';
        if (contentBox) contentBox.textContent = text || '🎙️ बोलिए, मैं सुन रहा हूँ... (Listening...)';
        if (actionWrap) actionWrap.style.display = 'none';
      } else if (state === 'thinking') {
        voiceBtn.classList.remove('kr-voice-listening', 'kr-voice-speaking');
        if (headerTitle) headerTitle.textContent = 'Thinking / उत्तर तैयार कर रहे हैं...';
        if (liveDot) liveDot.style.background = '#f59e0b';
        if (waveBox) waveBox.style.display = 'none';
        if (contentBox) contentBox.textContent = text || '⏳ सोच रहे हैं...';
      } else if (state === 'speaking') {
        voiceBtn.setAttribute('aria-pressed', 'true');
        voiceBtn.classList.add('kr-voice-speaking');
        voiceBtn.classList.remove('kr-voice-listening');
        if (headerTitle) headerTitle.textContent = 'KisanRoute AI Voice';
        if (liveDot) liveDot.style.background = '#10b981';
        if (waveBox) waveBox.style.display = 'flex';
        if (contentBox && text) contentBox.textContent = text;
      } else if (state === 'idle') {
        voiceBtn.setAttribute('aria-pressed', 'false');
        voiceBtn.classList.remove('kr-voice-listening', 'kr-voice-speaking');
        if (headerTitle) headerTitle.textContent = 'KisanRoute Voice';
        if (liveDot) liveDot.style.background = '#2e7d32';
        if (waveBox) waveBox.style.display = 'none';
        if (contentBox && text) contentBox.textContent = text;
      }
    }

    function stopAll() {
      if (recognition && isListening) {
        try { recognition.abort(); } catch (e) {}
      }
      isListening = false;

      if ('speechSynthesis' in window) {
        try { window.speechSynthesis.cancel(); } catch (e) {}
      }
      isSpeaking = false;
      if (navTimeout) { clearTimeout(navTimeout); navTimeout = null; }
      setVisualState('hidden');
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        stopAll();
      });
    }

    function executeVoiceAction(action) {
      if (!action || !action.url) return;
      if (action.type === 'navigate') {
        if (typeof window.triggerKisanTransition === 'function') {
          window.triggerKisanTransition({ url: action.url, label: action.label || 'डैशबोर्ड' });
        } else {
          window.location.href = action.url;
        }
      }
    }

    function speakReply(replyData) {
      var spokenText = replyData.spoken_reply || replyData.reply || '';
      var displayReply = replyData.reply || spokenText;
      var lang = replyData.lang || 'hi-IN';
      var action = replyData.action || null;

      setVisualState('speaking', displayReply);

      if (action && actionWrap) {
        actionWrap.innerHTML = '<a href="' + action.url + '" class="kr-voice-action-pill" id="krVoiceActionLink">' + (action.label || 'पेज खोलें') + ' &rarr;</a>';
        actionWrap.style.display = 'block';
        var actionLink = document.getElementById('krVoiceActionLink');
        if (actionLink) {
          actionLink.addEventListener('click', function (e) {
            e.preventDefault();
            stopAll();
            executeVoiceAction(action);
          });
        }
      }

      if (!('speechSynthesis' in window) || !spokenText) {
        isSpeaking = false;
        if (action) {
          setTimeout(function () { executeVoiceAction(action); }, 1500);
        } else {
          setTimeout(function () { setVisualState('idle'); }, 4000);
        }
        return;
      }

      window.speechSynthesis.cancel();

      var utter = new SpeechSynthesisUtterance(spokenText);
      utter.lang = lang;
      utter.rate = 0.95;
      utter.pitch = 1.0;

      // Voice selection
      var voices = window.speechSynthesis.getVoices() || [];
      var chosenVoice = null;

      for (var i = 0; i < voices.length; i++) {
        var v = voices[i];
        var vLang = (v.lang || '').toLowerCase();
        if (lang === 'hi-IN' && (vLang === 'hi-in' || vLang.startsWith('hi'))) {
          chosenVoice = v;
          break;
        } else if (lang === 'en-IN' && (vLang === 'en-in' || vLang.startsWith('en'))) {
          chosenVoice = v;
          if (vLang === 'en-in') break;
        }
      }
      if (chosenVoice) utter.voice = chosenVoice;

      isSpeaking = true;

      // Fallback timer if onend doesn't trigger on mobile browsers
      var safetyMs = Math.max(3000, spokenText.length * 85);
      if (action) {
        navTimeout = setTimeout(function () {
          if (isSpeaking) {
            isSpeaking = false;
            executeVoiceAction(action);
          }
        }, safetyMs + 800);
      } else {
        navTimeout = setTimeout(function () {
          if (isSpeaking) {
            isSpeaking = false;
            setVisualState('idle');
          }
        }, safetyMs + 2000);
      }

      utter.onend = function () {
        isSpeaking = false;
        if (navTimeout) { clearTimeout(navTimeout); navTimeout = null; }
        if (action) {
          setTimeout(function () { executeVoiceAction(action); }, 500);
        } else {
          setTimeout(function () { setVisualState('idle'); }, 2500);
        }
      };

      utter.onerror = function () {
        isSpeaking = false;
        if (navTimeout) { clearTimeout(navTimeout); navTimeout = null; }
        if (action) {
          executeVoiceAction(action);
        } else {
          setVisualState('idle');
        }
      };

      window.speechSynthesis.speak(utter);
    }

    function processVoiceQuery(queryText) {
      setVisualState('thinking', '🔍 "' + queryText + '"');

      fetch('/api/voice/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText })
      })
      .then(function (res) {
        if (!res.ok) throw new Error('Voice server response error: ' + res.status);
        return res.json();
      })
      .then(function (data) {
        speakReply(data);
      })
      .catch(function (err) {
        console.error('Kisan Voice error:', err);
        var fallbackReply = {
          reply: 'माफ़ कीजिए, सर्वर से कनेक्ट करने में समस्या हुई। कृपया दोबारा प्रयास करें।',
          spoken_reply: 'माफ़ कीजिए, सर्वर से कनेक्ट करने में समस्या हुई।',
          lang: 'hi-IN'
        };
        speakReply(fallbackReply);
      });
    }

    function startListening() {
      if (!SpeechRecognition) {
        setVisualState('idle', 'आपके ब्राउज़र में वॉइस इनपुट सपोर्ट नहीं है। कृपया Google Chrome या Safari का उपयोग करें।');
        return;
      }

      try {
        if (recognition) {
          try { recognition.abort(); } catch (e) {}
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'hi-IN'; // hi-IN captures both Hindi, Hinglish, and English in India
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.maxAlternatives = 1;

        var finalTranscript = '';

        recognition.onstart = function () {
          isListening = true;
          setVisualState('listening', '🎙️ बोलिए, मैं सुन रहा हूँ... (Listening...)');
        };

        recognition.onresult = function (event) {
          var interim = '';
          for (var i = event.resultIndex; i < event.results.length; ++i) {
            var trans = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += trans;
            } else {
              interim += trans;
            }
          }
          var liveDisplay = finalTranscript || interim || '🎙️ बोलिए...';
          if (contentBox) contentBox.textContent = liveDisplay;
        };

        recognition.onerror = function (event) {
          isListening = false;
          console.warn('SpeechRecognition error:', event.error);
          var msg = 'बोलने में कोई समस्या आई। कृपया दोबारा माइक दबाकर बोलें।';
          if (event.error === 'not-allowed') {
            msg = 'माइक्रोफ़ोन एक्सेस अस्वीकृत है। कृपया ब्राउज़र में माइक परमिशन Allow करें।';
          } else if (event.error === 'no-speech') {
            msg = 'आपकी आवाज़ सुनाई नहीं दी। कृपया माइक दबाकर दोबारा बोलें।';
          }
          setVisualState('idle', msg);
        };

        recognition.onend = function () {
          isListening = false;
          var query = (finalTranscript || '').trim();
          if (query) {
            processVoiceQuery(query);
          } else {
            setTimeout(function () {
              if (!isSpeaking && !isListening) {
                setVisualState('hidden');
              }
            }, 3000);
          }
        };

        recognition.start();
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
        setVisualState('idle', 'माइक शुरू नहीं हो सका। कृपया परमिशन चेक करें।');
      }
    }

    voiceBtn.addEventListener('click', function (e) {
      e.preventDefault();

      if (isListening || isSpeaking) {
        stopAll();
        return;
      }

      startListening();
    });
  })();
});