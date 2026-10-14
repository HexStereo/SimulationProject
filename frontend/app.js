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
  setupLiveRadar();

  // Load existing results immediately if available
  fetchLatestResults();

  // Poll status periodically (every 1s if running, 4s if idle)
  startStatusPolling();

  // Keepalive heartbeat every 3 seconds to keep server alive
  setInterval(() => {
    fetch("/api/heartbeat", { method: "POST" }).catch(() => {});
  }, 3000);

  // Send shutdown beacon when window is closed
  window.addEventListener("beforeunload", () => {
    try {
      navigator.sendBeacon("/api/shutdown");
    } catch (e) {}
  });
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

// =========================================================================
// MODÜL 1 & MODÜL 2: CANLI RADAR VE TUTARLILIK AKIŞI
// =========================================================================
let liveStreamInterval = null;
let liveIsPaused = false;
let lastCodeIndexRendered = -1;

function setupLiveRadar() {
  // 1. Tohumlama Yöntemi Değişimi (Modül 1)
  const methodSelect = document.getElementById("select-live-method");
  if (methodSelect) {
    methodSelect.addEventListener("change", (e) => {
      fetch("/api/live/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method: e.target.value })
      }).catch(err => console.error("Error setting method:", err));
    });
  }

  // 2. Üretim Hızı Butonları
  const speedContainer = document.getElementById("live-speed-pills");
  if (speedContainer) {
    const pills = speedContainer.querySelectorAll(".pill-btn");
    pills.forEach(pill => {
      pill.addEventListener("click", () => {
        pills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        const eps = parseFloat(pill.getAttribute("data-eps")) || 12.0;
        fetch("/api/live/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ speed: eps })
        }).catch(err => console.error("Error setting speed:", err));
      });
    });
  }

  // 3. Duraklat / Devam Et Butonu
  const btnPause = document.getElementById("btn-live-pause");
  if (btnPause) {
    btnPause.addEventListener("click", () => {
      liveIsPaused = !liveIsPaused;
      fetch("/api/live/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_paused: liveIsPaused })
      }).then(() => {
        updatePauseButtonState(liveIsPaused);
      }).catch(err => console.error("Error toggling pause:", err));
    });
  }

  // 4. Sıfırla Butonu
  const btnReset = document.getElementById("btn-live-reset");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      fetch("/api/live/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset: true })
      }).then(() => {
        pollLiveSnapshot();
      }).catch(err => console.error("Error resetting live engine:", err));
    });
  }

  // 5. Otomatik Başlatma: Uygulama açıldığı an anlık polling başlatılır
  pollLiveSnapshot();
  liveStreamInterval = setInterval(pollLiveSnapshot, 320);
}

function updatePauseButtonState(paused) {
  const icon = document.getElementById("btn-live-pause-icon");
  const text = document.getElementById("btn-live-pause-text");
  const dot = document.getElementById("live-stream-dot");
  const statusText = document.getElementById("live-stream-status-text");

  if (paused) {
    if (icon) icon.textContent = "▶️";
    if (text) text.textContent = "Üretimi Devam Ettir";
    if (dot) dot.style.backgroundColor = "#94a3b8";
    if (statusText) statusText.textContent = "ÜRETİM DURAKLATILDI";
  } else {
    if (icon) icon.textContent = "⏸️";
    if (text) text.textContent = "Üretimi Duraklat";
    if (dot) dot.style.backgroundColor = "var(--accent-emerald)";
    if (statusText) statusText.textContent = "CANLI AKIŞ AKTİF";
  }
}

async function pollLiveSnapshot() {
  try {
    const res = await fetch("/api/live/stream");
    if (!res.ok) return;
    const data = await res.json();
    renderLiveDashboard(data);
  } catch (e) {
    // Sunucu yeniden başlatılırken veya beklemede sessizce atla
  }
}

function renderLiveDashboard(data) {
  if (!data) return;

  // 1. Hız ve Duraklatma Durumu
  const epsElem = document.getElementById("live-current-eps");
  if (epsElem && typeof data.speed_eps === "number") {
    epsElem.textContent = data.speed_eps.toFixed(1);
  }
  if (typeof data.is_paused === "boolean" && data.is_paused !== liveIsPaused) {
    liveIsPaused = data.is_paused;
    updatePauseButtonState(liveIsPaused);
  }

  // 2. Modül 1: Dijital Kod Göstergesi
  if (data.recent_codes && data.recent_codes.length > 0) {
    const latest = data.recent_codes[0];
    const codeStr = String(latest.code_str || "000000").padStart(6, "0");

    const p0 = document.getElementById("live-digit-p0");
    const p1 = document.getElementById("live-digit-p1");
    const p2 = document.getElementById("live-digit-p2");
    const s3 = document.getElementById("live-digit-s3");
    const s4 = document.getElementById("live-digit-s4");
    const s5 = document.getElementById("live-digit-s5");

    if (p0) p0.textContent = codeStr[0];
    if (p1) p1.textContent = codeStr[1];
    if (p2) p2.textContent = codeStr[2];
    if (s3) s3.textContent = codeStr[3];
    if (s4) s4.textContent = codeStr[4];
    if (s5) s5.textContent = codeStr[5];

    const timeElem = document.getElementById("live-meta-time");
    if (timeElem) timeElem.textContent = latest.time_str || "--:--:--";

    const seedElem = document.getElementById("live-meta-seed");
    if (seedElem) {
      const seedVal = String(latest.seed_used);
      seedElem.textContent = seedVal.length > 14 ? seedVal.substring(0, 14) + "…" : seedVal;
      seedElem.title = seedVal;
    }

    const countElem = document.getElementById("live-meta-count");
    if (countElem) countElem.textContent = (data.total_generated || 0).toLocaleString();
  }

  // 3. Modül 2: Tutarlılık & Benzerlik Metrikleri
  // 3.1 Benzersizlik Oranı (Uniqueness)
  const uniqRateElem = document.getElementById("live-uniqueness-rate");
  const uniqBarElem = document.getElementById("live-uniqueness-bar");
  const uniqCountElem = document.getElementById("live-unique-count");
  const totalCountElem = document.getElementById("live-total-count");
  const repeatStatusElem = document.getElementById("live-repeat-status");

  if (uniqRateElem && typeof data.uniqueness_pct === "number") {
    uniqRateElem.textContent = `%${data.uniqueness_pct.toFixed(2)}`;
    if (uniqBarElem) {
      uniqBarElem.style.width = `${Math.min(100, Math.max(0, data.uniqueness_pct))}%`;
      uniqBarElem.className = "mini-progress-fill " + (data.uniqueness_pct >= 98 ? "fill-green" : (data.uniqueness_pct >= 90 ? "fill-amber" : "fill-red"));
    }
  }
  if (uniqCountElem) uniqCountElem.textContent = (data.unique_codes_count || 0).toLocaleString();
  if (totalCountElem) totalCountElem.textContent = (data.total_generated || 0).toLocaleString();
  if (repeatStatusElem) {
    if (data.full_collisions_count > 0) {
      repeatStatusElem.innerHTML = `<span style="color:var(--accent-rose)">⚠️ ${data.full_collisions_count} Tam Tekrar!</span>`;
    } else {
      repeatStatusElem.innerHTML = `<span style="color:var(--accent-emerald)">✓ Sıfır Tekrar</span>`;
    }
  }

  // 3.2 İlk 3 Hane Benzerlik Oranı
  const prefixSimElem = document.getElementById("live-prefix-sim-rate");
  const prefixCollElem = document.getElementById("live-prefix-coll-count");
  if (prefixSimElem && typeof data.prefix_similarity_pct === "number") {
    prefixSimElem.textContent = `%${data.prefix_similarity_pct.toFixed(4)}`;
    if (data.prefix_similarity_pct > 0.5) {
      prefixSimElem.style.color = "var(--accent-rose)";
    } else if (data.prefix_similarity_pct > 0.25) {
      prefixSimElem.style.color = "var(--accent-amber)";
    } else {
      prefixSimElem.style.color = "var(--accent-emerald)";
    }
  }
  if (prefixCollElem) prefixCollElem.textContent = (data.prefix_collisions_count || 0).toLocaleString();

  // 3.3 Hane Bazlı Hamming Benzerliği
  const digitSimElem = document.getElementById("live-digit-sim-rate");
  const avgDigitsElem = document.getElementById("live-avg-digits");
  if (digitSimElem && typeof data.digit_similarity_pct === "number") {
    digitSimElem.textContent = `%${data.digit_similarity_pct.toFixed(2)}`;
    if (digitSimElem) {
      digitSimElem.style.color = data.digit_similarity_pct > 20.0 ? "var(--accent-rose)" : "#ffffff";
    }
  }
  if (avgDigitsElem && typeof data.avg_matched_digits === "number") {
    avgDigitsElem.textContent = data.avg_matched_digits.toFixed(2);
  }

  // 3.4 Shannon Entropisi
  const entropyElem = document.getElementById("live-entropy-rate");
  const entropyEffElem = document.getElementById("live-entropy-eff");
  if (entropyElem && typeof data.rolling_entropy_bits === "number") {
    entropyElem.textContent = `${data.rolling_entropy_bits.toFixed(3)} bit`;
  }
  if (entropyEffElem && typeof data.entropy_efficiency_pct === "number") {
    entropyEffElem.textContent = `%${data.entropy_efficiency_pct.toFixed(1)}`;
  }

  // 3.5 Anomali Rozeti ve Açıklama Kutusu
  const anomalyPill = document.getElementById("live-anomaly-pill");
  const anomalyBadgeText = document.getElementById("live-anomaly-badge-text");
  const anomalyBox = document.getElementById("live-anomaly-box");
  const anomalyDetailText = document.getElementById("live-anomaly-detail-text");

  if (anomalyBadgeText && data.anomaly_text) {
    anomalyBadgeText.textContent = data.anomaly_text;
  }
  if (anomalyPill) {
    if (data.anomaly_level === "CRITICAL_ANOMALY") {
      anomalyPill.className = "status-pill status-error";
    } else if (data.anomaly_level === "SUSPICIOUS") {
      anomalyPill.className = "status-pill status-running";
    } else {
      anomalyPill.className = "status-pill status-ready";
    }
  }

  if (anomalyBox) {
    if (data.anomaly_level === "CRITICAL_ANOMALY") {
      anomalyBox.className = "live-alert-box alert-critical";
    } else if (data.anomaly_level === "SUSPICIOUS") {
      anomalyBox.className = "live-alert-box alert-suspicious";
    } else {
      anomalyBox.className = "live-alert-box alert-normal";
    }
  }

  if (anomalyDetailText) {
    if (data.anomaly_reasons && data.anomaly_reasons.length > 0) {
      anomalyDetailText.innerHTML = data.anomaly_reasons.map(r => `• ${r}`).join("<br>");
    } else {
      anomalyDetailText.textContent = "Sistem tutarlı. Çıktılar rastlantısal bağımsızlık kriterlerini sağlıyor.";
    }
  }

  // 3.6 Son Çakışma Özeti
  const lastCollElem = document.getElementById("live-last-collision-summary");
  if (lastCollElem && data.last_collision_summary) {
    lastCollElem.textContent = data.last_collision_summary;
  }

  // 4. Tablo 1: Canlı Kod Akış Ticker'ı (Modül 1)
  const tbodyStream = document.getElementById("tbody-live-stream");
  if (tbodyStream && data.recent_codes && data.recent_codes.length > 0) {
    tbodyStream.innerHTML = data.recent_codes.slice(0, 15).map((c, i) => {
      const isNew = (i === 0 && c.index !== lastCodeIndexRendered);
      const rowClass = isNew ? "row-new" : "";
      const codeStr = String(c.code_str || "000000").padStart(6, "0");
      const prefix = codeStr.substring(0, 3);
      const suffix = codeStr.substring(3, 6);
      const seedStr = String(c.seed_used || "");
      const shortSeed = seedStr.length > 12 ? seedStr.substring(0, 12) + "…" : seedStr;

      return `<tr class="${rowClass}">
        <td><b>#${c.index}</b></td>
        <td class="mono">${c.time_str}</td>
        <td>
          <span style="color:var(--accent-cyan); font-weight:700; font-family:'JetBrains Mono'">${prefix}</span>
          <span style="color:var(--text-dim)">•</span>
          <span style="color:var(--accent-emerald); font-weight:700; font-family:'JetBrains Mono'">${suffix}</span>
        </td>
        <td><span class="badge badge-neutral">${prefix}</span></td>
        <td class="mono" style="font-size:0.75rem; color:var(--text-dim);" title="${seedStr}">${shortSeed}</td>
      </tr>`;
    }).join("");

    if (data.recent_codes.length > 0) {
      lastCodeIndexRendered = data.recent_codes[0].index;
    }
  }

  // 5. Tablo 2: Anlık Çakışma & Benzerlik Günlüğü (Modül 2)
  const tbodyColl = document.getElementById("tbody-live-collisions");
  if (tbodyColl) {
    if (data.recent_collisions && data.recent_collisions.length > 0) {
      tbodyColl.innerHTML = data.recent_collisions.slice(0, 10).map(coll => {
        const isFull = coll.event_type === "full_6";
        const badgeClass = isFull ? "badge-danger" : "badge-warning";
        const badgeLabel = isFull ? "TAM KOD" : "İLK 3 HANE";
        const rowClass = isFull ? "row-collision-full" : "row-collision";

        return `<tr class="${rowClass}">
          <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
          <td class="mono font-bold" style="color:var(--accent-amber)">${coll.matched_value}</td>
          <td class="mono">${coll.current_code}</td>
          <td class="mono">${coll.previous_code}</td>
          <td><b>${coll.step_delta}</b> adım</td>
          <td><b>${coll.time_delta_seconds.toFixed(2)}</b>s</td>
        </tr>`;
      }).join("");
    } else {
      tbodyColl.innerHTML = '<tr><td colspan="6" class="text-center py-3">Henüz çakışma tespit edilmedi.</td></tr>';
    }
  }
}

