(function () {
  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  const uploadZone = qs('#upload-zone');
  const imageInput = qs('#image-input');
  const selectedFileName = qs('#selected-file-name');
  const form = qs('#scan-form');
  const formMessage = qs('#form-message');
  const toggleFormats = qs('#toggle-formats');

  if (imageInput && selectedFileName) {
    imageInput.addEventListener('change', () => {
      const file = imageInput.files?.[0];
      selectedFileName.textContent = file ? `${file.name} • ${(file.size / (1024 * 1024)).toFixed(2)} MB` : 'Nenhum arquivo selecionado';
    });
  }

  if (uploadZone && imageInput) {
    ['dragenter', 'dragover'].forEach(evt => {
      uploadZone.addEventListener(evt, e => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      uploadZone.addEventListener(evt, e => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
      });
    });
    uploadZone.addEventListener('drop', e => {
      const files = e.dataTransfer?.files;
      if (files && files.length) {
        imageInput.files = files;
        imageInput.dispatchEvent(new Event('change'));
      }
    });
  }

  if (toggleFormats) {
    let allChecked = false;
    toggleFormats.addEventListener('click', () => {
      allChecked = !allChecked;
      qsa('input[name="formats"]').forEach(cb => {
        cb.checked = allChecked;
      });
      toggleFormats.textContent = allChecked ? 'Desmarcar todos' : 'Marcar todos';
    });
  }

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      formMessage.className = 'form-message';
      formMessage.textContent = 'Enviando imagem e iniciando sessão...';

      const submitButton = form.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      const data = new FormData(form);

      try {
        const response = await fetch('/api/sessions', { method: 'POST', body: data });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || 'Falha ao criar a sessão.');
        }
        formMessage.classList.add('success');
        formMessage.textContent = 'Sessão criada. Redirecionando...';
        window.location.href = payload.detail_url;
      } catch (error) {
        formMessage.classList.add('error');
        formMessage.textContent = error.message;
        submitButton.disabled = false;
      }
    });
  }

  const sessionRoot = qs('[data-session-id]');
  if (!sessionRoot) return;

  const sessionId = sessionRoot.dataset.sessionId;
  const statusEl = qs('#session-status');
  const messageEl = qs('#session-message');
  const progressBar = qs('#progress-bar');
  const progressText = qs('#progress-text');
  const scannedValue = qs('#scanned-value');
  const scannedHuman = qs('#scanned-human');
  const recoveredValue = qs('#recovered-value');
  const skippedValue = qs('#skipped-value');
  const bytesRecovered = qs('#bytes-recovered');
  const resultsBody = qs('#results-table-body');
  const reportList = qs('#report-list');
  const summaryText = qs('#summary-text');
  const bundleButton = qs('#bundle-button');

  function renderReports(reportFiles) {
    if (!reportFiles?.length) {
      reportList.innerHTML = '<p class="empty-state">Os relatórios aparecerão aqui ao final da análise.</p>';
      return;
    }
    reportList.innerHTML = reportFiles.map(file => `
      <a class="report-link" href="${file.download_url}">
        <span>${file.name}</span>
        <strong>Baixar</strong>
      </a>
    `).join('');
  }

  function renderResults(results) {
    if (!results?.length) {
      resultsBody.innerHTML = '<tr class="placeholder-row"><td colspan="5">Nenhum arquivo recuperado até o momento.</td></tr>';
      return;
    }

    resultsBody.innerHTML = results.map(item => `
      <tr>
        <td>
          <div class="result-type">${item.file_type}</div>
          <div class="result-meta">${item.extension}</div>
        </td>
        <td>${item.size_human}</td>
        <td>${item.offset_start_hex}</td>
        <td>${item.status}</td>
        <td><a class="button subtle" href="${item.download_url}">Baixar</a></td>
      </tr>
    `).join('');
  }

  function applyStatusClass(status) {
    statusEl.className = `status-pill ${status}`;
    statusEl.textContent = status;
  }

  async function poll() {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Não foi possível carregar a sessão.');
      }

      applyStatusClass(data.status);
      messageEl.textContent = data.error || data.message || '';
      progressBar.style.width = `${data.progress}%`;
      progressText.textContent = `${data.progress}%`;
      scannedValue.textContent = `${data.scanned_bytes_human} / ${data.total_bytes_human}`;
      scannedHuman.textContent = `${data.scanned_bytes.toLocaleString('pt-BR')} de ${data.total_bytes.toLocaleString('pt-BR')} bytes`;
      recoveredValue.textContent = data.recovered_count.toLocaleString('pt-BR');
      skippedValue.textContent = data.skipped_count.toLocaleString('pt-BR');
      bytesRecovered.textContent = data.bytes_recovered_human;
      summaryText.textContent = data.error || data.summary_text || 'O resumo ficará disponível assim que a análise terminar.';

      if (data.bundle_url) {
        bundleButton.hidden = false;
        bundleButton.href = data.bundle_url;
      }

      renderReports(data.report_files);
      renderResults(data.results);

      if (data.status === 'completed' || data.status === 'error') {
        return;
      }
      window.setTimeout(poll, 1200);
    } catch (error) {
      messageEl.textContent = error.message;
      applyStatusClass('error');
    }
  }

  poll();
})();
