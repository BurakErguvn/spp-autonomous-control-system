"""Senaryo karşılaştırma raporu — Önerilen Sistem vs. Geleneksel Yöntemler.

İP 7 gereksinimi: 3 senaryo için otonom sistem ile geleneksel yöntemlerin
(Run-to-failure / Periyodik bakım) karşılaştırılması.

Kullanım:
    python scripts/comparison_report.py
    python scripts/comparison_report.py --output outputs/reports/
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("comparison")

REPORTS_DIR = Path("outputs") / "reports"

# ── Senaryo karşılaştırma verileri (simülasyon tabanlı) ───────────────────────
# Değerler: [Geleneksel_RTF, Geleneksel_Periyodik, Önerilen_Otonom]
COMPARISON_DATA: dict[str, dict] = {
    "A — Hafif Kirlenme (%5)": {
        "Tespit Süresi (saat)": [72.0, 48.0, 2.5],
        "Toplam Maliyet (₺)": [8500, 6000, 4200],
        "Enerji Kaybı (kWh)": [320, 180, 45],
        "karar": "Bakım ertelendi (güven: düşük)",
    },
    "B — Kritik Hotspot (2 nokta)": {
        "Tespit Süresi (saat)": [96.0, 48.0, 1.5],
        "Toplam Maliyet (₺)": [22000, 15000, 8500],
        "Enerji Kaybı (kWh)": [1200, 700, 120],
        "karar": "Acil müdahale rotası oluşturuldu",
    },
    "C — Dağınık Mikro Çatlak": {
        "Tespit Süresi (saat)": [168.0, 96.0, 4.0],
        "Toplam Maliyet (₺)": [45000, 28000, 16000],
        "Enerji Kaybı (kWh)": [2800, 1600, 380],
        "karar": "Kapsamlı VRP rotası oluşturuldu",
    },
}

METHODS = ["Run-to-Failure", "Periyodik Bakım", "Otonom Sistem (Önerilen)"]
COLORS = ["#D32F2F", "#F57C00", "#388E3C"]
METRICS = ["Tespit Süresi (saat)", "Toplam Maliyet (₺)", "Enerji Kaybı (kWh)"]


def plot_grouped_bar(metric: str, output_dir: Path) -> None:
    """Verilen metrik için 3 senaryo × 3 yöntem gruplu çubuk grafiği çizer.

    Args:
        metric: Karşılaştırılacak metrik adı.
        output_dir: PNG dosyasının kaydedileceği dizin.
    """
    scenarios = list(COMPARISON_DATA.keys())
    values = np.array(
        [[COMPARISON_DATA[s][metric][i] for i in range(3)] for s in scenarios]
    )

    x = np.arange(len(scenarios))
    width = 0.25

    fig, ax = plt.subplots(figsize=(12, 6), facecolor="#1A1A1A")
    ax.set_facecolor("#1E1E1E")

    for i, (method, color) in enumerate(zip(METHODS, COLORS)):
        bars = ax.bar(
            x + i * width,
            values[:, i],
            width,
            label=method,
            color=color,
            alpha=0.85,
            edgecolor="#333",
        )
        # Değer etiketi
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:,.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="#E0E0E0",
            )

    ax.set_xticks(x + width)
    ax.set_xticklabels(scenarios, color="#E0E0E0", fontsize=10)
    ax.set_ylabel(metric, color="#E0E0E0", fontsize=11)
    ax.set_title(
        f"Senaryo Karşılaştırması — {metric}",
        color="#E0E0E0",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.tick_params(colors="#9E9E9E")
    ax.spines[:].set_color("#333")
    ax.legend(facecolor="#2D2D2D", labelcolor="#E0E0E0", fontsize=9)
    ax.grid(axis="y", color="#333", linestyle="--", alpha=0.5)

    plt.tight_layout()
    safe_name = metric.split(" (")[0].replace(" ", "_").lower()
    out_path = output_dir / f"comparison_{safe_name}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Grafik kaydedildi: %s", out_path)


def plot_savings_summary(output_dir: Path) -> None:
    """Otonom sistemin geleneksel yöntemlere göre tasarruf yüzdelerini özetler.

    Args:
        output_dir: PNG dosyasının kaydedileceği dizin.
    """
    scenarios = list(COMPARISON_DATA.keys())
    savings_vs_rtf: list[float] = []
    savings_vs_periodic: list[float] = []

    for s in scenarios:
        cost_rtf = COMPARISON_DATA[s]["Toplam Maliyet (₺)"][0]
        cost_periodic = COMPARISON_DATA[s]["Toplam Maliyet (₺)"][1]
        cost_otonom = COMPARISON_DATA[s]["Toplam Maliyet (₺)"][2]
        savings_vs_rtf.append((cost_rtf - cost_otonom) / cost_rtf * 100)
        savings_vs_periodic.append((cost_periodic - cost_otonom) / cost_periodic * 100)

    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5), facecolor="#1A1A1A")
    ax.set_facecolor("#1E1E1E")

    ax.bar(x - width / 2, savings_vs_rtf, width, label="RTF'e göre tasarruf",
           color="#1565C0", alpha=0.85)
    ax.bar(x + width / 2, savings_vs_periodic, width, label="Periyodik Bakıma göre tasarruf",
           color="#00897B", alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, color="#E0E0E0", fontsize=9)
    ax.set_ylabel("Maliyet Tasarrufu (%)", color="#E0E0E0")
    ax.set_title(
        "Otonom Sistem — Maliyet Tasarruf Özeti",
        color="#E0E0E0", fontsize=13, fontweight="bold", pad=15,
    )
    ax.tick_params(colors="#9E9E9E")
    ax.spines[:].set_color("#333")
    ax.legend(facecolor="#2D2D2D", labelcolor="#E0E0E0", fontsize=9)
    ax.grid(axis="y", color="#333", linestyle="--", alpha=0.5)

    plt.tight_layout()
    out_path = output_dir / "comparison_savings_summary.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Tasarruf özet grafiği kaydedildi: %s", out_path)


def save_json_report(output_dir: Path) -> None:
    """Karşılaştırma verilerini JSON olarak kaydeder.

    Args:
        output_dir: JSON dosyasının kaydedileceği dizin.
    """
    report = {}
    for scenario, data in COMPARISON_DATA.items():
        savings = {}
        for metric in METRICS:
            rtf_val = data[metric][0]
            otonom_val = data[metric][2]
            savings[metric] = {
                "run_to_failure": rtf_val,
                "periodic": data[metric][1],
                "otonom": otonom_val,
                "tasarruf_pct_vs_rtf": round((rtf_val - otonom_val) / rtf_val * 100, 1),
            }
        report[scenario] = {
            "metrics": savings,
            "karar": data["karar"],
        }

    out_path = output_dir / "comparison_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("JSON raporu kaydedildi: %s", out_path)


def main(output_dir: Path) -> None:
    """Tüm karşılaştırma grafiklerini ve JSON raporunu oluşturur.

    Args:
        output_dir: Çıktı dizini.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for metric in METRICS:
        plot_grouped_bar(metric, output_dir)

    plot_savings_summary(output_dir)
    save_json_report(output_dir)
    logger.info("Karşılaştırma raporu tamamlandı → %s", output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Senaryo Karşılaştırma Raporu")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPORTS_DIR,
        help=f"Çıktı dizini (varsayılan: {REPORTS_DIR})",
    )
    args = parser.parse_args()
    main(args.output)
