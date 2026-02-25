/**
 * VYON Widget — Client Logic
 * Single Responsibility: state management & API communication only.
 * All visual styles live in vyon-widget.css.
 */
(function () {
  'use strict';

  /* ── Constants ── */
  var API_PROXY     = '/apps/vyon-api/api/proxy';
  var POLL_INTERVAL = 4000;
  var MAX_POLLS     = 30;

  var PROC_MESSAGES = [
    ['Analyzing your photo...',   'Detecting body measurements'],
    ['Fitting the garment...',    'Applying fabric simulation'],
    ['Processing your style...',  'Our AI is tailoring the look for you'],
    ['Almost done...',            'Adding the final touches'],
  ];

  /* ── State ── */
  var currentFile = null;
  var pollId      = null;
  var msgCycleId  = null;
  var msgIdx      = 0;

  /* ── DOM helper ── */
  var $ = function (id) { return document.getElementById(id); };

  /* ──────────────────────────────────────
     State transitions
  ────────────────────────────────────── */
  function showState(name) {
    ['upload', 'processing', 'result', 'error'].forEach(function (s) {
      var el = $('vy-s-' + s);
      if (el) el.classList.toggle('vy-active', s === name);
    });
    if (name === 'processing') { startMsgCycle(); }
    else                       { stopMsgCycle();  }
  }

  function openPanel() {
    var p = $('vyon-panel');
    if (p) { p.classList.add('vy-visible'); showState('upload'); }
  }

  function closePanel() {
    var p = $('vyon-panel');
    if (p) p.classList.remove('vy-visible');
    stopPoll();
  }

  function resetToUpload() {
    currentFile = null;
    var fi = $('vyon-file-input');
    if (fi) fi.value = '';
    var fp = $('vyon-file-preview');
    if (fp) fp.classList.remove('vy-visible');

    var submitBtn = $('vyon-submit-btn');
    if (submitBtn) submitBtn.style.display = 'none';

    showState('upload');
  }

  /* ──────────────────────────────────────
     File handling
  ────────────────────────────────────── */
  function setFilePreview(file) {
    currentFile = file;
    var nameEl  = $('vy-prev-name');
    var imgEl   = $('vy-prev-img');
    var fp      = $('vyon-file-preview');
    if (!fp || !nameEl) return;

    nameEl.textContent = file.name.toUpperCase();

    var reader = new FileReader();
    reader.onload = function (e) { if (imgEl) imgEl.src = e.target.result; };
    reader.readAsDataURL(file);

    fp.classList.add('vy-visible');

    var submitBtn = $('vyon-submit-btn');
    if (submitBtn) submitBtn.style.display = 'flex';
  }

  /* ──────────────────────────────────────
     Processing message cycle
  ────────────────────────────────────── */
  function startMsgCycle() {
    msgIdx = 0;
    renderMsg();
    msgCycleId = setInterval(function () {
      msgIdx = (msgIdx + 1) % PROC_MESSAGES.length;
      renderMsg();
    }, 3200);
  }

  function stopMsgCycle() {
    if (msgCycleId) { clearInterval(msgCycleId); msgCycleId = null; }
  }

  function renderMsg() {
    var pair  = PROC_MESSAGES[msgIdx];
    var title = $('vy-proc-title');
    var hint  = $('vy-proc-hint');
    fadeText(title, pair[0]);
    fadeText(hint,  pair[1]);
  }

  function fadeText(el, text) {
    if (!el) return;
    el.style.opacity = '0';
    setTimeout(function () { el.textContent = text; el.style.opacity = '1'; }, 200);
  }

  /* ──────────────────────────────────────
     Error display
  ────────────────────────────────────── */
  function showError(message) {
    var el = $('vy-err-msg');
    if (el) el.textContent = message || 'An error occurred';
    showState('error');
  }

  /* ──────────────────────────────────────
     Polling
  ────────────────────────────────────── */
  function stopPoll() {
    if (pollId) { clearInterval(pollId); pollId = null; }
  }

  function pollStatus(taskId) {
    var attempts = 0;
    pollId = setInterval(async function () {
      attempts++;
      if (attempts > MAX_POLLS) {
        stopPoll();
        showError('Request timed out. Please try again later.');
        return;
      }
      try {
        var res  = await fetch(API_PROXY + '?task_id=' + encodeURIComponent(taskId));
        if (!res.ok) throw new Error('Status check failed: ' + res.status);
        var data = await res.json();

        if (data.status === 'completed') {
          stopPoll();
          var imgUrl = (data.results || [])[0];
          if (!imgUrl) { showError('Task completed but no result image found.'); return; }
          var ri = $('vy-result-img');
          if (ri) ri.src = imgUrl;
          showState('result');

        } else if (data.status === 'failed') {
          stopPoll();
          showError(data.error || 'Processing failed. Please try again.');
        }
      } catch (e) {
        stopPoll();
        showError(e.message || 'Connection error');
      }
    }, POLL_INTERVAL);
  }

  /* ──────────────────────────────────────
     Try-On submission
  ────────────────────────────────────── */
  async function startTryOn() {
    if (!currentFile) { return; }

    var garmentEl  = $('vyon-product-url');
    var garmentUrl = garmentEl ? garmentEl.value : '';
    if (!garmentUrl) { showError('Could not determine product image URL.'); return; }

    showState('processing');

    try {
      var fd = new FormData();
      fd.append('model',         currentFile);
      fd.append('garment_url_1', garmentUrl);

      var res = await fetch(API_PROXY, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Failed to create task: ' + res.status);

      var data   = await res.json();
      var taskId = data.task_id;
      if (!taskId) throw new Error('No task ID received from server');

      pollStatus(taskId);

    } catch (e) {
      showError(e.message || 'An unexpected error occurred');
    }
  }

  /* ──────────────────────────────────────
     Event binding
  ────────────────────────────────────── */
  function bindEvents() {
    var trigger = $('vyon-trigger-btn');
    if (trigger) trigger.addEventListener('click', openPanel);

    document.querySelectorAll('#vyon-panel .vy-close').forEach(function (btn) {
      btn.addEventListener('click', closePanel);
    });

    var fileInput  = $('vyon-file-input');
    var uploadZone = $('vyon-upload-zone');
    var pillBtn    = document.querySelector('.vy-pill-btn');

    if (fileInput) {
      fileInput.addEventListener('change', function (e) {
        var f = e.target.files && e.target.files[0];
        if (f) setFilePreview(f);
      });
    }

    // Надёжный клик по всей зоне и по кнопке Select File
    if (uploadZone && fileInput) {
      uploadZone.addEventListener('click', function () {
        fileInput.click();
      });
    }
    if (pillBtn && fileInput) {
      pillBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        fileInput.click();
      });
    }

    var delBtn = $('vy-remove-btn');
    if (delBtn) {
      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        resetToUpload();
      });
    }

    var submitBtn = $('vyon-submit-btn');
    if (submitBtn) submitBtn.addEventListener('click', startTryOn);

    var retryBtn = $('vy-retry-btn');
    if (retryBtn) retryBtn.addEventListener('click', resetToUpload);

    var retryErrBtn = $('vy-retry-err-btn');
    if (retryErrBtn) retryErrBtn.addEventListener('click', resetToUpload);

    var cancelProc = $('vy-cancel-proc');
    if (cancelProc) {
      cancelProc.addEventListener('click', function () {
        stopPoll();
        closePanel();
      });
    }
  }

  /* ── Init ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindEvents);
  } else {
    bindEvents();
  }

})();

