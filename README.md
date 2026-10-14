# 6 Haneli Sayısal Kod Üretimi — İstatistiksel Anomali ve Periyot Analiz Simülatörü

Bu proje; bir yoklama/doğrulama sisteminde sunucu tarafından üretilen 6 haneli numerik kodların ilk 3 hanesinde yaklaşık 40 dakika arayla iki farklı kod arasında gözlemlenen eşleşmenin **normal rastlantısal çakışma mı** yoksa **algoritmik/PRNG kaynaklı bir kusur mu** olduğunu araştıran bilimsel, istatistiksel ve tekrarlanabilir bir analiz simülatörüdür.

---

## 📌 Proje Yapısı

```
SimulationProject/
│
├── time_generator.py      # [MODÜL 1] Zamana Bağlı Random Seed & 6-Haneli Kod Üretici
├── live_evaluator.py      # [MODÜL 2] Canlı Tutarlılık, Benzerlik ve Anomali Analizörü
├── desktop_app.py        # Masaüstü uygulaması başlatıcısı (Edge App Mode)
├── desktop_server.py     # REST API & Canlı Akış / Simülasyon Sunucusu
├── launch.bat             # Windows masaüstü çift tıklama başlatıcı betiği
├── create_desktop_shortcut.py # Masaüstüne .lnk kısayolu oluşturan araç
├── assets/                # Uygulama ikonları (.ico ve .png)
│   ├── icon.ico
│   └── icon.png
├── frontend/              # Canlı Radar & Dark Glassmorphism Masaüstü Arayüzü
│   ├── index.html
│   ├── style.css
│   └── app.js
├── generators.py          # Uniform, PRNG, CSPRNG ve 6 adet kontrollü kusurlu üretici modeli
├── collision_analysis.py  # Doğum günü problemi matematiği, Wilson CI, binomial hipotez testleri
├── statistics_tests.py    # Chi-Square (Cochran + Monte Carlo), Entropi, Runs, Otokorelasyon, FDR
├── periodicity.py         # Pearson/Spearman zaman korelasyonu, FFT spektral analiz, tekrar aralığı
├── experiments.py         # 40-dakika çift çakışma deneyleri, 1k..1M örneklem ölçekleme benchmark'ı
├── visualization.py       # 8 adet yayın kalitesinde Matplotlib grafik üreticisi (PNG)
├── reporting.py           # Markdown denetim raporu, CSV ve JSON çıktı serileştiricileri
├── main.py                # CLI giriş noktası ve parametre yöneticisi
├── requirements.txt       # Python bağımlılıkları (NumPy, SciPy, pandas, Matplotlib, pytest)
│
├── tests/                 # Kapsamlı birim ve istatistiksel doğrulama testleri (30 Test)
│   ├── __init__.py
│   ├── test_live_engine.py # Modül 1 ve Modül 2 canlı motor testleri
│   ├── test_generators.py
│   ├── test_statistics.py
│   ├── test_collision.py
│   ├── test_periodicity.py
│   └── test_server.py
```

---

## 📡 2 Ayrık Modüllü Canlı Mimari

Proje iki ana modül ve gerçek zamanlı bir izleme radarı üzerine kuruludur:

### 1. Modül 1: Zamana Bağlı Random Seed & Kod Üretici (`time_generator.py`)
- Sistem zaman damgasını (mikrosaniye, saniye veya periyodik dalga) girdi olarak alır.
- Algoritmik yöntemlerle dinamik tohumlar (seeds) türetir ve 6 haneli kodlar üretir (`000000` - `999999`).
- Desteklenen tohumlama modları:
  1. `high_res_crypto`: Mikrosaniye + OS kriptografik entropi karması (İdeal referans).
  2. `standard_second`: Saniye çözünürlüklü tohumlama (Aynı saniye içinde gelen tüm isteklere aynı kodu üreten kusurlu model).
  3. `coarse_periodic_40m`: 40 dakikalık periyodik döngüsel kovan tohumlama.
  4. `harmonic_drift`: Zamana bağlı ilk 3 hane faz kayması (deterministik ilk 3 hane).
  5. `linear_congruential_time`: LCG zaman damgası çarpanı ile kısa periyotlu tohumlama.
  6. `digit_biased_time`: Belirli rakamlara ağırlık veren zaman sapması modeli.

### 2. Modül 2: Canlı Tutarlılık, Benzerlik ve Anomali Analizörü (`live_evaluator.py`)
- Modül 1'den akan kodları gerçek zamanlı tamponlarda işler:
  - **Benzersizlik Oranı (Uniqueness %):** Sistemin her an farklı çıktılar üretip üretmediğini, mükerrer kodların varlığını anlık ölçer.
  - **İlk 3 Hane Ardışık Benzerlik Oranı:** İki ardışık kodun ilk 3 hanesinin aynı olma olasılığı (Teorik beklenti: `%0.1000`).
  - **Hane Bazlı Hamming Benzerliği:** 6 basamak üzerinde ardışık benzerlik oranı (Teorik beklenti: `%10.00`).
  - **Rolling Shannon Entropisi:** 1000 kovan üzerinden anlık bilgi entropisi (Maksimum 9.9658 bit).
  - **Anomali Skoru ve Risk Seviyesi:** Sapmaları saptadığında anında uyarı rozeti ve gerekçeleri sunar.

### 3. Otomatik Canlı Başlatma
- Masaüstü uygulaması açıldığı andan itibaren arka planda `LiveStreamingManager` daemon iş parçacığında üretime başlar.
- Arayüz hiçbir butona basmaya gerek kalmadan canlı kod akışını ve anlık tutarlılık göstergelerini her 320ms'de bir günceller.

---

## 🛠️ Kurulum

Python 3.12+ kurulu olmalıdır:

```bash
# 1. Sanal ortam oluşturma ve etkinleştirme
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 2. Bağımlılıkları yükleme
pip install -r requirements.txt
```

---

## 🧪 Testleri Çalıştırma

Tüm birim ve matematiksel doğrulama testlerini çalıştırmak için:

```bash
pytest -v
```

---

## 🖥️ Masaüstü Uygulamasını Çalıştırma (GUI)

### 1. Masaüstü Kısayolu ile (Önerilen)
Masaüstünüzde otomatik olarak oluşturulan **`6-Haneli Kod Simulatoru`** ikonuna çift tıklayarak doğrudan uygulamayı açabilirsiniz.

*Kısayolu yeniden oluşturmak isterseniz:*
```bash
python create_desktop_shortcut.py
```

### 2. Batch veya Terminal ile Çalıştırma:
```bash
# launch.bat dosyasına çift tıklayabilir veya terminalden çalıştırabilirsiniz:
.\launch.bat

# veya doğrudan Python ile:
python desktop_app.py
```
Uygulama, Microsoft Edge App Mode (veya varsayılan tarayıcı) üzerinden bağımsız, modern koyu temalı bir masaüstü penceresi olarak anında başlatılır.

---

## 🚀 Simülatörü Çalıştırma (CLI Kullanımı)

### 1. Tüm Modelleri 40 Dakika Çift Deneyinde Karşılaştırma & Benchmark:
```bash
python main.py --generator all --sample-size 100000 --trials 30000 --benchmark --output-dir ./output
```

### 2. Yalnızca Kriptografik CSPRNG (`secrets`) Testi:
```bash
python main.py --generator crypto --sample-size 100000 --trials 50000
```

### 3. Belirli Bir Kusurlu Modeli İnceleme (Örn: Zamana Dayalı Deterministik Kayma):
```bash
python main.py --generator timedeterministic --sample-size 50000 --trials 20000
```

### 4. CLI Parametreleri:
- `--generator`, `-g`: `all`, `uniform`, `standard`, `crypto`, `seedreuse`, `lowres`, `lcg`, `digitbias`, `timedeterministic`, `modulo` (Varsayılan: `all`).
- `--sample-size`, `-n`: İstatistiksel testler için üretilecek kod sayısı (Varsayılan: `100,000`).
- `--trials`, `-t`: 40 dakikalık aralıklı çift çakışma deneyinin tekrar sayısı (Varsayılan: `50,000`).
- `--seed`, `-s`: Tekrarlanabilirlik için random seed (Varsayılan: `42`).
- `--benchmark`: 1k, 10k, 100k ve 1,000,000 örneklem ölçekleme kıyaslamasını çalıştırır.
- `--skip-plots`: Grafik çizimini atlar, yalnızca veri ve rapor üretir.
- `--output-dir`, `-o`: Çıktıların yazılacağı dizin (Varsayılan: `./output`).

---

## 📊 Matematiksel ve İstatistiki Çerçeve

### 1. 40 Dakikalık Çakışmanın Doğası:
- **Tek Bir Çift:** 6 haneli kodların ilk 3 hanesi (000..999) 1.000 farklı değer alabilir. İki bağımsız ve uniform kodun ilk 3 hanesinin aynı olma olasılığı tam olarak:
  $$P(\text{ilk 3 hane çakışması}) = \frac{1}{1000} = 0.001 \quad (\%0.1)$$
  Tek bir çiftte bu olayın gözlenmesi tek başına algoritmik bir kusurun kanıtı **değildir** (1000 bağımsız gözlemde 1 kez gerçekleşmesi olağandır).
- **Doğum Günü Paradoksu:** Bir sistem günde $N = 38$ kod ürettiğinde, gün içinde ilk 3 hanesi çakışan **en az bir çift bulunma olasılığı %50'yi aşar**; $N = 60$ kodda **%83'e** ulaşır.
- **Kusur Ayrımı:** Eğer 40 dakika aralıklı çiftlerde çakışma oranı kontrollü binlerce deneyde %0.1'den istatistiksel olarak anlamlı şekilde sapıyorsa ($p < 0.001$), sunucuda zamana dayalı tohumlama (low-res timestamp seed), döngüsel re-seed veya zayıf bir LCG algoritması bulunduğu doğrulanır.
