"""
reporting.py - Automated Audit Reporting, CSV & JSON Serialization
===================================================================
Produces comprehensive Markdown audit reports, structured JSON data,
and tabular CSV summaries. Implements the 3-tier anomaly classification system
and provides cryptographic vs statistical risk assessments.
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd


class ReportGenerator:
    """Generates structured CSV, JSON, and human-readable Markdown audit reports."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def classify_result(
        p_values: List[float],
        prefix_collision_rate: float,
        is_periodic: bool = False,
        has_significant_autocorr: bool = False
    ) -> Tuple[int, str]:
        """
        Classifies findings into one of 3 mandatory categories:
        1. Belirgin istatistiksel anomali gözlenmedi (No notable statistical anomaly).
        2. Daha fazla veriyle araştırılması gereken şüpheli bulgular var (Suspicious findings).
        3. Kontrollü deneylerde tekrarlanabilir istatistiksel anomali gözlendi (Reproducible anomaly).
        """
        # Significant deviation in collision rate or severe test rejections
        severe_anomaly = any(p < 1e-4 for p in p_values) or is_periodic
        suspicious_anomaly = any(p < 0.05 for p in p_values) or has_significant_autocorr

        if severe_anomaly:
            return (
                3,
                "KATEGORİ 3: Kontrollü deneylerde tekrarlanabilir istatistiksel anomali gözlendi."
            )
        elif suspicious_anomaly:
            return (
                2,
                "KATEGORİ 2: Daha fazla veriyle araştırılması gereken şüpheli bulgular var."
            )
        else:
            return (
                1,
                "KATEGORİ 1: Belirgin istatistiksel anomali gözlenmedi."
            )

    def export_json(self, data: Dict[str, Any], filename: str = "detailed_metrics.json") -> str:
        """Serializes all experimental metrics to a JSON file."""
        filepath = os.path.join(self.output_dir, filename)

        def sanitize_for_json(obj):
            if isinstance(obj, (int, float, str, bool)) or obj is None:
                return obj
            elif hasattr(obj, "tolist"):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {str(k): sanitize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [sanitize_for_json(i) for i in obj]
            return str(obj)

        clean_data = sanitize_for_json(data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
        return filepath

    def export_csv_summary(
        self,
        comparison_results: List[Dict[str, Any]],
        filename: str = "results_summary.csv"
    ) -> str:
        """Exports comparative experiment metrics to CSV."""
        filepath = os.path.join(self.output_dir, filename)
        rows = []

        for r in comparison_results:
            p_test = r.get("prefix_test", {})
            f_test = r.get("full_test", {})
            ci = p_test.get("wilson_ci_95", (0.0, 0.0))

            rows.append({
                "Generator": r.get("generator_name", "Unknown"),
                "Trials": r.get("trials", 0),
                "Prefix_Collisions": r.get("prefix_collisions", 0),
                "Prefix_Rate_%": r.get("prefix_collision_rate", 0.0) * 100.0,
                "Prefix_Wilson_CI95_Low_%": ci[0] * 100.0,
                "Prefix_Wilson_CI95_High_%": ci[1] * 100.0,
                "Prefix_p_value": p_test.get("p_value", 1.0),
                "Full_Collisions": r.get("full_collisions", 0),
                "Full_p_value": f_test.get("p_value", 1.0)
            })

        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        return filepath

    def build_markdown_report(
        self,
        generator_name: str,
        sample_size: int,
        pair_experiment: Dict[str, Any],
        stats_battery: Dict[str, Any],
        periodicity_data: Dict[str, Any],
        classification_tier: int,
        classification_text: str,
        filename: str = "audit_report.md"
    ) -> str:
        """Constructs a comprehensive, publication-grade Markdown audit report."""
        filepath = os.path.join(self.output_dir, filename)

        p_test = pair_experiment.get("prefix_test", {})
        full_test = pair_experiment.get("full_test", {})
        chi2 = stats_battery.get("chi2_prefix", {})
        ent = stats_battery.get("entropy", {}).get("first_3_digits", {})
        runs = stats_battery.get("runs_test", {})
        autocorr = stats_battery.get("autocorrelation", {})
        time_corr = periodicity_data.get("time_correlation", {})
        spectral = periodicity_data.get("spectral", {})
        recurrence = periodicity_data.get("recurrence", {})

        report_md = f"""# 6 Haneli Sayısal Kod Üretimi — İstatistiksel Anomali ve Periyot Analiz Raporu

**Tarih:** 2026-10-14  
**Analiz Edilen Model:** `{generator_name}`  
**Örneklem Büyüklüğü:** {sample_size:,} kod  
**40-Dakika Çift Deneyi Tekrarı:** {pair_experiment.get('trials', 0):,} çift  

---

## 1. Yönetici Özeti ve Karar Sınıflandırması

> **Resmi Değerlendirme:**  
> ### {classification_text}

*Önemli Güvenlik Notu: Bu istatistiksel değerlendirme, kriptografik güvenlik garantisi DEĞİLDİR. İstatistiksel olarak mükemmel bir uniform dağılım sergileyen bir PRNG (örneğin Python Mersenne Twister MT19937), iç durumu 624 çıktı sonrasında tamamen tahmin edilebilir olduğu için kriptografik olarak güvensiz olabilir.*

---

## 2. 40 Dakikalık Aralıkla İlk 3 Hane Çakışma Deneyi

*Problem İncelemesi: Bir yoklama/doğrulama sisteminde yaklaşık 40 dakika arayla üretilen iki kodun ilk 3 hanesinin aynı olması durumu araştırılmıştır.*

| Parametre | Gözlenen Değer | Teorik Beklenti | Yorum |
| :--- | :--- | :--- | :--- |
| **Deney Sayısı (Çift)** | {pair_experiment.get('trials', 0):,} | - | Bağımsız çiftler |
| **İlk 3 Hane Çakışması** | {pair_experiment.get('prefix_collisions', 0):,} adet | {int(pair_experiment.get('trials', 0) * 0.001):,} adet | Beklenen: %0.1 (1/1000) |
| **Gözlenen Çakışma Oranı** | **%{p_test.get('observed_rate', 0.0) * 100.0:.4f}** | **%0.1000** | Oran Katı: {p_test.get('relative_ratio', 1.0):.2f}x |
| **%95 Wilson Güven Aralığı** | [%{p_test.get('wilson_ci_95', (0,0))[0]*100:.4f}, %{p_test.get('wilson_ci_95', (0,0))[1]*100:.4f}] | %0.1000 içinde olmalı | Güven aralığı |
| **Tam Kod (6 Hane) Çakışması** | {pair_experiment.get('full_collisions', 0)} adet | {pair_experiment.get('trials', 0) * 1e-6:.2f} adet | Teorik: 1 / 1,000,000 |
| **Binomial Test p-değeri** | **{p_test.get('p_value', 1.0):.6e}** | p ≥ 0.05 (H0 reddedilemez) | {'İSTATİSTİKSEL ANOMALİ' if p_test.get('p_value', 1.0) < 0.05 else 'Rastlantısal ile Uyumlu'} |

### 40 Dakikalık Çakışmanın İstatistiki Doğası:
- **Tek bir çift için:** İki bağımsız ve uniform kodun ilk 3 hanesinin tesadüfen aynı olma olasılığı tam olarak **$1 / 1000 = %0.1$**'dir. Dolayısıyla tek bir çiftte bu olayın gözlenmesi tek başına algoritmik bir kusurun kanıtı DEĞİLDİR (1000 olayda 1 kez beklenir).
- **Doğum Günü Paradoksu (Birthday Paradox):** Bir gün veya oturum boyunca $N = 38$ adet kod üretildiğinde, ilk 3 hanesi eşleşen **en az bir çift bulunma olasılığı %50'yi aşar**. $N = 60$ kodda bu olasılık **%83'e** çıkar! 
- **Algoritmik Kusur Belirtisi:** Ancak 40 dakika aralıklı kod çiftlerinde çakışma oranı kontrollü deneylerde tekrarlanabilir biçimde %0.1'in belirgin üzerinde çıkıyorsa (örneğin %1.0 veya %100), sistemde zaman damgasına bağlı periyodik re-seed, zayıf LCG döngüsü veya deterministik bir kayma olduğu kesinleşir.

---

## 3. Ayrıntılı İstatistiksel Test Bataryası (Örneklem N = {sample_size:,})

### A. Frekans ve Uygunluk (Goodness-of-Fit)
- **Kategori Sayısı:** 1,000 (İlk 3 hane: 000..999)
- **Beklenen Kategori Başı Frekans:** {chi2.get('min_expected_count', 0.0):.1f}
- **Cochran Kriterleri:** {'Karşılandı (Test geçerli)' if chi2.get('assumptions_met') else 'Karşılanmadı (Seyrek beklenen frekanslar)'}
- **Kullanılan Yöntem:** `{chi2.get('method_used', 'N/A')}`
- **Chi-Square İstatistiği ($\\\\chi^2$):** {chi2.get('chi2_statistic', 0.0):.2f} (Serbestlik Derecesi: {chi2.get('degrees_of_freedom', 999)})
- **Chi-Square p-değeri:** **{chi2.get('p_value', 1.0):.6e}** ({'Reddedildi (Anomali)' if chi2.get('reject_null_at_05') else 'Uniform dağılımla uyumlu'})

### B. Bilgi Entropisi (Shannon Entropy)
- **Gözlenen İlk 3 Hane Entropisi:** {ent.get('observed_entropy_bits', 0.0):.4f} bit
- **Maksimum Teorik Entropi ($H_{{max}} = \\\\log_2(1000)$):** {ent.get('max_entropy_bits', 9.9658):.4f} bit
- **Entropi Verimliliği:** %{ent.get('efficiency', 1.0)*100:.2f} (Kayıp: {ent.get('deficiency_bits', 0.0):.4f} bit)

### C. Sırasal Bağımlılık ve Rastgelelik (Runs & Autocorrelation)
- **Wald-Wolfowitz Runs Test:**
  - Gözlenen Seri Sayısı (Runs): {runs.get('observed_runs', 0):,} (Beklenen: {runs.get('expected_runs', 0):.1f})
  - Z-Skoru: {runs.get('z_score', 0.0):.3f}
  - p-değeri: **{runs.get('p_value', 1.0):.6e}** ({'Bağımlılık saptandı' if runs.get('reject_null_at_05') else 'Ardışık bağımsızlık korundu'})
- **Ljung-Box Otokorelasyon Testi:**
  - Q-İstatistiği: {autocorr.get('ljung_box_q', 0.0):.2f}
  - p-değeri: **{autocorr.get('ljung_box_p', 1.0):.6e}**
  - Anlamlı Otokorelasyon: {'EVET (Gecikmeli bağımlılık var)' if autocorr.get('has_significant_autocorr') else 'HAYIR (Beyaz gürültü / White noise)'}

### D. Periyot ve Spektral Analiz
- **Zaman Damgası Korelasyonu (Pearson r):** {time_corr.get('pearson_code_vs_time', {}).get('coefficient', 0.0):.4f} (p = {time_corr.get('pearson_code_vs_time', {}).get('p_value', 1.0):.4f})
- **FFT Spektral Tepe Tespiti:** {'Periyodik rezonans tespit edildi!' if spectral.get('is_periodic') else 'Baskın periyot gözlenmedi (Spektrum düz)'}
- **İlk 3 Hane Ortalama Tekrarlama Aralığı:** {recurrence.get('mean_interval', 1000.0) if recurrence.get('mean_interval') is not None else 'N/A'} adım (Teorik: 1,000 adım)

---

## 4. Çoklu Hipotez Test Düzeltmesi (Benjamini-Hochberg FDR)

| Test Adı | Ham p-değeri | Düzeltilmiş p-değeri (FDR) | Anlamlı mı (α=0.05)? |
| :--- | :--- | :--- | :--- |
"""
        for row in stats_battery.get("multiple_testing", []):
            report_md += f"| `{row['test_name']}` | {row['raw_p_value']:.4e} | {row['fdr_adj_p_value']:.4e} | {'ANOMALİ' if row['significant_at_05'] else 'Normal'} |\n"

        report_md += f"""
---

## 5. Bulguların Sınırlamaları

1. **Örneklem Temsiliyeti:** Sentetik simülasyonlar gerçek sunucu altyapısındaki eşzamanlı istek yükünü, saat senkronizasyon kaymalarını (NTP skew) veya load-balancer çoklu iş parçacığı durumlarını tam olarak yansıtmayabilir.
2. **Tek Test Yanılgısı:** Tek bir testin p-değerinin 0.05'in altına inmesi (Tip I hata / False Positive) tek başına algoritmik kusur kanıtı değildir. Karar, FDR düzeltmesi ve çoklu test tutarlılığıyla verilmelidir.
3. **Kriptografik Güvenlik:** İstatistiksel testler (Dieharder, NIST SP 800-22 vb. dahil) rastlantısallığı ölçer; ancak bir üreticinin tahmin edilemezliğini garanti edemez.

---

## 6. Sonuç ve Önerilen Aksiyonlar

### Güvenlik Kritik Doğrulama Kodları İçin Tavsiyeler:
- **`random.Random` (Mersenne Twister) Kesinlikle Kullanılmamalıdır:** 624 ardışık çıktı gözlemlendiğinde tüm gelecek kodlar önceden bilinir.
- **Kriptografik Kaynak (`secrets` / `SystemRandom` / `BCryptGenRandom`):** İşletim sisteminin entropi havuzuna bağlı CSPRNG kullanılmalıdır.
- **Modulo Sapmasından Kaçınılmalıdır:** 6 haneli kod üretirken doğrudan `rand() % 1000000` yapılmamalı, ret örneklemesi (rejection sampling) veya `secrets.randbelow(1000000)` tercih edilmelidir.
- **Zamana Dayalı Seed Engellenmelidir:** PRNG'nin zaman damgasıyla başlatılması veya dakika/saat bazlı re-seed yapılması engellenmelidir.

---
*Rapor HexAI İstatistiksel Anomali Simülatörü v2.0 tarafından otomatik üretilmiştir.*
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_md)

        return filepath
