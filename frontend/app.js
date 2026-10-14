/**
 * app.js - Frontend Logic & Realtime Dashboard Controller
 * ========================================================
 * Handles parameters, REST API polling, real-time KPI updates,
 * table rendering, birthday calculator, and image modals.
 */

let pollInterval = null;
let currentResults = null;

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupPills();
  setupInputs();
  setupActionButtons();
  setupBirthdayCalculator();
  setupImageModal();

  // Load existing results immediately if available
  fetchLatestResults();

  // Poll status periodically (every 1s if running, 4s if idle)
  startStatusPolling();
});

// =========================================================================
// TABS
// =========================================================================
function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");
    });
  });
}

// =========================================================================
// PILLS & FORM CONTROLS
// =========================================================================
function setupPills() {
  // Sample size pills
  setupPillGroup("pill-sample-size", "input-sample-size");
  // Trials pills
  setupPillGroup("pill-trials", "input-trials");

  // Time delta slider
  const deltaSlider = document.getElementById("input-delta-minutes");
  const deltaLabel = document.getElementById("label-delta-val");
  deltaSlider.addEventListener("input", (e) => {
    deltaLabel.textContent = `${parseFloat(e.target.value).toFixed(1)} dk`;
  });

  // Seed shuffle button
  document.getElementById("btn-shuffle-seed").addEventListener("click", () => {
    const randomSeed = Math.floor(Math.random() * 900000) + 100000;
    document.getElementById("input-seed").value = randomSeed;
  });
}

function setupPillGroup(groupId, inputId) {
  const container = document.getElementById(groupId);
  const input = document.getElementById(inputId);
  if (!container || !input) return;

  const buttons = container.querySelectorAll(".pill-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      input.value = btn.getAttribute("data-val");
    });
  });

  input.addEventListener("input", () => {
    buttons.forEach(b => {
      if (b.getAttribute("data-val") === input.value) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });
  });
}

function setupInputs() {
  // Select generator change helper
  const genSelect = document.getElementById("select-generator");
  genSelect.addEventListener("change", () => {
    // optional helper
  });
}

// =========================================================================
// ACTION BUTTONS
// =========================================================================
function setupActionButtons() {
  // Start simulation
  document.getElementById("btn-start-simulation").addEventListener("click", triggerSimulation);

  // Open folder
  document.getElementById("btn-open-folder").addEventListener("click", () => {
    fetch("/api/open-folder", { method: "POST" })
      .then(res => res.json())
      .catch(err => console.error("Klasör açma hatası:", err));
  });

  // Refresh
  document.getElementById("btn-refresh-data").addEventListener("click", () => {
    fetchLatestResults();
  });

  // Copy report
  document.getElementById("btn-copy-report").addEventListener("click", () => {
    const text = document.getElementById("markdown-viewer").innerText;
    navigator.clipboard.writeText(text).then(() => {
      alert("Denetim raporu panoya kopyalandı!");
    });
  });

  // Clear logs
  document.getElementById("btn-clear-logs").addEventListener("click", () => {
    document.getElementById("terminal-view").textContent = "";
  });
}

// =========================================================================
// SIMULATION TRIGGER & POLLING
// =========================================================================
async function triggerSimulation() {
  const generator = document.getElementById("select-generator").value;
  const sampleSize = parseInt(document.getElementById("input-sample-size").value) || 100000;
  const trials = parseInt(document.getElementById("input-trials").value) || 20000;
  const deltaMinutes = parseFloat(document.getElementById("input-delta-minutes").value) || 40.0;
  const seed = parseInt(document.getElementById("input-seed").value) || 42;
  const benchmark = document.getElementById("check-benchmark").checked;

  const payload = {
    generator: generator,
    sample_size: sampleSize,
    trials: trials,
    delta_minutes: deltaMinutes,
    seed: seed,
    benchmark: benchmark
  };

  setUIRunningState(true);

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!data.success) {
      alert(data.message || "Simülasyon başlatılamadı.");
      setUIRunningState(false);
      return;
    }
    // Speed up polling while running
    restartPolling(600);
  } catch (err) {
    console.error("Simülasyon tetikleme hatası:", err);
    alert("Sunucuyla bağlantı kurulamadı.");
    setUIRunningState(false);
  }
}

function startStatusPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(checkStatus, 1500);
}

function restartPolling(intervalMs) {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(checkStatus, intervalMs);
}

async function checkStatus() {
  try {
    const res = await fetch("/api/poll");
    const data = await res.json();

    updateProgressUI(data);

    if (data.is_running) {
      setUIRunningState(true);
    } else {
      setUIRunningState(false);
      // If just finished or has result, fetch latest results
      if (data.has_result && !currentResults) {
        fetchLatestResults();
      }
    }
  } catch (err) {
    // Server might be temporarily busy
  }
}

function updateProgressUI(data) {
  const pct = data.progress_pct || 0;
  document.getElementById("progress-percent").textContent = `${pct}%`;
  document.getElementById("progress-bar-fill").style.width = `${pct}%`;
  document.getElementById("progress-step-name").textContent = data.current_step || "Hazır";

  // Terminal logs
  if (data.logs && data.logs.length > 0) {
    const term = document.getElementById("terminal-view");
    term.textContent = data.logs.join("\n");
    term.scrollTop = term.scrollHeight;

    // Snippet in sidebar
    const lastLog = data.logs[data.logs.length - 1];
    document.getElementById("live-log-snippet").textContent = lastLog;
  }
}

function setUIRunningState(isRunning) {
  const btn = document.getElementById("btn-start-simulation");
  const spinner = document.getElementById("run-spinner");
  const text = document.getElementById("btn-run-text");
  const pill = document.getElementById("system-status-pill");
  const statusText = document.getElementById("status-text");

  if (isRunning) {
    btn.disabled = true;
    spinner.classList.remove("hidden");
    text.textContent = "Simüle Ediliyor...";
    pill.className = "status-pill status-running";
    statusText.textContent = "Çalışıyor...";
  } else {
    btn.disabled = false;
    spinner.classList.add("hidden");
    text.textContent = "🚀 Simülasyonu Başlat";
    pill.className = "status-pill status-ready";
    statusText.textContent = "Hazır";
  }
}

// =========================================================================
// RESULTS RENDERING
// =========================================================================
async function fetchLatestResults() {
  try {
    const res = await fetch("/api/results");
    const data = await res.json();
    if (data.has_result === false) return;

    currentResults = data;
    renderResults(data);
  } catch (err) {
    console.error("Sonuçlar alınamadı:", err);
  }
}

function renderResults(data) {
  // 1. KPI Cards
  renderKPICards(data);

  // 2. Comparison Table
  renderComparisonTable(data.comparison_40min || []);

  // 3. 12-Test Battery & FDR Table
  renderTestBatteryTable(data.statistical_battery || {});

  // 4. Report Markdown
  if (data.report_markdown) {
    document.getElementById("markdown-viewer").textContent = data.report_markdown;
  }

  // 5. Reload images with cache buster
  const timestamp = Date.now();
  document.querySelectorAll(".chart-preview img").forEach(img => {
    const baseSrc = img.src.split("?")[0];
    if (baseSrc) {
      img.src = `${baseSrc}?t=${timestamp}`;
    }
  });
}

function renderKPICards(data) {
  // Classification
  const cardClass = document.getElementById("card-classification");
  const classTitle = document.getElementById("kpi-class-title");
  const classDesc = document.getElementById("kpi-class-desc");
  const classIcon = document.getElementById("class-icon");

  const tier = data.classification ? data.classification.tier : 1;
  cardClass.className = "kpi-card kpi-classification";

  if (tier === 3) {
    cardClass.classList.add("tier-anomaly");
    classTitle.textContent = "Kategori 3";
    classDesc.textContent = "Tekrarlanabilir İstatistiksel Anomali Saptandı!";
    classIcon.textContent = "🚨";
  } else if (tier === 2) {
    cardClass.classList.add("tier-suspicious");
    classTitle.textContent = "Kategori 2";
    classDesc.textContent = "Daha fazla veriyle araştırılması gereken şüpheli bulgular var.";
    classIcon.textContent = "⚠️";
  } else {
    cardClass.classList.add("tier-normal");
    classTitle.textContent = "Kategori 1";
    classDesc.textContent = "Belirgin istatistiksel anomali gözlenmedi. Uniform ile uyumlu.";
    classIcon.textContent = "🛡️";
  }

  // Find primary pair result
  const primaryModel = data.primary_model || "UniformReference";
  const comparison = data.comparison_40min || [];
  const primaryPair = comparison.find(c => c.generator_name === primaryModel) || comparison[0];

  if (primaryPair) {
    const rate = (primaryPair.prefix_collision_rate * 100).toFixed(4);
    const count = primaryPair.prefix_collisions;
    const trials = primaryPair.trials;
    const ratio = (primaryPair.prefix_collision_rate / 0.001).toFixed(2);

    document.getElementById("kpi-collision-rate").textContent = `%${rate}`;
    document.getElementById("kpi-collision-count").textContent = count.toLocaleString();
    document.getElementById("kpi-collision-trials").textContent = trials.toLocaleString();
    document.getElementById("kpi-collision-ratio").textContent = ratio;
  }

  // Chi-Square
  const battery = data.statistical_battery || {};
  const chi2 = battery.chi2_prefix || {};
  if (chi2.p_value !== undefined) {
    document.getElementById("kpi-chi2-p").textContent = `p = ${chi2.p_value.toExponential(3)}`;
    document.getElementById("kpi-chi2-stat").textContent = chi2.chi2_statistic.toFixed(1);
    document.getElementById("kpi-chi2-cochran").textContent = chi2.assumptions_met ? "Geçerli" : "İhlal";
  }

  // Entropy
  const ent = battery.entropy ? battery.entropy.first_3_digits : {};
  if (ent.observed_entropy_bits !== undefined) {
    document.getElementById("kpi-entropy-val").textContent = `${ent.observed_entropy_bits.toFixed(4)} bit`;
    document.getElementById("kpi-entropy-eff").textContent = `%${(ent.efficiency * 100).toFixed(2)}`;
    document.getElementById("kpi-entropy-loss").textContent = `${ent.deficiency_bits.toFixed(4)} bit`;
  }

  // Runs & Autocorr
  const runs = battery.runs_test || {};
  const autocorr = battery.autocorrelation || {};
  if (runs.p_value !== undefined) {
    const runsOk = runs.p_value >= 0.05;
    document.getElementById("kpi-runs-status").textContent = runsOk ? "Bağımsız" : "Bağımlı!";
    document.getElementById("kpi-runs-status").style.color = runsOk ? "var(--accent-emerald)" : "var(--accent-rose)";
    document.getElementById("kpi-runs-z").textContent = runs.z_score ? runs.z_score.toFixed(2) : "-";
    document.getElementById("kpi-autocorr-p").textContent = autocorr.ljung_box_p ? autocorr.ljung_box_p.toExponential(2) : "-";
  }
}

function renderComparisonTable(comparisonList) {
  const tbody = document.getElementById("tbody-comparison");
  if (!comparisonList || comparisonList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4">Veri bulunamadı.</td></tr>`;
    return;
  }

  const descriptions = {
    "UniformReference": "Discrete Uniform Baseline (NumPy PCG64)",
    "StandardPRNG_MT19937": "Python random.Random (Mersenne Twister MT19937)",
    "Cryptographic_CSPRNG": "Python secrets / İşletim Sistemi Entropi Havuzu",
    "Defect_SeedReuse": "Her 50 çağrıda PRNG tohumunu statik değere sıfırlar",
    "Defect_LowResTimestamp": "Zaman damgasını 40 dakikalık bloklara yuvarlayarak tohumlar",
    "Defect_ShortPeriodLCG": "Kısa döngülü oyuncak LCG üreteci (m=8192)",
    "Defect_DigitBias": "Rakam 1, 2, 3 için 2.5x daha yüksek üretim ağırlığı",
    "Defect_TimeDeterministic": "İlk 3 haneyi 40 dakikalık periyotla harmonik kaydırır",
    "Defect_ModuloBias": "2^20 sayıyı doğrudan modulo 10^6 yaparak ret örneklemesinden kaçar"
  };

  let html = "";
  comparisonList.forEach(row => {
    const name = row.generator_name;
    const desc = descriptions[name] || "Simülasyon Modeli";
    const trials = row.trials ? row.trials.toLocaleString() : "-";
    const colls = row.prefix_collisions ? row.prefix_collisions.toLocaleString() : 0;
    const rate = (row.prefix_collision_rate * 100).toFixed(4);

    const pTest = row.prefix_test || {};
    const ci = pTest.wilson_ci_95 || [0, 0];
    const ciStr = `[%${(ci[0] * 100).toFixed(4)}, %${(ci[1] * 100).toFixed(4)}]`;
    const pVal = pTest.p_value !== undefined ? pTest.p_value.toExponential(3) : "-";

    const isAnomaly = pTest.p_value !== undefined && pTest.p_value < 0.05;
    const badgeHtml = isAnomaly
      ? `<span class="badge badge-danger">Anomali</span>`
      : `<span class="badge badge-success">Normal</span>`;

    html += `
      <tr>
        <td><strong>${name}</strong></td>
        <td><small class="text-muted">${desc}</small></td>
        <td>${trials}</td>
        <td><b>${colls}</b></td>
        <td><b style="color: ${isAnomaly ? 'var(--accent-rose)' : 'var(--text-main)'}">%${rate}</b></td>
        <td><small class="font-mono">${ciStr}</small></td>
        <td><small class="font-mono">${pVal}</small></td>
        <td>${badgeHtml}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

function renderTestBatteryTable(battery) {
  const tbody = document.getElementById("tbody-fdr");
  const fdrList = battery.multiple_testing || [];

  if (fdrList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4">Test sonuçları hazır değil.</td></tr>`;
    return;
  }

  const descriptions = {
    "Chi2_Prefix_Uniformity": "İlk 3 hane (000-999) 1.000 kategori homojenlik testi",
    "Runs_Test_Randomness": "Wald-Wolfowitz medyan bazlı ardışık rastlantısallık",
    "Serial_Transition_Test": "Ardışık kod geçiş matrisi bağımsızlık testi (10x10)",
    "Ljung_Box_Autocorrelation": "50 gecikmeye kadar kümülatif otokorelasyon beyaz gürültü testi",
    "Chi2_Position_0": "Hane 0 (En sol rakam) 0-9 frekans uniformluk testi",
    "Chi2_Position_1": "Hane 1 0-9 frekans uniformluk testi",
    "Chi2_Position_2": "Hane 2 0-9 frekans uniformluk testi",
    "Chi2_Position_3": "Hane 3 0-9 frekans uniformluk testi",
    "Chi2_Position_4": "Hane 4 0-9 frekans uniformluk testi",
    "Chi2_Position_5": "Hane 5 (En sağ rakam) 0-9 frekans uniformluk testi"
  };

  let html = "";
  fdrList.forEach(item => {
    const name = item.test_name;
    const desc = descriptions[name] || "İstatistiksel Doğrulama Testi";
    const rawP = item.raw_p_value.toExponential(3);
    const fdrP = item.fdr_adj_p_value.toExponential(3);
    const isSig = item.significant_at_05;

    const badge = isSig
      ? `<span class="badge badge-danger">Reddedildi (Anomali)</span>`
      : `<span class="badge badge-success">Kabul (Normal)</span>`;

    html += `
      <tr>
        <td><code>${name}</code></td>
        <td>${desc}</td>
        <td><span class="font-mono">${rawP}</span></td>
        <td><span class="font-mono font-bold">${fdrP}</span></td>
        <td>${badge}</td>
        <td>${isSig ? 'Sıfır hipotezi reddedildi (Dağılım bozuk)' : 'Beklenen teorik değerle uyumlu'}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// =========================================================================
// BIRTHDAY PARADOX CALCULATOR
// =========================================================================
function setupBirthdayCalculator() {
  const slider = document.getElementById("calc-n-slider");
  const input = document.getElementById("calc-n-input");
  const selectM = document.getElementById("calc-m-select");

  slider.addEventListener("input", (e) => {
    input.value = e.target.value;
    updateBirthdayCalculation();
  });

  input.addEventListener("input", (e) => {
    slider.value = e.target.value;
    updateBirthdayCalculation();
  });

  selectM.addEventListener("change", () => {
    updateBirthdayCalculation();
  });

  updateBirthdayCalculation();
}

function setBirthdayN(val) {
  document.getElementById("calc-n-slider").value = val;
  document.getElementById("calc-n-input").value = val;
  updateBirthdayCalculation();
}

function updateBirthdayCalculation() {
  const n = parseInt(document.getElementById("calc-n-input").value) || 38;
  const m = parseInt(document.getElementById("calc-m-select").value) || 1000;

  document.getElementById("calc-n-display").textContent = `${n} Kod`;

  // Compute exact birthday paradox in JS
  let logNoCollision = 0.0;
  for (let k = 0; k < n; k++) {
    if (k >= m) {
      logNoCollision = -Infinity;
      break;
    }
    logNoCollision += Math.log(1.0 - k / m);
  }

  const probCollision = logNoCollision === -Infinity ? 1.0 : (1.0 - Math.exp(logNoCollision));
  const probPct = Math.min(100.0, Math.max(0.0, probCollision * 100.0));

  const totalPairs = (n * (n - 1)) / 2;
  const expectedPairs = totalPairs / m;
  const singlePairProb = 1.0 / m;

  document.getElementById("calc-prob-result").textContent = `%${probPct.toFixed(2)}`;
  document.getElementById("calc-prob-bar").style.width = `${probPct}%`;

  document.getElementById("calc-pair-prob").textContent = `%${(singlePairProb * 100).toFixed(4)}`;
  document.getElementById("calc-pair-count").textContent = `${totalPairs.toLocaleString()} Çift`;
  document.getElementById("calc-expected-pairs").textContent = expectedPairs.toFixed(2);
}

// =========================================================================
// IMAGE MODAL
// =========================================================================
function setupImageModal() {
  const modal = document.getElementById("image-modal");
  const closeBtn = document.getElementById("btn-close-modal");

  closeBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.add("hidden");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) {
      modal.classList.add("hidden");
    }
  });
}

function openImageModal(imgSrc, title) {
  const modal = document.getElementById("image-modal");
  const img = document.getElementById("modal-image-elem");
  const titleElem = document.getElementById("modal-image-title");

  const timestamp = Date.now();
  img.src = `${imgSrc}?t=${timestamp}`;
  titleElem.textContent = title || "Teşhis Grafiği";
  modal.classList.remove("hidden");
}
