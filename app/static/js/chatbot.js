/**
 * WIU Library Chatbot Widget
 * 
 * Embeds on any WIU library page via a single <script> tag.
 * Communicates with the FastAPI backend at the configured API URL.
 * 
 * No external dependencies. Vanilla JS only.
 */

(function () {
  'use strict';

  // ── Configuration ───────────────────────────────────────────────
  // API base URL is fetched from the backend /api/config endpoint.
  // This avoids hardcoding the URL in the JS file.
  let API_BASE = '';
  const CSS_URL = document.currentScript
    ? document.currentScript.src.replace('chatbot.js', '../css/chatbot.css')
    : '/static/css/chatbot.css';

  // ── State ────────────────────────────────────────────────────────
  let isOpen = false;
  let isTyping = false;
  let quickButtons = [];

  // ── Inject CSS ───────────────────────────────────────────────────
  function injectCSS() {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = CSS_URL;
    document.head.appendChild(link);
  }

  // ── HTML ───────────────────────────────────────────────────
  function buildWidget() {
    // Notification banner
    const notifMessages = [
    "<strong>Library assistance</strong><br>Have a question? I can help.",
    "<strong>Need Help?</strong><br>Ask me about library services.",
    "<strong>Questions?</strong><br>I'm here to help with library inquiries.",
    "<strong>Library Chatbot</strong><br>Ask me anything about the library.",
];
const randomMsg = notifMessages[Math.floor(Math.random() * notifMessages.length)];

const notification = document.createElement('div');
notification.id = 'wiu-chat-notification';
notification.innerHTML = `
    <p>📚 ${randomMsg}</p>
    <button id="wiu-notif-close" aria-label="Close notification">×</button>
`;

    // Floating button
    const btn = document.createElement('button');
    btn.id = 'wiu-chat-btn';
    btn.setAttribute('aria-label', 'Open library chat');
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
      </svg>
    `;

    // Chat window
    const window_ = document.createElement('div');
    window_.id = 'wiu-chat-window';
    window_.setAttribute('role', 'dialog');
    window_.setAttribute('aria-label', 'WIU Library Chat');
    window_.innerHTML = `
      <div id="wiu-chat-header">
        <div id="wiu-chat-header-left">
          <div id="wiu-chat-header-avatar"><img src="${API_BASE}/static/css/library-avatar.png" alt="Malpass Library" style="width:30px;height:30px;object-fit:contain;border-radius:4px;"></div>
          <div>
            <h3>WIU Library Assistant</h3>
            <p>Ask me anything about the library</p>
          </div>
        </div>
        <button id="wiu-chat-close" aria-label="Close chat">×</button>
      </div>
      <div id="wiu-chat-messages" role="log" aria-live="polite"></div>
      <div id="wiu-quick-buttons"></div>
      <div id="wiu-chat-input-area">
        <textarea
          id="wiu-chat-input"
          placeholder="Type your question..."
          rows="1"
          maxlength="500"
          aria-label="Chat input"
        ></textarea>
        <button id="wiu-chat-send" aria-label="Send message">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
      <div id="wiu-chat-disclaimer">
        <p>AI-generated responses may not always be accurate. 
           <a href="https://www.wiu.edu/libraries/contact.php" target="_blank">Contact us</a> for help.</p>
      </div>
    `;

    document.body.appendChild(notification);
    document.body.appendChild(btn);
    document.body.appendChild(window_);
  }

  // ── Event Listeners ──────────────────────────────────────────────
  function bindEvents() {
    // Open chat, hide notification
    document.getElementById('wiu-chat-btn').addEventListener('click', () => {
      toggleChat(true);
      hideNotification();
    });

    // Close chat
    document.getElementById('wiu-chat-close').addEventListener('click', () => {
      toggleChat(false);
    });

    // Close notification
    document.getElementById('wiu-notif-close').addEventListener('click', () => {
      hideNotification();
    });

    // Send on button click
    document.getElementById('wiu-chat-send').addEventListener('click', sendMessage);

    // Send on Enter key (Shift+Enter for new line)
    document.getElementById('wiu-chat-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    document.getElementById('wiu-chat-input').addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 80) + 'px';
    });
  }

  // ── Toggle Chat Window ───────────────────────────────────────────
  function toggleChat(open) {
    isOpen = open;
    const window_ = document.getElementById('wiu-chat-window');
    if (open) {
      window_.classList.add('wiu-open');
      document.getElementById('wiu-chat-input').focus();
    } else {
      window_.classList.remove('wiu-open');
    }
  }

  // ── Hide Notification ────────────────────────────────────────────
  function hideNotification() {
    const notif = document.getElementById('wiu-chat-notification');
    if (notif) {
      notif.style.display = 'none';
      // Remember preference in sessionStorage
      sessionStorage.setItem('wiu-notif-closed', '1');
    }
  }

  // ── Add Message to Chat ───────────────────────────────────────────
  function addMessage(text, role, urls) {
    const messages = document.getElementById('wiu-chat-messages');

    const msg = document.createElement('div');
    msg.className = `wiu-msg wiu-msg-${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'wiu-bubble';
    bubble.textContent = text;

    msg.appendChild(bubble);

    // Add URL links if present
    if (urls && urls.length > 0) {
    const linksDiv = document.createElement('div');
    linksDiv.className = 'wiu-url-links';
    
    urls.forEach(({ url, label }) => {
        const a = document.createElement('a');
        a.className = 'wiu-url-link';
        a.textContent = label || url;

        if (url === 'https://www.wiu.edu/libraries/contact.php') {
            a.href = '#';
            a.addEventListener('click', (e) => {
                e.preventDefault();
                addMessage(
                    "For research questions or assignments, contact our librarians:\n\nStacia McKeever — sr-mckeever@wiu.edu\nNadia Nieblas Nunez — n-nieblasnunez@wiu.edu\nPhone: (309) 298-2326\nLocation: Malpass Library, 3rd floor\nOffice hours: Monday–Friday, 9am–5pm",
                    'bot',
                    []
                );
            });
        } else {
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
        }

        linksDiv.appendChild(a);
    });

        // Back to main menu button
        const backBtn = document.createElement('button');
        backBtn.className = 'wiu-url-link';
        backBtn.style.cssText = 'border:none;cursor:pointer;background:#f0edf5;color:#663399;width:100%;text-align:left;margin-top:4px;';
        backBtn.textContent = '← Back to main menu';
        backBtn.addEventListener('click', () => {
            renderQuickButtons(quickButtons);
        });
        linksDiv.appendChild(backBtn);

        msg.appendChild(linksDiv);
    }

    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  // ── Typing Indicator ─────────────────────────────────────────────
  function showTyping() {
    const messages = document.getElementById('wiu-chat-messages');
    const typing = document.createElement('div');
    typing.id = 'wiu-typing-indicator';
    typing.className = 'wiu-msg wiu-msg-bot';
    typing.innerHTML = `
      <div class="wiu-typing">
        <span></span><span></span><span></span>
      </div>
    `;
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    const indicator = document.getElementById('wiu-typing-indicator');
    if (indicator) indicator.remove();
  }

  // ── Render Quick Buttons ──────────────────────────────────────────
  function renderQuickButtons(buttons) {
  const container = document.getElementById('wiu-quick-buttons');
  container.innerHTML = '';

  // Header row with label and close button
  const header = document.createElement('div');
  header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;width:100%;margin-bottom:6px;padding:0 2px;';
  header.innerHTML = `
    <span style="font-size:11px;color:#8a7aa0;font-family:Georgia,serif;">Quick questions</span>
    <button style="background:none;border:none;cursor:pointer;color:#8a7aa0;font-size:16px;line-height:1;padding:0;" 
            aria-label="Close quick menu" id="wiu-quick-close">×</button>
  `;
  container.appendChild(header);

  buttons.forEach(({ question, faq_id }) => {
    const btn = document.createElement('button');
    btn.className = 'wiu-quick-btn';
    btn.textContent = question;
    btn.addEventListener('click', () => {
      container.innerHTML = '';
      sendQuestion(question);
    });
    container.appendChild(btn);
  });

  document.getElementById('wiu-quick-close').addEventListener('click', () => {
    container.innerHTML = '';
  });
}

  // ── Send Message ──────────────────────────────────────────────────
  function sendMessage() {
    const input = document.getElementById('wiu-chat-input');
    const text = input.value.trim();
    if (!text || isTyping) return;

    input.value = '';
    input.style.height = 'auto';

    // Hide quick buttons once user starts typing their own question
    document.getElementById('wiu-quick-buttons').innerHTML = '';

    sendQuestion(text);
  }

  // ── Core Send Logic ───────────────────────────────────────────────
  async function sendQuestion(question) {
    if (isTyping) return;
    isTyping = true;

    addMessage(question, 'user');
    showTyping();

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question }),
      });

      if (!response.ok) throw new Error('API error');

      const data = await response.json();
      hideTyping();
      addMessage(data.answer, 'bot', data.urls);

    } catch (error) {
      hideTyping();
      addMessage(
        'Sorry, I\'m having trouble connecting right now. Please try again or contact the library directly.',
        'bot',
        [{ url: 'https://www.wiu.edu/libraries/contact.php', label: 'Contact the Library →' }]
      );
    } finally {
      isTyping = false;
    }
  }

  // ── Load Quick Buttons from API ───────────────────────────────────
  async function loadQuickButtons() {
  try {
    const response = await fetch(`${API_BASE}/api/quick-buttons`);
    if (!response.ok) return;
    const buttons = await response.json();
    if (buttons.length > 0) {
      quickButtons = buttons;
      renderQuickButtons(buttons);
    }
  } catch (e) {
    // Silently fail
  }
}

  // ── Welcome Message ───────────────────────────────────────────────
  function showWelcome() {
    addMessage(
      'Hello! I\'m the WIU Library Assistant. How can I help you today? You can ask me about library hours, borrowing books, accessing databases, and more.',
      'bot'
    );
  }

  // ── Init ──────────────────────────────────────────────────────────
  async function init() {
    // Fetch API config from backend
    try {
      const scriptSrc = document.currentScript
        ? document.currentScript.src
        : window.location.origin + '/static/js/chatbot.js';
      const origin = new URL(scriptSrc).origin;
      const configRes = await fetch(`${origin}/api/config`);
      const config = await configRes.json();
      API_BASE = config.api_base_url || origin;
    } catch (e) {
      // Fallback to same origin as script
      API_BASE = window.location.origin;
    }

    injectCSS();
    buildWidget();
    bindEvents();

    // Show welcome message when chat first opens
    document.getElementById('wiu-chat-btn').addEventListener('click', function onFirst() {
      showWelcome();
      loadQuickButtons();
      this.removeEventListener('click', onFirst);
    }, { once: true });

    // Show notification after 3 seconds if not previously closed
    if (!sessionStorage.getItem('wiu-notif-closed')) {
      setTimeout(() => {
        const notif = document.getElementById('wiu-chat-notification');
        if (notif && !isOpen) notif.style.display = 'flex';
      }, 3000);
    }

    // Hide notification initially
    const notif = document.getElementById('wiu-chat-notification');
    if (notif) notif.style.display = 'none';
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();