"""
visualization.py - Publication-Quality Matplotlib Visualizations
================================================================
Generates 8 diagnostic charts:
1. First 3 digits observed vs expected distribution (000-999).
2. Per-position digit frequency (6 subplots for positions 0-5).
3. Time series trajectory with 40-minute collision highlights.
4. Collision rate as a function of time lag (0-120 minutes).
5. Autocorrelation correlogram with 95% Bartlett confidence bands.
6. Comparative collision rates across all generators with error bars.
7. Chi-Square p-values & runtimes across sample sizes.
8. Shannon entropy comparison vs theoretical maximum.
"""

import os
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt


class Visualizer:
    """Creates and exports diagnostic charts as high-resolution PNGs."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        # Professional aesthetic styling
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        plt.rcParams.update({
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
            "axes.edgecolor": "#cccccc",
            "axes.linewidth": 0.8,
            "grid.color": "#ebebeb",
            "grid.linestyle": "--"
        })

    def plot_first3_distribution(
        self,
        counts: np.ndarray,
        expected: float,
        generator_name: str,
        filename: str = "fig1_first3_distribution.png"
    ) -> str:
        """Plot 1: Observed vs expected frequency for first 3 digits (000..999)."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(12, 5), dpi=300)

        x = np.arange(len(counts))
        ax.bar(x, counts, width=1.0, color="#2563eb", alpha=0.6, label="Gözlenen Frekans (Observed)")
        ax.axhline(expected, color="#dc2626", linestyle="--", linewidth=1.8,
                   label=f"Teorik Beklenti E={expected:.1f} (Expected)")

        # Theoretical 95% Poisson error band around expected: E +/- 1.96*sqrt(E)
        std_err = np.sqrt(expected)
        ax.fill_between([0, len(counts)], expected - 1.96 * std_err, expected + 1.96 * std_err,
                        color="#dc2626", alpha=0.15, label="Teorik %95 Güven Bandı")

        ax.set_title(f"İlk 3 Hane Frekans Dağılımı (000-999) — {generator_name}", fontsize=13, fontweight="bold")
        ax.set_xlabel("İlk 3 Hane Kategorisi (Prefix: 000 - 999)", fontsize=11)
        ax.set_ylabel("Gözlenen Sayı (Count)", fontsize=11)
        ax.set_xlim(0, 1000)
        ax.legend(loc="upper right", frameon=True)
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_digit_positions(
        self,
        digit_matrix: np.ndarray,
        generator_name: str,
        filename: str = "fig2_digit_positions.png"
    ) -> str:
        """Plot 2: 6-panel subplot of digit frequencies (0-9) at each position."""
        filepath = os.path.join(self.output_dir, filename)
        fig, axes = plt.subplots(2, 3, figsize=(14, 8), dpi=300)
        axes = axes.flatten()

        digits = np.arange(10)
        for pos in range(6):
            ax = axes[pos]
            counts = digit_matrix[pos, :]
            expected = np.sum(counts) / 10.0

            ax.bar(digits, counts, color="#0d9488", alpha=0.75, edgecolor="#0f766e")
            ax.axhline(expected, color="#e11d48", linestyle="--", linewidth=1.5, label="E (Uniform)")

            ax.set_title(f"Pozisyon {pos + 1} (Hane {pos})", fontsize=11, fontweight="bold")
            ax.set_xticks(digits)
            ax.set_xlabel("Rakam (0-9)")
            ax.set_ylabel("Frekans")
            if pos == 0:
                ax.legend(loc="upper right")

        fig.suptitle(f"Hane Pozisyonlarına Göre Rakam Dağılımları — {generator_name}", fontsize=14, fontweight="bold")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_time_series(
        self,
        timestamps: np.ndarray,
        int_array: np.ndarray,
        generator_name: str,
        filename: str = "fig3_time_series.png"
    ) -> str:
        """Plot 3: Time series of code values with simulated intervals."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(12, 5), dpi=300)

        # Plot first 200 points to keep visibility sharp
        sub_n = min(250, len(int_array))
        t_sub = (timestamps[:sub_n] - timestamps[0]) / 60.0  # relative minutes
        val_sub = int_array[:sub_n]

        ax.plot(t_sub, val_sub, marker="o", markersize=3, linestyle="-", color="#6366f1",
                alpha=0.7, label="6 Haneli Kod Değeri")
        ax.set_title(f"Zaman Ekseninde Kod Değişimi — {generator_name}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Göreli Zaman (Dakika)", fontsize=11)
        ax.set_ylabel("Kod Değeri (000000 - 999999)", fontsize=11)
        ax.set_ylim(-10000, 1_010_000)
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_collision_lag_distribution(
        self,
        interval_sweep_results: List[Dict[str, Any]],
        generator_name: str,
        filename: str = "fig4_collision_lag_distribution.png"
    ) -> str:
        """Plot 4: Collision rate vs time lag in minutes."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)

        lags = [r["interval_minutes"] for r in interval_sweep_results]
        rates = [r["prefix_collision_rate"] * 100.0 for r in interval_sweep_results]  # in %
        ci_low = [r["wilson_ci_95"][0] * 100.0 for r in interval_sweep_results]
        ci_high = [r["wilson_ci_95"][1] * 100.0 for r in interval_sweep_results]

        y_err = [
            np.maximum(0.0, np.array(rates) - np.array(ci_low)),
            np.maximum(0.0, np.array(ci_high) - np.array(rates))
        ]

        ax.errorbar(lags, rates, yerr=y_err, fmt="-o", color="#8b5cf6", ecolor="#c4b5fd",
                    elinewidth=2, capsize=4, label="Gözlenen İlk 3 Hane Çakışma Oranı (%)")
        ax.axhline(0.1, color="#ef4444", linestyle="--", linewidth=1.8, label="Teorik Beklenti (%0.1)")

        ax.set_title(f"Zaman Gecikmesine (Lag) Göre Çakışma Oranı — {generator_name}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Zaman Farkı (Dakika)", fontsize=11)
        ax.set_ylabel("Çakışma Oranı (%)", fontsize=11)
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_autocorrelation(
        self,
        autocorr_data: Dict[str, Any],
        generator_name: str,
        filename: str = "fig5_autocorrelation.png"
    ) -> str:
        """Plot 5: Correlogram with 95% Bartlett white-noise bounds."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(11, 5), dpi=300)

        lags = autocorr_data["lags"]
        rhos = autocorr_data["autocorrelations"]
        bound = autocorr_data["bartlett_bound_95"]

        ax.stem(lags, rhos, linefmt="#3b82f6", markerfmt="o", basefmt="k-")
        ax.axhline(bound, color="#ef4444", linestyle="--", label=f"95% Bartlett Sınırı (+/- {bound:.4f})")
        ax.axhline(-bound, color="#ef4444", linestyle="--")
        ax.axhline(0, color="gray", linewidth=0.8)

        ax.set_title(f"Gecikmeli Otokorelasyon (Correlogram) — {generator_name}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Gecikme (Lag)", fontsize=11)
        ax.set_ylabel("Otokorelasyon Katsayısı (r_k)", fontsize=11)
        ax.set_ylim(-max(0.1, max(abs(r) for r in rhos) * 1.2), max(0.1, max(abs(r) for r in rhos) * 1.2))
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_generator_comparison(
        self,
        comparison_results: List[Dict[str, Any]],
        filename: str = "fig6_generator_comparison.png"
    ) -> str:
        """Plot 6: Bar chart comparing 40-minute collision rates across all generators."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(13, 6), dpi=300)

        names = [r["generator_name"].replace("Defect_", "Defect:\n") for r in comparison_results]
        rates = [r["prefix_collision_rate"] * 100.0 for r in comparison_results]
        ci_low = [r["prefix_test"]["wilson_ci_95"][0] * 100.0 for r in comparison_results]
        ci_high = [r["prefix_test"]["wilson_ci_95"][1] * 100.0 for r in comparison_results]

        y_err = [
            np.maximum(0.0, np.array(rates) - np.array(ci_low)),
            np.maximum(0.0, np.array(ci_high) - np.array(rates))
        ]

        colors = ["#10b981" if abs(r - 0.1) < 0.05 else "#f43f5e" for r in rates]

        x_pos = np.arange(len(names))
        bars = ax.bar(x_pos, rates, yerr=y_err, capsize=4, color=colors, alpha=0.85, edgecolor="#333333")
        ax.axhline(0.1, color="#2563eb", linestyle="--", linewidth=2.0, label="Teorik Beklenti (%0.1 = 1/1000)")

        ax.set_xticks(x_pos)
        ax.set_xticklabels(names, rotation=35, ha="right", fontsize=9)
        ax.set_title("40 Dakika Aralıklı Kod Çiftlerinde İlk 3 Hane Çakışma Oranları Karşılaştırması",
                     fontsize=13, fontweight="bold")
        ax.set_ylabel("Gözlenen Çakışma Oranı (%)", fontsize=11)
        ax.legend(loc="upper left")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_sample_size_chi2(
        self,
        scaling_results: List[Dict[str, Any]],
        generator_name: str,
        filename: str = "fig7_sample_size_chi2.png"
    ) -> str:
        """Plot 7: Chi-Square p-value and execution runtime vs sample size."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax1 = plt.subplots(figsize=(10, 5), dpi=300)

        sizes = [str(r["sample_size"]) for r in scaling_results]
        p_vals = [r["chi2_prefix_p_value"] for r in scaling_results]
        runtimes = [r["total_time_sec"] for r in scaling_results]

        color = "#2563eb"
        ax1.set_xlabel("Örneklem Büyüklüğü (Sample Size)", fontsize=11)
        ax1.set_ylabel("Chi-Square p-değeri", color=color, fontsize=11)
        ax1.plot(sizes, p_vals, marker="s", color=color, linewidth=2, label="Chi-Square p-değeri")
        ax1.axhline(0.05, color="#ef4444", linestyle=":", label="Anlamlılık Eşiği (α = 0.05)")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.set_ylim(-0.05, 1.05)

        ax2 = ax1.twinx()
        color = "#f59e0b"
        ax2.set_ylabel("Toplam Çalışma Süresi (Saniye)", color=color, fontsize=11)
        ax2.plot(sizes, runtimes, marker="^", color=color, linewidth=2, linestyle="--", label="Çalışma Süresi (s)")
        ax2.tick_params(axis="y", labelcolor=color)

        fig.suptitle(f"Örneklem Büyüklüğüne Göre Chi-Square & Performans Analizi — {generator_name}",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath

    def plot_entropy_comparison(
        self,
        entropy_data: List[Dict[str, Any]],
        filename: str = "fig8_entropy_comparison.png"
    ) -> str:
        """Plot 8: Shannon entropy vs theoretical maximum across generators."""
        filepath = os.path.join(self.output_dir, filename)
        fig, ax = plt.subplots(figsize=(12, 5), dpi=300)

        names = [d["name"] for d in entropy_data]
        obs_entropies = [d["observed_entropy"] for d in entropy_data]
        max_entropy = entropy_data[0]["max_entropy"] if entropy_data else 9.965784

        x = np.arange(len(names))
        ax.bar(x, obs_entropies, color="#0284c7", alpha=0.8, label="Gözlenen Entropi (Bits)")
        ax.axhline(max_entropy, color="#dc2626", linestyle="--", linewidth=1.8,
                   label=f"Maksimum Teorik Entropi ({max_entropy:.3f} Bits)")

        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=35, ha="right", fontsize=9)
        ax.set_title("Üreteçlere Göre İlk 3 Hane Shannon Entropisi Karşılaştırması", fontsize=13, fontweight="bold")
        ax.set_ylabel("Entropi (Bits)", fontsize=11)
        ax.set_ylim(0, max_entropy * 1.15)
        ax.legend(loc="lower right")
        fig.tight_layout()
        fig.savefig(filepath)
        plt.close(fig)
        return filepath
