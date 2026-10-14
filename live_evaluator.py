"""
live_evaluator.py - Modül 2: Canlı Tutarlılık, Benzerlik ve Anomali Analizörü
=============================================================================
Bu modül, zaman motorundan (Modül 1) anlık olarak akan 6 haneli kod akışını
dinamik olarak inceler:
1. Sistemin her an farklı çıktılar üretip üretmediğini (benzersizlik oranı) ölçer.
2. Ardışık ve geçmiş kodlar arasındaki benzerlik oranını hesaplar:
   - İlk 3 hane benzerlik oranı (Teorik beklenti: %0.1000).
   - Hane bazlı Hamming benzerliği (Teorik beklenti: %10.00).
   - Tam 6-hane çakışması (Teorik beklenti: %0.0001).
3. Çakışma olaylarını ve zaman aralıklarını anlık günceller.
4. Rolling pencerede Shannon bilgi entropisini hesaplar.
5. Anomali tespiti ve risk değerlendirmesi yapar.
"""

from collections import deque
from dataclasses import dataclass
import math
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from time_generator import GeneratedCodeEvent


@dataclass
class CollisionEvent:
    """Tespit edilen bir çakışma olayının meta verileri."""
    event_type: str  # "prefix_3" (İlk 3 hane) veya "full_6" (Tam kod)
    matched_value: str
    current_index: int
    previous_index: int
    step_delta: int
    time_delta_seconds: float
    timestamp: float
    current_code: str
    previous_code: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "matched_value": self.matched_value,
            "current_index": self.current_index,
            "previous_index": self.previous_index,
            "step_delta": self.step_delta,
            "time_delta_seconds": round(self.time_delta_seconds, 3),
            "timestamp": self.timestamp,
            "current_code": self.current_code,
            "previous_code": self.previous_code
        }


class LiveConsistencyEvaluator:
    """Gerçek zamanlı kod akışı üzerinde tutarlılık ve benzerlik ölçüm motoru."""

    def __init__(self, window_size: int = 5000):
        self.window_size = window_size
        self.total_processed = 0

        # Rolling buffers for fast analysis
        self.recent_events: deque[GeneratedCodeEvent] = deque(maxlen=window_size)
        self.prefix_history: Dict[int, List[Tuple[int, float, str]]] = {} # prefix -> list of (index, timestamp, code_str)
        self.code_history: Dict[int, List[Tuple[int, float]]] = {}         # code_int -> list of (index, timestamp)

        # Collision records
        self.recent_collisions: deque[CollisionEvent] = deque(maxlen=50)
        self.total_prefix_collisions = 0
        self.total_full_collisions = 0

        # Similarity metrics
        self.consecutive_hamming_matches = deque(maxlen=window_size) # matched digits out of 6
        self.consecutive_prefix_matches = deque(maxlen=window_size)  # 1 if prefix matches previous code, else 0
        self.rolling_code_window = deque(maxlen=1000)                # last 1000 codes for local uniqueness
        self.last_event: Optional[GeneratedCodeEvent] = None

        # Rolling prefix counts for entropy & chi2
        self.prefix_counts = np.zeros(1000, dtype=np.int32)

        # Performance tracking
        self.start_time = time.time()
        self.last_tick_time = time.time()
        self.current_eps = 0.0 # events per second
        self.recent_tick_counts = deque(maxlen=10)

    def reset(self):
        """Tüm geçmiş verileri ve tamponları sıfırlar."""
        self.total_processed = 0
        self.recent_events.clear()
        self.prefix_history.clear()
        self.code_history.clear()
        self.recent_collisions.clear()
        self.total_prefix_collisions = 0
        self.total_full_collisions = 0
        self.consecutive_hamming_matches.clear()
        self.consecutive_prefix_matches.clear()
        self.rolling_code_window.clear()
        self.last_event = None
        self.prefix_counts.fill(0)
        self.start_time = time.time()
        self.last_tick_time = time.time()
        self.current_eps = 0.0
        self.recent_tick_counts.clear()

    def process_code(self, event: GeneratedCodeEvent) -> Dict[str, Any]:
        """Gelen yeni kodu analiz eder ve güncel metrikleri döndürür."""
        self.total_processed += 1
        curr_idx = event.index
        curr_time = event.timestamp
        curr_code = event.code_int
        curr_prefix = event.prefix
        curr_str = event.code_str

        # 1. Hane Bazlı Benzerlik (Hamming mesafesi / ardışık karşılaştırma)
        digit_match_count = 0
        is_consec_prefix = False
        if self.last_event is not None:
            # Kaç hane bir önceki kodla aynı pozisyonda aynı rakama sahip
            prev_digits = self.last_event.digit_list
            curr_digits = event.digit_list
            digit_match_count = sum(1 for p, c in zip(prev_digits, curr_digits) if p == c)
            self.consecutive_hamming_matches.append(digit_match_count)

            # Ardışık ilk 3 hane eşitliği
            if self.last_event.prefix == curr_prefix:
                is_consec_prefix = True
                self.consecutive_prefix_matches.append(1)
            else:
                self.consecutive_prefix_matches.append(0)

        # 2. İlk 3 Hane Çakışma / Tekrar Analizi (Tüm geçmiş havuzunda)
        is_prefix_collision = False
        if curr_prefix in self.prefix_history and len(self.prefix_history[curr_prefix]) > 0:
            is_prefix_collision = True
            self.total_prefix_collisions += 1
            last_seen_idx, last_seen_time, prev_code_str = self.prefix_history[curr_prefix][-1]
            time_delta = curr_time - last_seen_time
            step_delta = curr_idx - last_seen_idx

            coll = CollisionEvent(
                event_type="prefix_3",
                matched_value=f"{curr_prefix:03d}",
                current_index=curr_idx,
                previous_index=last_seen_idx,
                step_delta=step_delta,
                time_delta_seconds=time_delta,
                timestamp=curr_time,
                current_code=curr_str,
                previous_code=prev_code_str
            )
            self.recent_collisions.appendleft(coll)

        # 3. Tam Kod (6 Hane) Çakışma Analizi
        is_full_collision = False
        if curr_code in self.code_history and len(self.code_history[curr_code]) > 0:
            is_full_collision = True
            self.total_full_collisions += 1
            last_seen_idx, last_seen_time = self.code_history[curr_code][-1]
            time_delta = curr_time - last_seen_time
            step_delta = curr_idx - last_seen_idx

            coll = CollisionEvent(
                event_type="full_6",
                matched_value=curr_str,
                current_index=curr_idx,
                previous_index=last_seen_idx,
                step_delta=step_delta,
                time_delta_seconds=time_delta,
                timestamp=curr_time,
                current_code=curr_str,
                previous_code=curr_str
            )
            self.recent_collisions.appendleft(coll)

        # Güncelleme
        if curr_prefix not in self.prefix_history:
            self.prefix_history[curr_prefix] = []
        self.prefix_history[curr_prefix].append((curr_idx, curr_time, curr_str))

        if curr_code not in self.code_history:
            self.code_history[curr_code] = []
        self.code_history[curr_code].append((curr_idx, curr_time))

        self.rolling_code_window.append(curr_code)
        self.prefix_counts[curr_prefix] += 1
        self.recent_events.appendleft(event)
        self.last_event = event

        return {
            "is_prefix_collision": is_prefix_collision,
            "is_full_collision": is_full_collision,
            "is_consec_prefix": is_consec_prefix,
            "digit_match_count": digit_match_count
        }

    def get_live_metrics(self) -> Dict[str, Any]:
        """Masaüstü arayüzüne gönderilecek anlık tutarlılık göstergelerini hesaplar."""
        n = self.total_processed
        if n == 0:
            return self._empty_metrics()

        # 1. Benzersizlik Oranı (Uniqueness Rate)
        # Yerel pencerede ve toplamda benzersizlik
        rolling_n = len(self.rolling_code_window)
        if rolling_n > 0:
            rolling_unique = len(set(self.rolling_code_window))
            uniqueness_pct = (rolling_unique / rolling_n) * 100.0
        else:
            unique_codes_count = len(self.code_history)
            uniqueness_pct = (unique_codes_count / n) * 100.0
        unique_codes_count = len(self.code_history)

        # 2. Benzerlik Oranı: Ardışık İlk 3 Hane Benzerlik Oranı (Teorik: %0.1000)
        if len(self.consecutive_prefix_matches) > 0:
            prefix_similarity_pct = float(np.mean(self.consecutive_prefix_matches)) * 100.0
        else:
            prefix_similarity_pct = 0.1000

        # 3. Hane Bazlı Benzerlik (Ortalama eşleşen hane / 6 - Teorik: %10.00)
        if len(self.consecutive_hamming_matches) > 0:
            avg_matched_digits = float(np.mean(self.consecutive_hamming_matches))
            digit_similarity_pct = (avg_matched_digits / 6.0) * 100.0
        else:
            avg_matched_digits = 0.6
            digit_similarity_pct = 10.0

        # 4. Rolling Shannon Entropisi (Son 1000 kategori üzerinde)
        total_in_counts = np.sum(self.prefix_counts)
        if total_in_counts > 0:
            p = self.prefix_counts[self.prefix_counts > 0] / float(total_in_counts)
            rolling_entropy = float(-np.sum(p * np.log2(p)))
            entropy_efficiency = (rolling_entropy / math.log2(1000)) * 100.0
        else:
            rolling_entropy = 0.0
            entropy_efficiency = 0.0

        # 5. Anomali Değerlendirmesi
        # Normal şartlarda: İlk 3 hane ardışık benzerlik ~ %0.10, Hane benzerliği ~ %10.0, Benzersizlik ~ %100
        anomaly_score = 0
        anomaly_reasons = []

        if prefix_similarity_pct > 1.0:  # 10x üzerinde
            anomaly_score += 40
            anomaly_reasons.append(f"İlk 3 hane ardışık benzerlik (%{prefix_similarity_pct:.2f}) teorik %0.10'un çok üzerinde!")
        elif prefix_similarity_pct > 0.35: # 3.5x üzerinde
            anomaly_score += 20
            anomaly_reasons.append(f"İlk 3 hane benzerlik oranı hafif yüksek (%{prefix_similarity_pct:.2f}).")

        if digit_similarity_pct > 22.0:   # 2.2x üzerinde
            anomaly_score += 30
            anomaly_reasons.append(f"Hane benzerliği (%{digit_similarity_pct:.1f}) teorik %10.0 beklentisinden belirgin yüksek!")

        if uniqueness_pct < 95.0 and n > 50:
            anomaly_score += 35
            anomaly_reasons.append(f"Benzersizlik oranı (%{uniqueness_pct:.1f}) düşük! Kodlar tekrarlanıyor.")

        if entropy_efficiency < 85.0 and n > 200:
            anomaly_score += 20
            anomaly_reasons.append(f"Shannon entropi verimliliği düşük (%{entropy_efficiency:.1f}).")

        if anomaly_score >= 50:
            anomaly_level = "CRITICAL_ANOMALY"
            anomaly_text = "KRİTİK İSTATİSTİKSEL ANOMALİ"
            status_color = "#f43f5e"
        elif anomaly_score >= 20:
            anomaly_level = "SUSPICIOUS"
            anomaly_text = "ŞÜPHELİ BENZERLİK BELİRTİLERİ"
            status_color = "#f59e0b"
        else:
            anomaly_level = "CONSISTENT_UNIFORM"
            anomaly_text = "SİSTEM TUTARLI & RASTLANTISAL"
            status_color = "#10b981"

        # Son çakışma bilgisi
        last_collision_str = "Henüz çakışma olmadı"
        if len(self.recent_collisions) > 0:
            last_c = self.recent_collisions[0]
            type_label = "İlk 3 Hane" if last_c.event_type == "prefix_3" else "Tam 6 Hane"
            last_collision_str = f"[{type_label}] '{last_c.matched_value}' ({last_c.step_delta} adım önce, {last_c.time_delta_seconds:.1f}s)"

        return {
            "total_generated": n,
            "unique_codes_count": unique_codes_count,
            "uniqueness_pct": round(uniqueness_pct, 2),
            "prefix_collisions_count": self.total_prefix_collisions,
            "prefix_similarity_pct": round(prefix_similarity_pct, 4),
            "theoretical_prefix_similarity_pct": 0.1000,
            "avg_matched_digits": round(avg_matched_digits, 2),
            "digit_similarity_pct": round(digit_similarity_pct, 2),
            "theoretical_digit_similarity_pct": 10.00,
            "full_collisions_count": self.total_full_collisions,
            "rolling_entropy_bits": round(rolling_entropy, 4),
            "max_entropy_bits": 9.9658,
            "entropy_efficiency_pct": round(entropy_efficiency, 2),
            "anomaly_level": anomaly_level,
            "anomaly_text": anomaly_text,
            "anomaly_score": anomaly_score,
            "status_color": status_color,
            "anomaly_reasons": anomaly_reasons,
            "last_collision_summary": last_collision_str,
            "recent_collisions": [c.to_dict() for c in list(self.recent_collisions)[:10]],
            "recent_codes": [e.to_dict() for e in list(self.recent_events)[:25]]
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "total_generated": 0,
            "unique_codes_count": 0,
            "uniqueness_pct": 100.0,
            "prefix_collisions_count": 0,
            "prefix_similarity_pct": 0.0,
            "theoretical_prefix_similarity_pct": 0.1000,
            "avg_matched_digits": 0.6,
            "digit_similarity_pct": 10.00,
            "theoretical_digit_similarity_pct": 10.00,
            "full_collisions_count": 0,
            "rolling_entropy_bits": 0.0,
            "max_entropy_bits": 9.9658,
            "entropy_efficiency_pct": 100.0,
            "anomaly_level": "CONSISTENT_UNIFORM",
            "anomaly_text": "SİSTEM BAŞLATILIYOR...",
            "anomaly_score": 0,
            "status_color": "#38bdf8",
            "anomaly_reasons": [],
            "last_collision_summary": "Bekleniyor",
            "recent_collisions": [],
            "recent_codes": []
        }
