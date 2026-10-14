"""
desktop_server.py - Lightweight REST API & Web Server for Desktop Frontend
============================================================================
Runs locally on 127.0.0.1, serving the frontend UI and providing APIs for:
- Triggering simulations in background worker threads.
- Streaming live progress and logs.
- Returning JSON metrics, CSV data, and report text.
- Interactive Birthday Paradox calculator.
- Opening output directory in Windows Explorer.
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from typing import Dict, Any, Optional

import numpy as np

# Import simulation modules
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
    BinomialInference,
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
    SampleScalingBenchmark
)
from visualization import Visualizer
from reporting import ReportGenerator


# Global simulation state manager
class SimulationState:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.progress_pct = 0
        self.current_step = "Hazır"
        self.logs: list[str] = []
        self.latest_result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.output_dir = os.path.abspath("./output")

    def reset_for_run(self):
        with self.lock:
            self.is_running = True
            self.progress_pct = 0
            self.current_step = "Simülasyon başlatılıyor..."
            self.logs = [f"[{time.strftime('%H:%M:%S')}] Yeni simülasyon başlatıldı."]
            self.error = None

    def add_log(self, message: str, step: Optional[str] = None, pct: Optional[int] = None):
        with self.lock:
            timestamp = time.strftime("%H:%M:%S")
            self.logs.append(f"[{timestamp}] {message}")
            if step is not None:
                self.current_step = step
            if pct is not None:
                self.progress_pct = pct

    def complete(self, result: Dict[str, Any]):
        with self.lock:
            self.is_running = False
            self.progress_pct = 100
            self.current_step = "Tamamlandı"
            self.latest_result = result
            self.logs.append(f"[{time.strftime('%H:%M:%S')}] Simülasyon başarıyla tamamlandı.")

    def fail(self, err_msg: str):
        with self.lock:
            self.is_running = False
            self.error = err_msg
            self.current_step = "Hata oluştu"
            self.logs.append(f"[{time.strftime('%H:%M:%S')}] HATA: {err_msg}")


SIM_STATE = SimulationState()


def execute_simulation_worker(params: Dict[str, Any]):
    """Background worker executing the full simulation pipeline."""
    try:
        gen_type = params.get("generator", "all").lower()
        sample_size = int(params.get("sample_size", 100_000))
        trials = int(params.get("trials", 20_000))
        seed = int(params.get("seed", 42))
        run_benchmark = bool(params.get("benchmark", False))
        delta_minutes = float(params.get("delta_minutes", 40.0))
        output_dir = SIM_STATE.output_dir

        os.makedirs(output_dir, exist_ok=True)
        visualizer = Visualizer(output_dir=output_dir)
        reporter = ReportGenerator(output_dir=output_dir)

        SIM_STATE.add_log(f"Parametreler: Üreteç={gen_type}, Örneklem={sample_size:,}, Çift={trials:,}, Seed={seed}", pct=5)

        # 1. Generator selection
        if gen_type == "all":
            generators = get_all_generators(seed=seed)
        elif "uniform" in gen_type:
            generators = [UniformReferenceGenerator(seed=seed)]
        elif "standard" in gen_type or "mt" in gen_type:
            generators = [StandardPRNGGenerator(seed=seed)]
        elif "crypto" in gen_type or "secrets" in gen_type:
            generators = [CryptographicGenerator(seed=seed)]
        elif "seedreuse" in gen_type:
            generators = [SeedReuseGenerator(seed=seed, period_calls=50)]
        elif "lowres" in gen_type:
            generators = [LowResTimestampSeedGenerator(resolution_seconds=delta_minutes * 60.0, base_seed=seed)]
        elif "lcg" in gen_type:
            generators = [ToyShortPeriodLCGGenerator(m=8192, seed=seed)]
        elif "digitbias" in gen_type:
            generators = [DigitFrequencyBiasedGenerator(biased_digits=[1, 2, 3], bias_weight=2.5, seed=seed)]
        elif "timedeterministic" in gen_type:
            generators = [TimeDependentDeterministicGenerator(cycle_minutes=delta_minutes, seed=seed)]
        elif "modulo" in gen_type:
            generators = [ModuloBiasGenerator(source_bits=20, seed=seed)]
        else:
            generators = get_all_generators(seed=seed)

        # 2. Pair collision experiments
        SIM_STATE.add_log(f"{len(generators)} model için {delta_minutes} dakikalık çift çakışma deneyleri yürütülüyor...",
                          step="40-Dk Çift Deneyleri", pct=15)
        comparison_results = []
        entropy_summary = []

        total_gens = len(generators)
        for idx, gen in enumerate(generators):
            SIM_STATE.add_log(f"-> Model test ediliyor: {gen.name}")
            res_pair = run_40min_pair_experiment(
                generator=gen,
                trials=trials,
                time_delta_seconds=delta_minutes * 60.0
            )
            comparison_results.append(res_pair)
            pct = 15 + int(((idx + 1) / total_gens) * 25)
            SIM_STATE.progress_pct = pct

        csv_path = reporter.export_csv_summary(comparison_results, filename="results_summary.csv")
        SIM_STATE.add_log(f"CSV özeti kaydedildi: {os.path.basename(csv_path)}", pct=42)

        # 3. Detailed battery on primary generator
        primary_gen = generators[0]
        SIM_STATE.add_log(f"Birincil model ({primary_gen.name}) için {sample_size:,} kod üretiliyor...",
                          step="İstatistiksel Test Bataryası", pct=45)

        primary_gen.reset(seed=seed)
        t0 = time.perf_counter()
        int_array, _ = primary_gen.generate_batch(count=sample_size, step_seconds=1.0)
        t_gen = time.perf_counter() - t0
        SIM_STATE.add_log(f"Kod üretimi tamamlandı: {t_gen:.2f} saniyede {sample_size:,} adet.", pct=50)

        SIM_STATE.add_log("12 istatistiksel test (Chi-Square, Entropy, Runs, Otokorelasyon, FDR) hesaplanıyor...", pct=55)
        stats_battery = run_full_statistical_battery(int_array)

        # Periodicity & Time Correlation
        SIM_STATE.add_log("Zaman serisi korelasyonu ve FFT periyodiklik analizi yürütülüyor...", pct=62)
        timestamps = np.linspace(1_700_000_000.0, 1_700_000_000.0 + sample_size, sample_size)
        time_corr = TimeCorrelationAnalysis.analyze_timestamp_correlation(timestamps, int_array)
        spectral = SpectralPeriodicityAnalysis.detect_dominant_periods(int_array.astype(np.float64)[:min(10_000, len(int_array))])
        recurrence = RecurrenceIntervalAnalysis.analyze_prefix_recurrences(int_array)

        periodicity_data = {
            "time_correlation": time_corr,
            "spectral": spectral,
            "recurrence": recurrence
        }

        # 4. Result Classification
        primary_pair = next(r for r in comparison_results if r["generator_name"] == primary_gen.name)
        p_vals = [
            primary_pair["prefix_test"]["p_value"],
            stats_battery["chi2_prefix"]["p_value"],
            stats_battery["runs_test"]["p_value"]
        ]
        tier, tier_text = ReportGenerator.classify_result(
            p_values=p_vals,
            prefix_collision_rate=primary_pair["prefix_collision_rate"],
            is_periodic=spectral.get("is_periodic", False),
            has_significant_autocorr=stats_battery["autocorrelation"].get("has_significant_autocorr", False)
        )

        SIM_STATE.add_log(f"Sınıflandırma: {tier_text}", pct=70)

        # 5. Build Reports
        report_path = reporter.build_markdown_report(
            generator_name=primary_gen.name,
            sample_size=sample_size,
            pair_experiment=primary_pair,
            stats_battery=stats_battery,
            periodicity_data=periodicity_data,
            classification_tier=tier,
            classification_text=tier_text,
            filename="audit_report.md"
        )

        json_data = {
            "primary_model": primary_gen.name,
            "sample_size": sample_size,
            "trials": trials,
            "delta_minutes": delta_minutes,
            "classification": {"tier": tier, "text": tier_text},
            "comparison_40min": comparison_results,
            "statistical_battery": stats_battery,
            "periodicity": periodicity_data
        }
        json_path = reporter.export_json(json_data, filename="detailed_metrics.json")
        SIM_STATE.add_log("Raporlar ve JSON metrikleri dışa aktarıldı.", pct=75)

        # 6. Generate Figures
        SIM_STATE.add_log("Yayın kalitesinde grafikler oluşturuluyor...", step="Grafik Çizimi", pct=80)
        fig_paths = {}

        fig_paths["fig1"] = visualizer.plot_first3_distribution(
            counts=stats_battery["prefix_analysis"]["counts"],
            expected=stats_battery["prefix_analysis"]["expected_per_bin"],
            generator_name=primary_gen.name
        )
        fig_paths["fig2"] = visualizer.plot_digit_positions(
            digit_matrix=FrequencyAnalysis.analyze_digit_positions(int_array),
            generator_name=primary_gen.name
        )
        fig_paths["fig3"] = visualizer.plot_time_series(
            timestamps=timestamps,
            int_array=int_array,
            generator_name=primary_gen.name
        )

        sweep_data = CollisionExperimentRunner.run_interval_sweep(
            generator=primary_gen,
            intervals_minutes=[5.0, 10.0, 20.0, 30.0, 40.0, 60.0, 80.0, 120.0],
            trials=min(10_000, trials)
        )
        fig_paths["fig4"] = visualizer.plot_collision_lag_distribution(sweep_data, generator_name=primary_gen.name)

        fig_paths["fig5"] = visualizer.plot_autocorrelation(
            autocorr_data=stats_battery["autocorrelation"],
            generator_name=primary_gen.name
        )

        if len(comparison_results) > 1:
            fig_paths["fig6"] = visualizer.plot_generator_comparison(comparison_results)

        for gen in generators:
            gen.reset(seed=seed)
            sub_arr, _ = gen.generate_batch(count=min(20_000, sample_size))
            counts = np.bincount(sub_arr // 1000, minlength=1000)
            h_obs, h_max, _ = InformationEntropySuite.shannon_entropy(counts)
            entropy_summary.append({
                "name": gen.name.replace("Defect_", "Defect:\n"),
                "observed_entropy": h_obs,
                "max_entropy": h_max
            })
        fig_paths["fig8"] = visualizer.plot_entropy_comparison(entropy_summary)

        # Benchmark
        bench_data = []
        if run_benchmark:
            SIM_STATE.add_log("Örneklem büyüklüğü ölçekleme benchmarkı çalıştırılıyor...", step="Benchmark", pct=92)
            bench_data = SampleScalingBenchmark.run_benchmark(
                generator=primary_gen,
                sample_sizes=[1_000, 10_000, 100_000, 1_000_000]
            )
            fig_paths["fig7"] = visualizer.plot_sample_size_chi2(bench_data, generator_name=primary_gen.name)

        SIM_STATE.add_log("Tüm grafikler ve analizler hazır!", pct=98)

        # Read markdown report text
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()

        final_payload = {
            "primary_model": primary_gen.name,
            "sample_size": sample_size,
            "trials": trials,
            "classification": {"tier": tier, "text": tier_text},
            "comparison_40min": comparison_results,
            "statistical_battery": stats_battery,
            "periodicity": periodicity_data,
            "benchmark_results": bench_data,
            "report_markdown": report_text,
            "figures": {k: os.path.basename(v) for k, v in fig_paths.items()}
        }

        SIM_STATE.complete(final_payload)

    except Exception as e:
        import traceback
        err = f"{str(e)}\n{traceback.format_exc()}"
        SIM_STATE.fail(err)


class DesktopRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler serving UI and REST API."""

    def __init__(self, *args, **kwargs):
        # Set directory to project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=project_root, **kwargs)

    def log_message(self, format, *args):
        # Suppress normal stdout spam unless error
        if args and str(args[1]) in ("404", "500"):
            super().log_message(format, *args)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.serve_file(os.path.join("frontend", "index.html"), "text/html; charset=utf-8")
        elif path.startswith("/frontend/"):
            rel_path = path.lstrip("/")
            content_type = "text/plain"
            if rel_path.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif rel_path.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
            elif rel_path.endswith(".html"):
                content_type = "text/html; charset=utf-8"
            self.serve_file(rel_path, content_type)
        elif path == "/api/status":
            self.send_json_response({
                "is_running": SIM_STATE.is_running,
                "progress_pct": SIM_STATE.progress_pct,
                "current_step": SIM_STATE.current_step,
                "error": SIM_STATE.error,
                "has_result": SIM_STATE.latest_result is not None,
                "logs_count": len(SIM_STATE.logs)
            })
        elif path == "/api/poll":
            self.send_json_response({
                "is_running": SIM_STATE.is_running,
                "progress_pct": SIM_STATE.progress_pct,
                "current_step": SIM_STATE.current_step,
                "logs": SIM_STATE.logs[-30:],  # return last 30 logs
                "has_result": SIM_STATE.latest_result is not None,
                "error": SIM_STATE.error
            })
        elif path == "/api/results":
            if SIM_STATE.latest_result:
                self.send_json_response(SIM_STATE.latest_result)
            else:
                # Try loading existing output/detailed_metrics.json
                json_path = os.path.join(SIM_STATE.output_dir, "detailed_metrics.json")
                md_path = os.path.join(SIM_STATE.output_dir, "audit_report.md")
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8") as f:
                            data["report_markdown"] = f.read()
                    data["figures"] = {
                        "fig1": "fig1_first3_distribution.png",
                        "fig2": "fig2_digit_positions.png",
                        "fig3": "fig3_time_series.png",
                        "fig4": "fig4_collision_lag_distribution.png",
                        "fig5": "fig5_autocorrelation.png",
                        "fig6": "fig6_generator_comparison.png",
                        "fig7": "fig7_sample_size_chi2.png",
                        "fig8": "fig8_entropy_comparison.png"
                    }
                    self.send_json_response(data)
                else:
                    self.send_json_response({"has_result": False, "message": "Henüz simülasyon çalıştırılmadı."})
        elif path.startswith("/output/"):
            filename = os.path.basename(path)
            file_path = os.path.join(SIM_STATE.output_dir, filename)
            content_type = "application/octet-stream"
            if filename.endswith(".png"):
                content_type = "image/png"
            elif filename.endswith(".json"):
                content_type = "application/json"
            elif filename.endswith(".csv"):
                content_type = "text/csv; charset=utf-8"
            elif filename.endswith(".md"):
                content_type = "text/markdown; charset=utf-8"
            self.serve_file(file_path, content_type)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/run":
            if SIM_STATE.is_running:
                self.send_json_response({"success": False, "message": "Zaten devam eden bir simülasyon var."}, status=409)
                return

            SIM_STATE.reset_for_run()
            worker = threading.Thread(target=execute_simulation_worker, args=(data,), daemon=True)
            worker.start()
            self.send_json_response({"success": True, "message": "Simülasyon arka planda başlatıldı."})

        elif path == "/api/open-folder":
            try:
                os.makedirs(SIM_STATE.output_dir, exist_ok=True)
                if sys.platform.startswith("win"):
                    os.startfile(SIM_STATE.output_dir)
                else:
                    subprocess.Popen(["xdg-open", SIM_STATE.output_dir])
                self.send_json_response({"success": True})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)

        elif path == "/api/birthday":
            try:
                n = int(data.get("n", 38))
                m = int(data.get("m", 1000))
                prob = CollisionMath.birthday_probability(n_samples=n, num_bins=m)
                expected = CollisionMath.expected_collisions(n_samples=n, num_bins=m)
                self.send_json_response({
                    "n": n,
                    "m": m,
                    "probability": prob,
                    "probability_pct": prob * 100.0,
                    "expected_collisions": expected
                })
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)
        else:
            self.send_response(404)
            self.end_headers()

    def serve_file(self, file_path: str, content_type: str):
        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")
            return

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

    def send_json_response(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = 5055):
    """Starts the HTTP server."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DesktopRequestHandler)
    print(f"[Desktop Server] http://127.0.0.1:{port} adresinde dinleniyor...")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5055
    run_server(port)
