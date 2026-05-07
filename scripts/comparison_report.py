"""Senaryo karşılaştırma raporu — Önerilen Sistem vs. Geleneksel Yöntemler.

İP 7 gereksinimi: 3 senaryo için otonom sistem ile geleneksel yöntemlerin
(Run-to-failure / Periyodik bakım) karşılaştırılması.

Otonom sistem değerleri `outputs/scenarios/{A,B,C}/gorev_cizelgesi.json` ve
`ariza_verileri.json`'dan okunur. Geleneksel yöntemler IE araştırma raporu
(``dokumanlar/ie_arastirma_rapor.md``) parametrelerine göre formülle hesaplanır.

Kullanım:
    python scripts/run_scenarios.py        # önce 3 senaryoyu koş
    python scripts/comparison_report.py    # sonra raporu üret
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.optimization import CostCalculator, Parameters  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("comparison")

SCENARIOS_DIR = Path("outputs") / "scenarios"
REPORTS_DIR = Path("outputs") / "reports"

# ── Geleneksel yöntem varsayımları (IE rapor referanslı) ──────────────────────
# Tespit gecikmesi: arıza oluştuğundan müdahaleye kadar geçen süre
DETECTION_DELAY_DAYS: dict[str, int] = {
    "otonom": 1,    # İHA uçuşu + müdahale ertesi gün
    "rtf": 90,      # Run-to-Failure: el termali turu ortalama 3 ay sonra fark eder
    "periodic": 30, # Yılda 2 kez denetim → ortalama 30 gün gecikme
}

# Tepki süresi (saat) — tespitten müdahale tamamlanmasına kadar
RESPONSE_HOURS: dict[str, float] = {
    "rtf": 72.0,        # 3 gün — saha ekibinin tepki süresi + müdahale
    "periodic": 48.0,   # 2 gün — daha hızlı tepki, periyodik plan
}

# Geleneksel müdahalede malzeme oranı (panel değişimi olasılığı daha yüksek)
RTF_PANEL_RATIO = 0.70           # geç tespit → panel değişimi ihtiyacı %70
PERIODIC_PANEL_RATIO = 0.40      # orta gecikme → %40 panel değişimi

METHODS = ["Run-to-Failure", "Periyodik Bakım", "Otonom Sistem (Önerilen)"]
COLORS = ["#D32F2F", "#F57C00", "#388E3C"]
METRICS = ["Tespit Süresi (saat)", "Toplam Maliyet (₺)", "Enerji Kaybı (kWh)"]


# ─────────────────────────────────────────────────────────────────────────────
# Hesaplama
# ─────────────────────────────────────────────────────────────────────────────


def load_scenario_outputs(scenario: str) -> tuple[list[dict], dict]:
    """Senaryonun ariza_verileri ve gorev_cizelgesi içeriklerini yükler."""
    scen_dir = SCENARIOS_DIR / scenario
    fault_path = scen_dir / "ariza_verileri.json"
    sched_path = scen_dir / "gorev_cizelgesi.json"

    if not fault_path.exists() or not sched_path.exists():
        logger.warning("Senaryo %s için çıktı dosyaları eksik (%s)", scenario, scen_dir)
        return [], {}

    with open(fault_path, encoding="utf-8") as f:
        faults = json.load(f)
    with open(sched_path, encoding="utf-8") as f:
        schedule = json.load(f)
    return faults, schedule


def dedupe_faults(faults: list[dict]) -> dict[int, str]:
    """Panel başına en kritik hasar (solver mantığıyla aynı)."""
    priority = {"hotspot": 0, "mikro_catlak": 1, "tozlanma": 2}
    best: dict[int, str] = {}
    for f in faults:
        pid = int(f.get("panel_id", -1))
        h = f.get("hasar")
        if pid < 0 or h not in priority:
            continue
        if pid not in best or priority[h] < priority[best[pid]]:
            best[pid] = h
    return best


def traditional_cost(
    panel_hasar: dict[int, str], delay_days: int, panel_ratio: float
) -> float:
    """Geleneksel yöntem (RTF/Periyodik) toplam maliyeti.

    İşçilik + malzeme + fırsat maliyeti formülasyonu:
        Σ_i (labor_i + diode_or_panel_cost + opportunity_cost(delay_days))
    """
    total = 0.0
    diode_ratio = 1.0 - panel_ratio
    for hasar in panel_hasar.values():
        labor_tl = (
            CostCalculator.service_minutes(hasar) / 60.0
        ) * Parameters.TECH_TL_PER_HOUR
        if hasar == "tozlanma":
            material_tl = 0.0
        else:
            material_tl = (
                diode_ratio * Parameters.DIODE_COST_TL
                + panel_ratio * Parameters.PANEL_COST_TL
            )
        opp_tl = CostCalculator.opportunity_cost(hasar, days=delay_days)
        total += labor_tl + material_tl + opp_tl
    return total


def total_energy_loss_kwh(panel_hasar: dict[int, str], days: int) -> float:
    """Σ panel için belirtilen gün boyunca kaybedilen kWh."""
    return sum(CostCalculator.daily_loss_kwh(h) * days for h in panel_hasar.values())


def autonomous_response_hours(schedule: dict) -> float:
    """Otonom sistemin tepki süresi (saat).

    İHA uçuşu + AI inference + müdahale işçiliği toplamı.
    """
    service_min = schedule.get("total_service_time_min", 0)
    return round(service_min / 60.0 + 1.0, 1)  # 1 saat tespit-analiz baz


def build_comparison_row(scenario: str, faults: list[dict], schedule: dict) -> dict:
    """Tek senaryonun 3 yöntem × 3 metrik karşılaştırma satırını üretir."""
    panel_hasar = dedupe_faults(faults)
    panel_count = len(panel_hasar)

    # Otonom (gerçek değerler)
    autonomous_cost = float(schedule.get("total_cost_tl", 0.0))
    autonomous_kwh = total_energy_loss_kwh(panel_hasar, DETECTION_DELAY_DAYS["otonom"])
    autonomous_hours = autonomous_response_hours(schedule)

    # Run-to-Failure
    rtf_cost = traditional_cost(
        panel_hasar, DETECTION_DELAY_DAYS["rtf"], RTF_PANEL_RATIO
    )
    rtf_kwh = total_energy_loss_kwh(panel_hasar, DETECTION_DELAY_DAYS["rtf"])

    # Periyodik
    periodic_cost = traditional_cost(
        panel_hasar, DETECTION_DELAY_DAYS["periodic"], PERIODIC_PANEL_RATIO
    )
    periodic_kwh = total_energy_loss_kwh(
        panel_hasar, DETECTION_DELAY_DAYS["periodic"]
    )

    karar = (
        schedule.get("note")
        or f"{len(schedule.get('tasks', []))} görev, {schedule.get('team_count', 0)} ekip"
    )

    return {
        "Tespit Süresi (saat)": [RESPONSE_HOURS["rtf"], RESPONSE_HOURS["periodic"], autonomous_hours],
        "Toplam Maliyet (₺)": [round(rtf_cost, 0), round(periodic_cost, 0), round(autonomous_cost, 0)],
        "Enerji Kaybı (kWh)": [round(rtf_kwh, 1), round(periodic_kwh, 1), round(autonomous_kwh, 1)],
        "panel_count": panel_count,
        "karar": karar,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Görselleştirme (mevcut grafik fonksiyonları)
# ─────────────────────────────────────────────────────────────────────────────


def plot_grouped_bar(
    metric: str, comparison: dict[str, dict], output_dir: Path
) -> None:
    """Tek metrik için 3 senaryo × 3 yöntem gruplu çubuk grafiği."""
    scenarios = list(comparison.keys())
    values = np.array([[comparison[s][metric][i] for i in range(3)] for s in scenarios])

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


def plot_savings_summary(comparison: dict[str, dict], output_dir: Path) -> None:
    """Otonom sistemin maliyet tasarruf yüzdesi."""
    scenarios = list(comparison.keys())
    savings_vs_rtf: list[float] = []
    savings_vs_periodic: list[float] = []

    for s in scenarios:
        cost_rtf = comparison[s]["Toplam Maliyet (₺)"][0]
        cost_periodic = comparison[s]["Toplam Maliyet (₺)"][1]
        cost_otonom = comparison[s]["Toplam Maliyet (₺)"][2]
        savings_vs_rtf.append(
            (cost_rtf - cost_otonom) / cost_rtf * 100 if cost_rtf > 0 else 0
        )
        savings_vs_periodic.append(
            (cost_periodic - cost_otonom) / cost_periodic * 100 if cost_periodic > 0 else 0
        )

    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5), facecolor="#1A1A1A")
    ax.set_facecolor("#1E1E1E")

    ax.bar(
        x - width / 2,
        savings_vs_rtf,
        width,
        label="RTF'e göre tasarruf",
        color="#1565C0",
        alpha=0.85,
    )
    ax.bar(
        x + width / 2,
        savings_vs_periodic,
        width,
        label="Periyodik bakıma göre tasarruf",
        color="#00897B",
        alpha=0.85,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, color="#E0E0E0", fontsize=9)
    ax.set_ylabel("Maliyet Tasarrufu (%)", color="#E0E0E0")
    ax.set_title(
        "Otonom Sistem — Maliyet Tasarruf Özeti",
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
    out_path = output_dir / "comparison_savings_summary.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Tasarruf özet grafiği kaydedildi: %s", out_path)


def save_json_report(comparison: dict[str, dict], output_dir: Path) -> None:
    """Karşılaştırma verilerini JSON raporu olarak kaydeder."""
    report: dict = {}
    for scenario, data in comparison.items():
        savings: dict = {}
        for metric in METRICS:
            rtf_val = data[metric][0]
            otonom_val = data[metric][2]
            savings[metric] = {
                "run_to_failure": data[metric][0],
                "periodic": data[metric][1],
                "otonom": data[metric][2],
                "tasarruf_pct_vs_rtf": round(
                    (rtf_val - otonom_val) / rtf_val * 100, 1
                ) if rtf_val > 0 else 0.0,
            }
        report[scenario] = {
            "metrics": savings,
            "panel_count": data["panel_count"],
            "karar": data["karar"],
        }

    out_path = output_dir / "comparison_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("JSON raporu kaydedildi: %s", out_path)


# ─────────────────────────────────────────────────────────────────────────────


def main(output_dir: Path) -> None:
    """3 senaryo çıktısını okur, karşılaştırma raporunu üretir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    scenario_labels = {
        "A": "A — Hafif Tozlanma",
        "B": "B — Kritik Hotspot (2 nokta)",
        "C": "C — Dağınık Mikro Çatlak",
    }
    comparison: dict[str, dict] = {}
    for sid, label in scenario_labels.items():
        faults, schedule = load_scenario_outputs(sid)
        if not faults:
            logger.warning("Senaryo %s atlandı (girdi eksik).", sid)
            continue
        comparison[label] = build_comparison_row(sid, faults, schedule)

    if not comparison:
        logger.error(
            "Hiç senaryo verisi bulunamadı. Önce 'python scripts/run_scenarios.py' çalıştırın."
        )
        sys.exit(1)

    for metric in METRICS:
        plot_grouped_bar(metric, comparison, output_dir)
    plot_savings_summary(comparison, output_dir)
    save_json_report(comparison, output_dir)

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
