"""
generators.py - 6-Digit Numeric Code Generators
=================================================
Provides uniform reference, standard PRNG, cryptographic reference,
and controlled defective generators for statistical anomaly simulations.
All generators produce 6-digit codes formatted as '000000'-'999999'
with integer representation in [0, 999999].
"""

import abc
import hashlib
import os
import random
import secrets
import time
from typing import List, Optional, Tuple, Union
import numpy as np


class BaseCodeGenerator(abc.ABC):
    """Abstract base class for all 6-digit numeric code generators."""

    def __init__(self, name: str, description: str, seed: Optional[int] = None):
        self.name = name
        self.description = description
        self.initial_seed = seed
        self._counter = 0

    @abc.abstractmethod
    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        """
        Generates a single 6-digit code.
        Returns:
            Tuple[int, str]: (integer_value, zero_padded_string)
        """
        pass

    def generate_batch(self, count: int, start_timestamp: Optional[float] = None,
                       step_seconds: float = 1.0) -> Tuple[np.ndarray, List[str]]:
        """
        Generates a batch of codes.
        Returns:
            Tuple[np.ndarray, List[str]]: Array of integers (int32) and list of string codes.
        """
        int_arr = np.empty(count, dtype=np.int32)
        str_list = []
        curr_time = start_timestamp if start_timestamp is not None else time.time()

        for i in range(count):
            t = curr_time + (i * step_seconds)
            val, s = self.generate_single(t)
            int_arr[i] = val
            str_list.append(s)
            self._counter += 1

        return int_arr, str_list

    @staticmethod
    def format_code(value: int) -> str:
        """Formats an integer in [0, 999999] as a 6-digit zero-padded string."""
        return f"{int(value) % 1_000_000:06d}"

    @abc.abstractmethod
    def reset(self, seed: Optional[int] = None) -> None:
        """Resets generator state with optional new seed."""
        pass


class UniformReferenceGenerator(BaseCodeGenerator):
    """
    Generator A: Uniform Reference Generator.
    Uses NumPy PCG64 PRNG to draw integers uniformly from discrete uniform U(0, 999999).
    Represents the mathematical ideal baseline.
    """

    def __init__(self, seed: Optional[int] = 42):
        super().__init__(
            name="UniformReference",
            description="Discrete uniform distribution U(0, 999999) via NumPy PCG64",
            seed=seed
        )
        self.rng = np.random.default_rng(seed)

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        val = int(self.rng.integers(0, 1_000_000))
        return val, self.format_code(val)

    def generate_batch(self, count: int, start_timestamp: Optional[float] = None,
                       step_seconds: float = 1.0) -> Tuple[np.ndarray, List[str]]:
        int_arr = self.rng.integers(0, 1_000_000, size=count, dtype=np.int32)
        str_list = [f"{v:06d}" for v in int_arr]
        self._counter += count
        return int_arr, str_list

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.rng = np.random.default_rng(self.initial_seed)
        self._counter = 0


class StandardPRNGGenerator(BaseCodeGenerator):
    """
    Generator B: Standard Python PRNG (random.Random).
    Implements Mersenne Twister MT19937. Fast, statistically uniform for basic uses,
    but NOT cryptographically secure. State can be reconstructed from 624 outputs.
    """

    def __init__(self, seed: Optional[int] = 42):
        super().__init__(
            name="StandardPRNG_MT19937",
            description="Python random.Random (Mersenne Twister MT19937)",
            seed=seed
        )
        self.py_random = random.Random(seed)

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        val = self.py_random.randint(0, 999_999)
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.py_random = random.Random(self.initial_seed)
        self._counter = 0


class CryptographicGenerator(BaseCodeGenerator):
    """
    Generator C: Cryptographic Reference Generator.
    Uses Python 'secrets' module (SystemRandom backed by OS entropy source:
    /dev/urandom on Unix or BCryptGenRandom on Windows).
    Provides cryptographically unpredictable random values.
    """

    def __init__(self, seed: Optional[int] = None):
        super().__init__(
            name="Cryptographic_CSPRNG",
            description="Cryptographically secure PRNG via Python secrets / OS entropy",
            seed=None  # CSPRNG ignores deterministic seeds
        )
        self.sys_random = secrets.SystemRandom()

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        val = self.sys_random.randrange(0, 1_000_000)
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        # CSPRNG is non-deterministic; re-instantiate
        self.sys_random = secrets.SystemRandom()
        self._counter = 0


# =====================================================================
# Controlled Defective Generators (Testing Models - Not Real Attack Tools)
# =====================================================================

class SeedReuseGenerator(BaseCodeGenerator):
    """
    Generator D.1: Seed Reuse Defect.
    Resets the PRNG seed back to a fixed initial value every 'period_calls' generations
    or when explicit reset trigger occurs. Simulates a stateless microservice or AWS Lambda
    restarting its container with a fixed hardcoded seed.
    """

    def __init__(self, seed: int = 12345, period_calls: int = 100):
        super().__init__(
            name="Defect_SeedReuse",
            description=f"Resets PRNG to static seed ({seed}) every {period_calls} calls",
            seed=seed
        )
        self.period_calls = period_calls
        self.py_random = random.Random(seed)

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        if self._counter > 0 and (self._counter % self.period_calls == 0):
            # Reseed defect triggered
            self.py_random = random.Random(self.initial_seed)
        self._counter += 1
        val = self.py_random.randint(0, 999_999)
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.py_random = random.Random(self.initial_seed)
        self._counter = 0


class LowResTimestampSeedGenerator(BaseCodeGenerator):
    """
    Generator D.2: Low-Resolution Timestamp Seed Defect.
    Derives its PRNG seed from the current timestamp rounded to coarse intervals
    (e.g., 60 seconds, 10 minutes, or 40 minutes = 2400 seconds).
    If two requests arrive within the same interval, or if intervals repeat,
    the sequence starts from the exact same state.
    """

    def __init__(self, resolution_seconds: float = 2400.0, base_seed: int = 1000):
        super().__init__(
            name="Defect_LowResTimestamp",
            description=f"Seeds PRNG from timestamp bucketed to {resolution_seconds}s intervals",
            seed=base_seed
        )
        self.resolution_seconds = resolution_seconds
        self.base_seed = base_seed

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        t = timestamp if timestamp is not None else time.time()
        # Bucket timestamp
        bucket = int(t // self.resolution_seconds)
        # Derive seed deterministically from bucket
        seed = int(hashlib.sha256(f"{self.base_seed}_{bucket}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        # First code produced by this bucket's state
        val = rng.randint(0, 999_999)
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.base_seed = seed
        self._counter = 0


class ToyShortPeriodLCGGenerator(BaseCodeGenerator):
    """
    Generator D.3: Short-Period Toy Linear Congruential Generator (LCG).
    X_{n+1} = (a * X_n + c) mod m
    Uses a deliberately small modulus (e.g. m = 4096 or m = 65536) mapped to [0, 999999].
    Guaranteed to repeat its full cycle in very few iterations.
    """

    def __init__(self, m: int = 8192, a: int = 1013904223, c: int = 1664525, seed: int = 42):
        super().__init__(
            name="Defect_ShortPeriodLCG",
            description=f"Toy LCG with very short period m={m}",
            seed=seed
        )
        self.m = m
        self.a = a
        self.c = c
        self.state = seed % m

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        self.state = (self.a * self.state + self.c) % self.m
        # Scale to 6-digit range [0, 999999]
        val = int((self.state / self.m) * 1_000_000) % 1_000_000
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.state = (self.initial_seed if self.initial_seed is not None else 42) % self.m
        self._counter = 0


class DigitFrequencyBiasedGenerator(BaseCodeGenerator):
    """
    Generator D.4: Digit Frequency Bias Defect.
    Generates digits with non-uniform probability distribution.
    For example: Digits '1', '2', '3' or first 3 digits have a 3x higher probability,
    or certain digits are entirely omitted / over-represented.
    """

    def __init__(self, biased_digits: Optional[List[int]] = None,
                 bias_weight: float = 3.0, seed: Optional[int] = 42):
        super().__init__(
            name="Defect_DigitBias",
            description=f"Non-uniform digit probability: digits {biased_digits or [1,2,3]} have {bias_weight}x weight",
            seed=seed
        )
        self.biased_digits = biased_digits if biased_digits is not None else [1, 2, 3]
        self.bias_weight = bias_weight
        self.rng = np.random.default_rng(seed)

        # Build 10-element probability distribution
        weights = np.ones(10, dtype=np.float64)
        for d in self.biased_digits:
            if 0 <= d <= 9:
                weights[d] *= bias_weight
        self.probabilities = weights / weights.sum()

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        digits = self.rng.choice(10, size=6, p=self.probabilities)
        val = int("".join(str(d) for d in digits))
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.rng = np.random.default_rng(self.initial_seed)
        self._counter = 0


class TimeDependentDeterministicGenerator(BaseCodeGenerator):
    """
    Generator D.5: Time-Dependent Deterministic Pattern Defect.
    The code is directly influenced by a mathematical function of timestamp
    (e.g., sine wave or harmonic drift in the first 3 digits based on minutes).
    Simulates a flawed developer attempting to embed hour/minute information into the code.
    """

    def __init__(self, cycle_minutes: float = 40.0, seed: Optional[int] = 42):
        super().__init__(
            name="Defect_TimeDeterministic",
            description=f"First 3 digits deterministically cycle with period of {cycle_minutes} minutes",
            seed=seed
        )
        self.cycle_seconds = cycle_minutes * 60.0
        self.rng = np.random.default_rng(seed)

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        t = timestamp if timestamp is not None else time.time()
        # First 3 digits derived from phase in the cycle [0, 999]
        phase = (t % self.cycle_seconds) / self.cycle_seconds
        first_3 = int(phase * 1000) % 1000

        # Last 3 digits uniform random
        last_3 = int(self.rng.integers(0, 1000))
        val = first_3 * 1000 + last_3
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.rng = np.random.default_rng(self.initial_seed)
        self._counter = 0


class ModuloBiasGenerator(BaseCodeGenerator):
    """
    Generator D.6: Modulo Bias Defect.
    Simulates improper rejection sampling: sampling a power of 2 (e.g., 2^20 = 1,048,576)
    and simply computing raw_val % 1,000,000 without rejecting values >= 1,000,000.
    Values in [0, 48575] have probability 2 / 1,048,576 ≈ 1.907e-6,
    while values in [48576, 999999] have probability 1 / 1,048,576 ≈ 0.954e-6.
    Causes severe skew in the lower range.
    """

    def __init__(self, source_bits: int = 20, seed: Optional[int] = 42):
        super().__init__(
            name="Defect_ModuloBias",
            description=f"Raw 2^{source_bits} integers modulo 1,000,000 (creates 2x bias on 0..48575)",
            seed=seed
        )
        self.source_max = 1 << source_bits  # 1,048,576 for 20 bits
        self.rng = np.random.default_rng(seed)

    def generate_single(self, timestamp: Optional[float] = None) -> Tuple[int, str]:
        raw_val = int(self.rng.integers(0, self.source_max))
        val = raw_val % 1_000_000
        return val, self.format_code(val)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.initial_seed = seed
        self.rng = np.random.default_rng(self.initial_seed)
        self._counter = 0


def get_all_generators(seed: int = 42) -> List[BaseCodeGenerator]:
    """Instantiates and returns all reference and defective generators with consistent seed."""
    return [
        UniformReferenceGenerator(seed=seed),
        StandardPRNGGenerator(seed=seed),
        CryptographicGenerator(seed=seed),
        SeedReuseGenerator(seed=seed, period_calls=50),
        LowResTimestampSeedGenerator(resolution_seconds=2400.0, base_seed=seed),
        ToyShortPeriodLCGGenerator(m=8192, seed=seed),
        DigitFrequencyBiasedGenerator(biased_digits=[1, 2, 3], bias_weight=2.5, seed=seed),
        TimeDependentDeterministicGenerator(cycle_minutes=40.0, seed=seed),
        ModuloBiasGenerator(source_bits=20, seed=seed)
    ]
