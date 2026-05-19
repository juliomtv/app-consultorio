/* ============================================================
   ADMIN.JS — Painel Administrativo
   ============================================================ */

'use strict';

// ── BUSCA DE PACIENTES (live search) ─────────────────────────
const patientSearch = document.getElementById('patientLiveSearch');

if (patientSearch) {
  const searchDebounced = window.debounce ? window.debounce(doSearch, 350) : doSearch;
  patientSearch.addEventListener('input', searchDebounced);
}

async function doSearch() {
  const q = document.getElementById('patientLiveSearch')?.value || '';
  const resultsContainer = document.getElementById('searchResults');
  if (!resultsContainer) return;

  if (q.length < 2) {
    resultsContainer.style.display = 'none';
    return;
  }

  try {
    const res = await fetch(`/api/v1/admin/buscar-pacientes?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const patients = data.data || [];

    if (patients.length === 0) {
      resultsContainer.innerHTML = '<div class="dropdown-item">Nenhum paciente encontrado.</div>';
    } else {
      resultsContainer.innerHTML = patients.map(p => `
        <a href="/admin/pacientes/${p.id}" class="dropdown-item">
          <span>👤</span>
          <div>
            <div style="font-weight:600">${p.name}</div>
            <div style="font-size:.8rem;color:var(--text-muted)">${p.email}</div>
          </div>
        </a>
      `).join('');
    }
    resultsContainer.style.display = 'block';
  } catch (_) {}
}

document.addEventListener('click', (e) => {
  const results = document.getElementById('searchResults');
  if (results && !results.contains(e.target) && e.target !== patientSearch) {
    results.style.display = 'none';
  }
});

// ── STATUS DE CONSULTA ────────────────────────────────────────
function changeAppointmentStatus(apptId, currentStatus) {
  const modal = document.getElementById('statusModal');
  if (!modal) return;
  document.getElementById('statusApptId').value = apptId;
  document.getElementById('currentStatusLabel').textContent = currentStatus;
  window.openModal('statusModal');
}

window.changeAppointmentStatus = changeAppointmentStatus;

// ── GRÁFICO MENSAL (sem biblioteca externa) ───────────────────
function drawBarChart(canvasId, labels, values, color = '#4F46E5') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = canvas.offsetHeight || 240;
  ctx.clearRect(0, 0, W, H);

  if (!values || values.length === 0) return;

  const maxVal = Math.max(...values, 1);
  const padL = 40, padB = 36, padT = 16, padR = 16;
  const chartW = W - padL - padR;
  const chartH = H - padB - padT;
  const barW = (chartW / values.length) * 0.55;
  const barGap = chartW / values.length;

  // Grade
  ctx.strokeStyle = '#E2E8F0';
  ctx.lineWidth = 1;
  [0, 0.25, 0.5, 0.75, 1].forEach(fraction => {
    const y = padT + chartH * (1 - fraction);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(W - padR, y);
    ctx.stroke();
    ctx.fillStyle = '#94A3B8';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(Math.round(maxVal * fraction), padL - 6, y + 4);
  });

  // Barras
  values.forEach((val, i) => {
    const barH = (val / maxVal) * chartH;
    const x = padL + barGap * i + (barGap - barW) / 2;
    const y = padT + chartH - barH;

    // Gradiente
    const grad = ctx.createLinearGradient(x, y, x, y + barH);
    grad.addColorStop(0, color);
    grad.addColorStop(1, color + '88');
    ctx.fillStyle = grad;

    // Barra com bordas arredondadas
    const r = Math.min(4, barW / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + barW - r, y);
    ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
    ctx.lineTo(x + barW, y + barH);
    ctx.lineTo(x, y + barH);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.fill();

    // Valor
    if (val > 0) {
      ctx.fillStyle = '#0F172A';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(val, x + barW / 2, y - 6);
    }

    // Label
    ctx.fillStyle = '#64748B';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';
    const label = labels[i] || '';
    ctx.fillText(label, x + barW / 2, H - padB + 18);
  });
}

window.drawBarChart = drawBarChart;

// Inicializar gráfico se os dados estiverem disponíveis
const chartData = window.CHART_DATA;
if (chartData) {
  window.addEventListener('load', () => {
    drawBarChart(
      'monthlyChart',
      chartData.labels,
      chartData.values,
      '#4F46E5'
    );
  });
  window.addEventListener('resize', () => {
    drawBarChart('monthlyChart', chartData.labels, chartData.values, '#4F46E5');
  });
}

// ── CONFIRMAR EXCLUSÃO ────────────────────────────────────────
function confirmDelete(message, formId) {
  if (window.confirm(message || 'Confirmar exclusão?')) {
    document.getElementById(formId)?.submit();
  }
}

window.confirmDelete = confirmDelete;

// ── UPLOAD DE DOCUMENTOS (admin) ─────────────────────────────
const adminUploadZone = document.getElementById('adminUploadZone');
const adminFileInput  = document.getElementById('adminFileInput');

adminUploadZone?.addEventListener('click', () => adminFileInput?.click());

adminUploadZone?.addEventListener('dragover', (e) => {
  e.preventDefault();
  adminUploadZone.classList.add('drag-over');
});

adminUploadZone?.addEventListener('dragleave', () => adminUploadZone.classList.remove('drag-over'));

adminUploadZone?.addEventListener('drop', (e) => {
  e.preventDefault();
  adminUploadZone.classList.remove('drag-over');
  const file = e.dataTransfer?.files[0];
  if (file && adminFileInput) {
    const dt = new DataTransfer();
    dt.items.add(file);
    adminFileInput.files = dt.files;
    updateAdminUpload(file);
  }
});

adminFileInput?.addEventListener('change', (e) => {
  if (e.target.files[0]) updateAdminUpload(e.target.files[0]);
});

function updateAdminUpload(file) {
  const el = document.getElementById('adminUploadName');
  if (el) el.textContent = file.name;
  adminUploadZone?.classList.add('has-file');
}

// ── AGENDA — Navegação de datas ───────────────────────────────
let agendaDate = new Date();

function formatAgendaDate(d) {
  return d.toISOString().split('T')[0];
}

document.getElementById('agendaPrevDay')?.addEventListener('click', () => {
  agendaDate.setDate(agendaDate.getDate() - 1);
  updateAgendaDate();
});

document.getElementById('agendaNextDay')?.addEventListener('click', () => {
  agendaDate.setDate(agendaDate.getDate() + 1);
  updateAgendaDate();
});

document.getElementById('agendaToday')?.addEventListener('click', () => {
  agendaDate = new Date();
  updateAgendaDate();
});

function updateAgendaDate() {
  const dateInput = document.getElementById('agendaDateInput');
  const label = document.getElementById('agendaDateLabel');
  if (dateInput) dateInput.value = formatAgendaDate(agendaDate);
  if (label) {
    label.textContent = agendaDate.toLocaleDateString('pt-BR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });
  }
}

// ── TOAST / NOTIFICAÇÃO RÁPIDA ────────────────────────────────
document.querySelectorAll('[data-toast]').forEach(el => {
  el.addEventListener('click', () => {
    const msg = el.dataset.toast;
    const type = el.dataset.toastType || 'info';
    window.showToast?.(msg, type);
  });
});

// ── PRINT ─────────────────────────────────────────────────────
function printSection(id) {
  const content = document.getElementById(id)?.innerHTML;
  if (!content) return;
  const w = window.open('', '_blank');
  w.document.write(`
    <html><head><title>Imprimir</title>
    <link rel="stylesheet" href="/static/css/main.css">
    </head><body style="padding:2rem">${content}</body></html>
  `);
  w.document.close();
  w.print();
}

window.printSection = printSection;

// ── TOGGLE VISIBILIDADE (senha) ───────────────────────────────
document.querySelectorAll('[data-toggle-password]').forEach(btn => {
  const targetId = btn.dataset.togglePassword;
  const input = document.getElementById(targetId);
  btn.addEventListener('click', () => {
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
    btn.textContent = input.type === 'password' ? '👁' : '🙈';
  });
});
