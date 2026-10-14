"""
time_generator.py - Modül 1: Zamana Bağlı Random Seed & Kod Üretici Motoru
=============================================================================
Bu modül, sistem zaman damgasını (mikrosaniye, saniye veya döngüsel faz)
farklı algoritmik yaklaşımlarla rastgele tohumlara (seed) dönüştürür ve bu tohumlarla
6 haneli sayısal kodlar üretir.

Desteklenen Zaman Tohumlama Yöntemleri:
1. 'high_res_crypto': Mikrosaniye + OS entropi mikseri (İdeal kriptografik referans).
2. 'standard_second': 1 saniye çözünürlüklü zaman damgası (Aynı saniyede gelenler aynı tohumu alır).
3. 'coarse_periodic_40m': 40 dakikalık periyotlarla döngüsel veya periyodik tohumlama.
4. 'harmonic_drift': Zamana bağlı harmonik faz kayması (deterministik ilk 3 hane).
5. 'linear_congruential_time': Zamana dayalı LCG tohumlayıcı.
6. 'fast_system_random': Doğrudan Python secrets CSPRNG akışı.
"""

import hashlib
import math
import os
import random
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


@dataclass
class GeneratedCodeEvent:
    """Tek bir kod üretim olayının tüm zaman ve tohum meta verileri."""
    index: int
    timestamp: float
    time_str: str
    code_int: int
    code_str: str
    prefix: int
    seed_used: int
    method_name: str
    digit_list: List[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "time_str": self.time_str,
            "code_int": self.code_int,
            "code_str": self.code_str,
            "prefix": self.prefix,
            "seed_used": str(self.seed_used),
            "method_name": self.method_name,
            "digit_list": self.digit_list
        }


class TimeSeedEngine:
    """Zamana bağlı tohum ve 6-haneli kod üretici sınıfı."""

    def __init__(self, method: str = "high_res_crypto"):
        self.method = method
        self.counter = 0
        self._last_second = -1
        self._second_rng = None

    def set_method(self, method: str):
        self.method = method

    def generate_next(self, current_time: Optional[float] = None) -> GeneratedCodeEvent:
        """Belirlenen zaman moduna göre bir sonraki 6 haneli kodu üretir."""
        t = current_time if current_time is not None else time.time()
        self.counter += 1

        code_int, seed_val = self._produce_code_by_method(t)
        code_int = int(code_int) % 1_000_000
        code_str = f"{code_int:06d}"
        prefix = code_int // 1000
        digit_list = [int(d) for d in code_str]

        # Mikrosaniyeli zaman biçimi
        time_struct = time.localtime(t)
        ms = int((t % 1) * 1000)
        time_str = f"{time.strftime('%H:%M:%S', time_struct)}.{ms:03d}"

        return GeneratedCodeEvent(
            index=self.counter,
            timestamp=t,
            time_str=time_str,
            code_int=code_int,
            code_str=code_str,
            prefix=prefix,
            seed_used=seed_val,
            method_name=self.method,
            digit_list=digit_list
        )

    def _produce_code_by_method(self, t: float) -> Tuple[int, int]:
        """Seçilen yönteme göre (kod_değeri, kullanılan_tohum) döndürür."""

        if self.method == "high_res_crypto":
            # Mikrosaniye çözünürlüklü zaman + sistem kriptografik entropi karması
            ns = time.time_ns()
            entropy_bytes = os.urandom(8)
            combined = struct.pack(">Q", ns) + entropy_bytes
            seed_hash = hashlib.sha256(combined).digest()
            seed_int = int.from_bytes(seed_hash[:8], byteorder="big")
            rng = random.Random(seed_int)
            code = rng.randint(0, 999_999)
            return code, seed_int

        elif self.method == "standard_second":
            # Saniye hassasiyetli tohum: Her istek o anki tam saniye ile tohumlanır (aynı saniyede mükerrer kod!)
            sec = int(t)
            seed_int = sec
            rng = random.Random(seed_int)
            code = rng.randint(0, 999_999)
            return code, seed_int

        elif self.method == "coarse_periodic_40m":
            # 40 dakikalık blok tohumu (2400 saniye): 40 dakika boyunca aynı veya döngüsel tohum
            bucket = int(t // 2400.0)
            seed_hash = hashlib.sha256(f"bucket_{bucket}".encode()).digest()
            seed_int = int.from_bytes(seed_hash[:8], byteorder="big")
            # Kovan içindeki sıra numarasına göre üretir
            step = int((t % 2400.0) * 10) # 100ms aralık
            rng = random.Random(seed_int + (step % 50)) # Kısa döngü!
            code = rng.randint(0, 999_999)
            return code, seed_int

        elif self.method == "harmonic_drift":
            # Zamana bağlı deterministik kayma: İlk 3 hane zamanın sinüs/faz dalgasıdır
            cycle_sec = 2400.0 # 40 dakika
            phase = (t % cycle_sec) / cycle_sec
            first_3 = int(phase * 1000) % 1000
            # Son 3 hane rastgele
            last_3 = secrets.randbelow(1000)
            code = first_3 * 1000 + last_3
            seed_int = int(phase * 1_000_000)
            return code, seed_int

        elif self.method == "linear_congruential_time":
            # Zaman damgasını LCG çarpanı ile dönüştürür (kısa periyotlu kusurlu model)
            m = 65536
            a = 25173
            c = 13849
            state = int(t * 1000) % m
            next_state = (a * state + c) % m
            code = int((next_state / m) * 1_000_000)
            return code, state

        elif self.method == "digit_biased_time":
            # Zamana göre belirli rakamlara (1, 2, 3) 3 kat ağırlık verir
            ns = time.time_ns()
            rng = np.random.default_rng(ns % (2**32))
            weights = np.array([1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
            p = weights / weights.sum()
            digits = rng.choice(10, size=6, p=p)
            code = int("".join(str(d) for d in digits))
            return code, ns

        else: # default: pure CSPRNG
            code = secrets.randbelow(1_000_000)
            seed_int = int(time.time() * 1000)
            return code, seed_int
