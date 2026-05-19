/* ============================================================
   APP.JS — Utilitários globais do sistema
   ============================================================ */

'use strict';

// ── SIDEBAR TOGGLE ──────────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');

function openSidebar() {
  sidebar?.classList.add('open');
  sidebarBackdrop?.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  sidebar?.classList.remove('open');
  sidebarBackdrop?.classList.remove('active');
  document.body.style.overflow = '';
}

sidebarToggle?.addEventListener('click', () => {
  sidebar?.classList.contains('open') ? closeSidebar() : openSidebar();
});

sidebarBackdrop?.addEventListener('click', closeSidebar);

// ── AUTO-FECHAR ALERTAS ──────────────────────────────────────
document.querySelectorAll('.alert-close').forEach(btn => {
  btn.addEventListener('click', () => {
    const alert = btn.closest('.alert');
    alert?.remove();
  });
});

setTimeout(() => {
  document.querySelectorAll('.alert').forEach(a => {
    a.style.opacity = '0';
    a.style.transition = 'opacity .5s';
    setTimeout(() => a.remove(), 500);
  });
}, 5000);

// ── DROPDOWN ─────────────────────────────────────────────────
document.querySelectorAll('[data-dropdown]').forEach(trigger => {
  const menuId = trigger.dataset.dropdown;
  const menu = document.getElementById(menuId);

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = menu?.classList.contains('open');
    // Fechar todos os outros dropdowns
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    if (!isOpen) menu?.classList.add('open');
  });
});

document.addEventListener('click', () => {
  document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
});

// ── MODAL ─────────────────────────────────────────────────────
function openModal(id) {
  const overlay = document.getElementById(id);
  overlay?.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  const overlay = document.getElementById(id);
  overlay?.classList.remove('active');
  document.body.style.overflow = '';
}

// Fechar modal clicando no overlay
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

// Fechar com Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(o => o.classList.remove('active'));
    document.body.style.overflow = '';
  }
});

// Expor globalmente
window.openModal = openModal;
window.closeModal = closeModal;

// ── TOAST NOTIFICATIONS ───────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✓', danger: '✕', warning: '⚠', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size:1.1rem;font-weight:700">${icons[type] || icons.info}</span>
    <span style="flex:1">${message}</span>
    <button onclick="this.closest('.toast').remove()" style="background:none;border:none;cursor:pointer;opacity:.6;font-size:1rem;color:inherit">✕</button>
  `;
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity .4s';
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }
  return toast;
}

window.showToast = showToast;

// ── CONFIRM DIALOG ────────────────────────────────────────────
function confirmAction(message, callback) {
  if (window.confirm(message)) callback();
}

window.confirmAction = confirmAction;

// ── FORMULÁRIOS COM CONFIRM ───────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', (e) => {
    const msg = el.dataset.confirm || 'Tem certeza?';
    if (!window.confirm(msg)) e.preventDefault();
  });
});

// ── FORMATAR CPF ──────────────────────────────────────────────
function formatCPF(value) {
  return value.replace(/\D/g, '')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2')
    .slice(0, 14);
}

// ── FORMATAR TELEFONE ─────────────────────────────────────────
function formatPhone(value) {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 10) {
    return digits.replace(/(\d{2})(\d{4})(\d{0,4})/, '($1) $2-$3');
  }
  return digits.replace(/(\d{2})(\d{5})(\d{0,4})/, '($1) $2-$3');
}

// Aplicar máscaras automaticamente
document.querySelectorAll('[data-mask="cpf"]').forEach(input => {
  input.addEventListener('input', () => { input.value = formatCPF(input.value); });
});

document.querySelectorAll('[data-mask="phone"]').forEach(input => {
  input.addEventListener('input', () => { input.value = formatPhone(input.value); });
});

// ── NOTIFICAÇÕES (polling) ────────────────────────────────────
async function updateNotificationCount() {
  try {
    const res = await fetch('/api/v1/notificacoes/nao-lidas');
    if (!res.ok) return;
    const data = await res.json();
    const count = data?.data?.count || 0;
    const badge = document.getElementById('notifCount');
    const dot   = document.getElementById('notifDot');

    if (badge) badge.textContent = count > 99 ? '99+' : count;
    if (dot)   dot.style.display = count > 0 ? 'block' : 'none';

    // Atualizar nav badge da sidebar
    const navBadge = document.querySelector('.nav-notif-badge');
    if (navBadge) {
      navBadge.textContent = count;
      navBadge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  } catch (_) {}
}

// Polling a cada 60s
updateNotificationCount();
setInterval(updateNotificationCount, 60000);

// ── FORMATO DE DATA LEGÍVEL ───────────────────────────────────
function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function timeAgo(dateStr) {
  const diff = (Date.now() - new Date(dateStr)) / 1000;
  if (diff < 60) return 'agora';
  if (diff < 3600) return `${Math.floor(diff / 60)}min atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

window.formatDate = formatDate;
window.timeAgo = timeAgo;

// ── BUSCA COM DEBOUNCE ────────────────────────────────────────
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

window.debounce = debounce;

// ── COPIAR PARA CLIPBOARD ─────────────────────────────────────
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copiado!', 'success', 2000);
  } catch (_) {
    showToast('Não foi possível copiar.', 'danger');
  }
}

window.copyToClipboard = copyToClipboard;

// ── ACTIVE NAV ITEM ───────────────────────────────────────────
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(item => {
  const href = item.getAttribute('href');
  if (href && currentPath.startsWith(href) && href !== '/') {
    item.classList.add('active');
  }
});

// ── PWA INSTALL PROMPT ────────────────────────────────────────
let deferredPrompt = null;
const installBtn = document.getElementById('installAppBtn');

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if (installBtn) installBtn.style.display = 'flex';
});

installBtn?.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') showToast('App instalado com sucesso!', 'success');
  deferredPrompt = null;
  installBtn.style.display = 'none';
});

window.addEventListener('appinstalled', () => {
  showToast('App instalado!', 'success');
  if (installBtn) installBtn.style.display = 'none';
});

// ── REGISTRAR SERVICE WORKER ──────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .catch(() => {});
  });
}

// ── TABS ──────────────────────────────────────────────────────
document.querySelectorAll('.tabs').forEach(tabContainer => {
  const items = tabContainer.querySelectorAll('.tab-item');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.tab;
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.style.display = panel.id === target ? 'block' : 'none';
      });
    });
  });
});

// ── SUBMIT BUTTON LOADING ─────────────────────────────────────
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('[type="submit"]');
    if (btn && !btn.dataset.noLoading) {
      btn.disabled = true;
      const original = btn.innerHTML;
      btn.innerHTML = '<span class="spinner spinner-sm"></span> Aguarde...';
      setTimeout(() => { btn.disabled = false; btn.innerHTML = original; }, 8000);
    }
  });
});
