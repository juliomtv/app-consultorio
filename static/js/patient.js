/* ============================================================
   PATIENT.JS — Lógica específica da área do paciente
   ============================================================ */

'use strict';

// ── SELETOR DE HORÁRIOS ───────────────────────────────────────
const professionalSelect = document.getElementById('professionalSelect');
const dateInput = document.getElementById('appointmentDate');
const timeSlotsContainer = document.getElementById('timeSlots');
const selectedTimeInput = document.getElementById('selectedTime');

async function loadTimeSlots() {
  const profId = professionalSelect?.value;
  const date = dateInput?.value;
  const timeSlotsGroup = document.getElementById('timeSlotsGroup');

  if (!profId || !date) {
    if (timeSlotsContainer) timeSlotsContainer.innerHTML = '<p class="text-muted text-sm">Selecione profissional e data.</p>';
    return;
  }

  if (timeSlotsGroup) timeSlotsGroup.style.display = 'block';
  timeSlotsContainer.innerHTML = '<div class="d-flex justify-center py-4"><span class="spinner"></span></div>';

  try {
    const res = await fetch(`/api/v1/horarios-disponiveis?professional_id=${profId}&date=${date}`);
    const data = await res.json();

    if (!data.data || data.data.length === 0) {
      timeSlotsContainer.innerHTML = '<p class="text-muted text-sm text-center py-4">Nenhum horário disponível nesta data.</p>';
      return;
    }

    timeSlotsContainer.innerHTML = data.data.map(slot => `
      <button type="button"
              class="time-slot"
              data-time="${slot}"
              onclick="selectTimeSlot(this, '${slot}')">
        ${slot}
      </button>
    `).join('');

  } catch (err) {
    timeSlotsContainer.innerHTML = '<p class="text-danger text-sm">Erro ao carregar horários.</p>';
  }
}

function selectTimeSlot(btn, time) {
  document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
  btn.classList.add('selected');
  if (selectedTimeInput) selectedTimeInput.value = time;
}

professionalSelect?.addEventListener('change', loadTimeSlots);
dateInput?.addEventListener('change', loadTimeSlots);

// Bloquear datas passadas no input
if (dateInput) {
  const today = new Date().toISOString().split('T')[0];
  dateInput.min = today;
}

// ── CANCELAR CONSULTA ─────────────────────────────────────────
function confirmCancel(apptId, date) {
  const modal = document.getElementById('cancelModal');
  if (!modal) {
    if (window.confirm(`Cancelar consulta de ${date}?`)) {
      document.getElementById(`cancelForm${apptId}`)?.submit();
    }
    return;
  }
  document.getElementById('cancelApptId').value = apptId;
  document.getElementById('cancelApptDate').textContent = date;
  window.openModal('cancelModal');
}

window.confirmCancel = confirmCancel;

// ── MARCAR NOTIFICAÇÃO COMO LIDA ──────────────────────────────
async function markNotifRead(notifId, element) {
  try {
    await fetch(`/paciente/notificacoes/marcar-lida/${notifId}`, { method: 'POST' });
    element.classList.remove('unread');
    const dot = element.querySelector('.notif-unread-dot');
    dot?.remove();
  } catch (_) {}
}

window.markNotifRead = markNotifRead;

// ── MARCAR TODAS LIDAS ────────────────────────────────────────
document.getElementById('markAllReadBtn')?.addEventListener('click', async () => {
  try {
    await fetch('/paciente/notificacoes/marcar-todas-lidas', { method: 'POST' });
    document.querySelectorAll('.notif-item.unread').forEach(item => {
      item.classList.remove('unread');
      item.querySelector('.notif-unread-dot')?.remove();
    });
    showToast('Todas as notificações marcadas como lidas.', 'success');
  } catch (_) {
    showToast('Erro ao marcar notificações.', 'danger');
  }
});

// ── UPLOAD DE DOCUMENTOS ──────────────────────────────────────
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('docFileInput');

uploadZone?.addEventListener('click', () => fileInput?.click());

uploadZone?.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone?.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));

uploadZone?.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const file = e.dataTransfer?.files[0];
  if (file && fileInput) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    updateUploadDisplay(file);
  }
});

fileInput?.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) updateUploadDisplay(file);
});

function updateUploadDisplay(file) {
  const nameEl = document.getElementById('uploadFileName');
  const sizeEl = document.getElementById('uploadFileSize');
  if (nameEl) nameEl.textContent = file.name;
  if (sizeEl) sizeEl.textContent = formatFileSize(file.size);
  uploadZone?.classList.add('has-file');
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

// ── SELEÇÃO DE PROFISSIONAL (radio cards) ─────────────────────
document.querySelectorAll('.prof-select-card').forEach(card => {
  const radio = card.querySelector('input[type="radio"]');
  card.addEventListener('click', () => {
    document.querySelectorAll('.prof-select-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    if (radio) {
      radio.checked = true;
      if (professionalSelect) professionalSelect.value = radio.value;
    }
    loadTimeSlots();
  });
});

// ── BIRTH PLAN — Opções visuais ────────────────────────────────
document.querySelectorAll('.birth-plan-option').forEach(option => {
  const input = option.querySelector('input');
  option.addEventListener('click', () => {
    const name = input?.name;
    document.querySelectorAll(`.birth-plan-option input[name="${name}"]`).forEach(i => {
      i.closest('.birth-plan-option')?.classList.remove('selected');
    });
    option.classList.add('selected');
    if (input) input.checked = true;
  });

  if (input?.checked) option.classList.add('selected');
});

// ── ABRIR PDF INLINE ──────────────────────────────────────────
function openPDF(url, title) {
  const modal = document.getElementById('pdfViewerModal');
  if (!modal) {
    window.open(url, '_blank');
    return;
  }
  document.getElementById('pdfViewerTitle').textContent = title || 'Visualizador';
  document.getElementById('pdfViewerFrame').src = url;
  window.openModal('pdfViewerModal');
}

window.openPDF = openPDF;

// ── WHATSAPP ───────────────────────────────────────────────────
function openWhatsApp(phone, message = '') {
  const digits = phone.replace(/\D/g, '');
  const number = digits.startsWith('55') ? digits : '55' + digits;
  const url = `https://wa.me/${number}${message ? '?text=' + encodeURIComponent(message) : ''}`;
  window.open(url, '_blank');
}

window.openWhatsApp = openWhatsApp;
