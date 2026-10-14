"""
main.py - 6-Digit Numeric Code Statistical Anomaly & Periodicity Simulator
===========================================================================
CLI Entry Point for the research simulation project.
"""

import argparse
import os
import sys
import time
from typing import Dict, List, Optional, Any

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np

from generators import (
    BaseCodeGenerator,
    UniformReferenceGenerator,
    StandardPRNGGenerator,
    CryptographicGenerator,
    SeedReuseGenerator,
    LowResTimestampSeedGenerator,
    ToyShortPeriodLCGGenerator,
    DigitFrequencyBiasedGenerator,
    TimeDependentDeterministicGenerator,
    ModuloBiasGenerator,
    get_all_generators
)
from collision_analysis import (
    CollisionMath,
    run_40min_pair_experiment
)
from statistics_tests import (
    run_full_statistical_battery,
    FrequencyAnalysis,
    InformationEntropySuite
)
from periodicity import (
    TimeCorrelationAnalysis,
    SpectralPeriodicityAnalysis,
    RecurrenceIntervalAnalysis
)
from experiments import (
    CollisionExperimentRunner,
    SampleScalingBenchmark,
    BirthdayParadoxExperiment
)
from visualization import Visualizer
from reporting import ReportGenerator


def get_generator_by_name(name: str, seed: int = 42) -> BaseCodeGenerator:
    """Instantiates a generator by CLI identifier."""
    name_lower = name.lower()
    if "uniform" in name_lower:
        return UniformReferenceGenerator(seed=seed)
    elif "standard" in name_lower or "mt" in name_lower:
        return StandardPRNGGenerator(seed=seed)
    elif "crypto" in name_lower or "secrets" in name_lower:
        return CryptographicGenerator(seed=seed)
    elif "seedreuse" in name_lower:
        return SeedReuseGenerator(seed=seed, period_calls=50)
    elif "lowres" in name_lower or "timestamp" in name_lower:
        return LowResTimestampSeedGenerator(resolution_seconds=2400.0, base_seed=seed)
    elif "lcg" in name_lower or "shortperiod" in name_lower:
        return ToyShortPeriodLCGGenerator(m=8192, seed=seed)
    elif "digitbias" in name_lower or "bias" in name_lower:
        return DigitFrequencyBiasedGenerator(biased_digits=[1, 2, 3], bias_weight=2.5, seed=seed)
    elif "timedeterministic" in name_lower or "harmonic" in name_lower:
        return TimeDependentDeterministicGenerator(cycle_minutes=40.0, seed=seed)
    elif "modulo" in name_lower:
        return ModuloBiasGenerator(source_bits=20, seed=seed)
    else:
        raise ValueError(f"Bilinmeyen üretici adı: {name}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="6 Haneli Sayısal Kod Üretimi — İstatistiksel Anomali ve Periyot Analiz Simülatörü",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--generator", "-g",
        type=str,
        default="all",
        help="Simüle edilecek üretici: 'all', 'uniform', 'standard', 'crypto', 'seedreuse', 'lowres', 'lcg', 'digitbias', 'timedeterministic', 'modulo'"
    )

    parser.add_argument(
        "--sample-size", "-n",
        type=int,
        default=100_000,
        help="İstatistiksel testler için üretilecek kod sayısı (örn. 1000, 10000, 100000, 1000000)"
    )

    parser.add_argument(
        "--trials", "-t",
        type=int,
        default=50_000,
        help="40 dakikalık aralıklı çift çakışma deneyinin tekrar sayısı"
    )

    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="Tekrarlanabilirlik için sabit random seed"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default="./output",
        help="Grafik ve rapor çıktılarının kaydedileceği dizin"
    )

    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="1k, 10k, 100k, 1M örneklem ölçekleme benchmark'ını çalıştır"
    )

    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Grafik çizimini atla (yalnızca JSON, CSV ve rapor üretir)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ayrıntılı konsol çıktısı"
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 80)
    print("6 HANELİ SAYISAL KOD İSTATİSTİKSEL ANOMALİ VE PERİYOT SİMÜLATÖRÜ")
    print(f"Çıktı Dizini: {os.path.abspath(args.output_dir)}")
    print(f"Random Seed: {args.seed} | Örneklem: {args.sample_size:,} | Çift Deneyi: {args.trials:,}")
    print("=" * 80)

    visualizer = Visualizer(output_dir=args.output_dir)
    reporter = ReportGenerator(output_dir=args.output_dir)

    # 1. GENERATOR SELECTION
    if args.generator.lower() == "all":
        generators_to_test = get_all_generators(seed=args.seed)
    else:
        generators_to_test = [get_generator_by_name(args.generator, seed=args.seed)]

    # 2. RUN COMPARATIVE 40-MIN PAIR EXPERIMENTS
    print("\n[ADIM 1] 40 Dakika Aralıklı Kod Çifti Çakışma Deneyleri Yürütülüyor...")
    comparison_results = []
    entropy_summary = []

    for gen in generators_to_test:
        print(f"  -> Model Test Ediliyor: {gen.name:32s} ... ", end="", flush=True)
        t_start = time.perf_counter()
        res_40m = run_40min_pair_experiment(
            generator=gen,
            trials=args.trials,
            time_delta_seconds=2400.0
        )
        duration = time.perf_counter() - t_start
        obs_rate = res_40m["prefix_collision_rate"] * 100.0
        p_val = res_40m["prefix_test"]["p_value"]
        print(f"Bitti ({duration:.2f}s) | Çakışma Oranı: %{obs_rate:.4f} | p-değeri: {p_val:.4e}")
        comparison_results.append(res_40m)

    # Export CSV summary
    csv_path = reporter.export_csv_summary(comparison_results, filename="results_summary.csv")
    print(f"\n[OK] Çakışma özeti CSV kaydedildi: {csv_path}")

    # 3. DETAILED STATISTICAL BATTERY ON PRIMARY GENERATOR (or each)
    primary_gen = generators_to_test[0]
    print(f"\n[ADIM 2] Ayrıntılı İstatistiksel Test Bataryası Yürütülüyor ({primary_gen.name}, N={args.sample_size:,})...")

    primary_gen.reset(seed=args.seed)
    t_gen_start = time.perf_counter()
    int_array, _ = primary_gen.generate_batch(count=args.sample_size, step_seconds=1.0)
    t_gen = time.perf_counter() - t_gen_start
    print(f"  -> Kod üretimi tamamlandı: {t_gen:.2f} saniyede {args.sample_size:,} adet.")

    # Statistical battery
    stats_battery = run_full_statistical_battery(int_array)

    # Periodicity & Time Analysis
    timestamps = np.linspace(1_700_000_000.0, 1_700_000_000.0 + args.sample_size, args.sample_size)
    time_corr = TimeCorrelationAnalysis.analyze_timestamp_correlation(timestamps, int_array)
    spectral = SpectralPeriodicityAnalysis.detect_dominant_periods(int_array.astype(np.float64)[:10_000])
    recurrence = RecurrenceIntervalAnalysis.analyze_prefix_recurrences(int_array)

    periodicity_data = {
        "time_correlation": time_corr,
        "spectral": spectral,
        "recurrence": recurrence
    }

    # Find the matching 40-minute result for the primary generator
    primary_pair_res = next(r for r in comparison_results if r["generator_name"] == primary_gen.name)

    # Classification
    p_values_to_check = [
        primary_pair_res["prefix_test"]["p_value"],
        stats_battery["chi2_prefix"]["p_value"],
        stats_battery["runs_test"]["p_value"]
    ]
    tier, tier_text = ReportGenerator.classify_result(
        p_values=p_values_to_check,
        prefix_collision_rate=primary_pair_res["prefix_collision_rate"],
        is_periodic=spectral.get("is_periodic", False),
        has_significant_autocorr=stats_battery["autocorrelation"].get("has_significant_autocorr", False)
    )

    print(f"\n[SONUÇ SINIFLANDIRMASI]:\n{tier_text}\n")

    # 4. BUILD AUDIT REPORT & JSON
    report_path = reporter.build_markdown_report(
        generator_name=primary_gen.name,
        sample_size=args.sample_size,
        pair_experiment=primary_pair_res,
        stats_battery=stats_battery,
        periodicity_data=periodicity_data,
        classification_tier=tier,
        classification_text=tier_text,
        filename="audit_report.md"
    )
    print(f"[OK] Ayrıntılı Denetim Raporu üretildi: {report_path}")

    json_data = {
        "config": vars(args),
        "primary_model": primary_gen.name,
        "classification": {"tier": tier, "text": tier_text},
        "comparison_40min": comparison_results,
        "statistical_battery": stats_battery,
        "periodicity": periodicity_data
    }
    json_path = reporter.export_json(json_data, filename="detailed_metrics.json")
    print(f"[OK] Metrikler JSON olarak dışa aktarıldı: {json_path}")

    # 5. VISUALIZATIONS
    if not args.skip_plots:
        print("\n[ADIM 3] Yayın Kalitesinde Grafik Çıktıları Oluşturuluyor...")
        # Fig 1: First 3 digits distribution
        f1 = visualizer.plot_first3_distribution(
            counts=stats_battery["prefix_analysis"]["counts"],
            expected=stats_battery["prefix_analysis"]["expected_per_bin"],
            generator_name=primary_gen.name
        )
        print(f"  -> [Fig 1] İlk 3 Hane Dağılımı: {f1}")

        # Fig 2: Digit positions
        f2 = visualizer.plot_digit_positions(
            digit_matrix=FrequencyAnalysis.analyze_digit_positions(int_array),
            generator_name=primary_gen.name
        )
        print(f"  -> [Fig 2] Hane Pozisyonları Dağılımı: {f2}")

        # Fig 3: Time series
        f3 = visualizer.plot_time_series(
            timestamps=timestamps,
            int_array=int_array,
            generator_name=primary_gen.name
        )
        print(f"  -> [Fig 3] Zaman Serisi Grafiği: {f3}")

        # Fig 4: Interval sweep (lag distribution)
        print("  -> Zaman gecikmesi taraması (lag sweep) yapılıyor...")
        sweep_data = CollisionExperimentRunner.run_interval_sweep(
            generator=primary_gen,
            intervals_minutes=[5.0, 10.0, 20.0, 30.0, 40.0, 60.0, 80.0, 120.0],
            trials=min(10_000, args.trials)
        )
        f4 = visualizer.plot_collision_lag_distribution(sweep_data, generator_name=primary_gen.name)
        print(f"  -> [Fig 4] Gecikmeye Göre Çakışma Oranı: {f4}")

        # Fig 5: Autocorrelation
        f5 = visualizer.plot_autocorrelation(
            autocorr_data=stats_battery["autocorrelation"],
            generator_name=primary_gen.name
        )
        print(f"  -> [Fig 5] Otokorelogram: {f5}")

        # Fig 6: Generator Comparison (if all tested)
        if len(comparison_results) > 1:
            f6 = visualizer.plot_generator_comparison(comparison_results)
            print(f"  -> [Fig 6] Üreteç Karşılaştırma Grafiği: {f6}")

        # Fig 8: Entropy Comparison
        for gen in generators_to_test:
            gen.reset(seed=args.seed)
            sub_arr, _ = gen.generate_batch(count=min(20_000, args.sample_size))
            counts = np.bincount(sub_arr // 1000, minlength=1000)
            h_obs, h_max, _ = InformationEntropySuite.shannon_entropy(counts)
            entropy_summary.append({
                "name": gen.name.replace("Defect_", "Defect:\n"),
                "observed_entropy": h_obs,
                "max_entropy": h_max
            })
        f8 = visualizer.plot_entropy_comparison(entropy_summary)
        print(f"  -> [Fig 8] Entropi Karşılaştırma Grafiği: {f8}")

    # 6. OPTIONAL BENCHMARK
    if args.benchmark:
        print("\n[ADIM 4] Örneklem Büyüklüğü Ölçekleme Benchmark'ı (1k, 10k, 100k, 1M)...")
        bench_data = SampleScalingBenchmark.run_benchmark(
            generator=primary_gen,
            sample_sizes=[1_000, 10_000, 100_000, 1_000_000]
        )
        if not args.skip_plots:
            f7 = visualizer.plot_sample_size_chi2(bench_data, generator_name=primary_gen.name)
            print(f"  -> [Fig 7] Örneklem Büyüklüğü Benchmark Grafiği: {f7}")

    print("\n" + "=" * 80)
    print("SİMÜLASYON VE ANALİZ BAŞARIYLA TAMAMLANDI!")
    print(f"Tüm raporlar, grafikler ve çıktılar şu dizindedir: {os.path.abspath(args.output_dir)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
