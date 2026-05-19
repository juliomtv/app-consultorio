/* ============================================================
   CONTRACTIONS.JS — Contador de Contrações
   ============================================================ */

'use strict';

const ContractionCounter = {
  sessionId: null,
  isActive: false,
  contractionStartTime: null,
  sessionStartTime: null,
  contractions: [],
  timerInterval: null,
  elapsedInterval: null,

  // Elementos DOM
  els: {
    btn: null,
    mainTimer: null,
    timerLabel: null,
    count: null,
    avgDuration: null,
    avgInterval: null,
    lastInterval: null,
    historyList: null,
    statusText: null,
    startSessionBtn: null,
    endSessionBtn: null,
    sessionPanel: null,
    noSessionPanel: null,
  },

  init() {
    this.els.btn            = document.getElementById('contractionBtn');
    this.els.mainTimer      = document.getElementById('mainTimer');
    this.els.timerLabel     = document.getElementById('timerLabel');
    this.els.count          = document.getElementById('contractionCount');
    this.els.avgDuration    = document.getElementById('avgDuration');
    this.els.avgInterval    = document.getElementById('avgInterval');
    this.els.historyList    = document.getElementById('contractionHistory');
    this.els.statusText     = document.getElementById('statusText');
    this.els.startSessionBtn = document.getElementById('startSessionBtn');
    this.els.endSessionBtn   = document.getElementById('endSessionBtn');
    this.els.sessionPanel    = document.getElementById('sessionPanel');
    this.els.noSessionPanel  = document.getElementById('noSessionPanel');

    this.els.startSessionBtn?.addEventListener('click', () => this.startSession());
    this.els.endSessionBtn?.addEventListener('click', () => this.endSession());
    this.els.btn?.addEventListener('click', () => this.toggle());
  },

  async startSession() {
    try {
      const res = await fetch('/api/v1/contracoes/sessao', { method: 'POST' });
      const data = await res.json();
      this.sessionId = data.data?.session_id;
      this.sessionStartTime = Date.now();
      this.contractions = [];

      if (this.els.noSessionPanel) this.els.noSessionPanel.style.display = 'none';
      if (this.els.sessionPanel)   this.els.sessionPanel.style.display = 'block';

      this.startElapsedTimer();
      this.updateUI();
      showToast('Sessão iniciada. Pressione o botão quando sentir uma contração.', 'success');
    } catch (_) {
      showToast('Erro ao iniciar sessão.', 'danger');
    }
  },

  async endSession() {
    if (!this.sessionId) return;
    if (!window.confirm('Encerrar a sessão de contrações?')) return;

    if (this.isActive) this.stopContraction();
    clearInterval(this.elapsedInterval);

    try {
      const res = await fetch(`/api/v1/contracoes/sessao/${this.sessionId}/encerrar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: document.getElementById('sessionNotes')?.value || '' }),
      });
      const data = await res.json();

      if (this.els.sessionPanel)   this.els.sessionPanel.style.display   = 'none';
      if (this.els.noSessionPanel) this.els.noSessionPanel.style.display = 'block';

      this.sessionId = null;
      this.contractions = [];
      showToast('Sessão encerrada e salva com sucesso!', 'success');

      setTimeout(() => window.location.reload(), 1500);
    } catch (_) {
      showToast('Erro ao encerrar sessão.', 'danger');
    }
  },

  toggle() {
    if (!this.sessionId) {
      showToast('Inicie uma sessão primeiro.', 'warning');
      return;
    }
    if (!this.isActive) {
      this.startContraction();
    } else {
      this.stopContraction();
    }
  },

  startContraction() {
    this.isActive = true;
    this.contractionStartTime = Date.now();

    const btn = this.els.btn;
    if (btn) {
      btn.classList.remove('idle');
      btn.classList.add('active');
      btn.querySelector('.btn-label').textContent = 'FIM';
      btn.querySelector('.btn-icon-text').textContent = '⏸';
    }

    if (this.els.timerLabel) this.els.timerLabel.textContent = 'Duração';
    if (this.els.statusText)  this.els.statusText.textContent = 'Contração ativa...';

    this.timerInterval = setInterval(() => this.updateTimer(), 100);
  },

  async stopContraction() {
    if (!this.isActive) return;

    const endTime = Date.now();
    const duration = (endTime - this.contractionStartTime) / 1000;

    const lastContraction = this.contractions[this.contractions.length - 1];
    const interval = lastContraction
      ? (this.contractionStartTime - lastContraction.startedAt) / 1000
      : null;

    clearInterval(this.timerInterval);
    this.isActive = false;

    const contraction = {
      startedAt: this.contractionStartTime,
      endedAt: endTime,
      duration,
      interval,
      number: this.contractions.length + 1,
    };

    this.contractions.push(contraction);

    const btn = this.els.btn;
    if (btn) {
      btn.classList.add('idle');
      btn.classList.remove('active');
      btn.querySelector('.btn-label').textContent = 'CONTRAÇÃO';
      btn.querySelector('.btn-icon-text').textContent = '▶';
    }

    if (this.els.timerLabel) this.els.timerLabel.textContent = 'Intervalo';
    if (this.els.statusText)  this.els.statusText.textContent = 'Aguardando próxima contração...';

    // Salvar no servidor
    try {
      await fetch(`/api/v1/contracoes/sessao/${this.sessionId}/registrar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          started_at: new Date(this.contractionStartTime).toISOString(),
          ended_at:   new Date(endTime).toISOString(),
          duration,
          interval,
        }),
      });
    } catch (_) {}

    this.updateUI();
    this.addToHistory(contraction);

    // Alertas automáticos
    if (duration < 20) {
      showToast('Contração curta (menos de 20s). Continue monitorando.', 'info');
    }
    if (this.contractions.length >= 3) {
      const recentIntervals = this.contractions
        .slice(-3)
        .map(c => c.interval)
        .filter(Boolean);
      const avgInt = recentIntervals.reduce((a, b) => a + b, 0) / recentIntervals.length;
      if (avgInt <= 300) { // 5 minutos
        showToast('⚠ Contrações frequentes! Considere contatar seu médico.', 'warning', 8000);
      }
    }

    // Reiniciar timer para intervalo
    this.timerInterval = setInterval(() => this.updateIntervalTimer(), 100);
  },

  updateTimer() {
    const elapsed = (Date.now() - this.contractionStartTime) / 1000;
    if (this.els.mainTimer) this.els.mainTimer.textContent = this.formatTime(elapsed);
  },

  updateIntervalTimer() {
    const lastContraction = this.contractions[this.contractions.length - 1];
    if (!lastContraction) return;
    const elapsed = (Date.now() - lastContraction.endedAt) / 1000;
    if (this.els.mainTimer) this.els.mainTimer.textContent = this.formatTime(elapsed);
  },

  updateUI() {
    if (this.els.count) this.els.count.textContent = this.contractions.length;

    if (this.contractions.length > 0) {
      const durations = this.contractions.map(c => c.duration);
      const avgDur = durations.reduce((a, b) => a + b, 0) / durations.length;
      if (this.els.avgDuration) this.els.avgDuration.textContent = this.formatTime(avgDur);

      const intervals = this.contractions.map(c => c.interval).filter(Boolean);
      if (intervals.length > 0) {
        const avgInt = intervals.reduce((a, b) => a + b, 0) / intervals.length;
        if (this.els.avgInterval) this.els.avgInterval.textContent = this.formatTime(avgInt);
      }
    }
  },

  addToHistory(c) {
    if (!this.els.historyList) return;
    const item = document.createElement('div');
    item.className = 'contraction-row animate-slide-up';
    item.innerHTML = `
      <div class="contraction-number">${c.number}</div>
      <div style="flex:1">
        <div style="font-size:.875rem;font-weight:600;color:var(--text-primary)">
          Duração: ${this.formatTime(c.duration)}
        </div>
        ${c.interval ? `<div style="font-size:.8rem;color:var(--text-secondary)">Intervalo: ${this.formatTime(c.interval)}</div>` : ''}
      </div>
      <div style="font-size:.75rem;color:var(--text-muted)">
        ${new Date(c.startedAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </div>
    `;
    this.els.historyList.prepend(item);
  },

  startElapsedTimer() {
    const sessionLabel = document.getElementById('sessionElapsed');
    if (!sessionLabel) return;
    this.elapsedInterval = setInterval(() => {
      const elapsed = (Date.now() - this.sessionStartTime) / 1000;
      sessionLabel.textContent = this.formatTime(elapsed);
    }, 1000);
  },

  formatTime(seconds) {
    const s = Math.floor(seconds);
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return `${h}:${(m % 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
    return `${m.toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
  },
};

document.addEventListener('DOMContentLoaded', () => ContractionCounter.init());
