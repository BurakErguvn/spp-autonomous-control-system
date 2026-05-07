"""Senaryo tanımları — `iş_paketi.md` Hafta 13 ve `GEMINI.mdc` §7'ye uygun.

Her senaryo:
    target_class : Beklenen YOLO sınıf ID'si (0=hotspot, 1=mikro_catlak, 2=tozlanma)
    panel_ids    : Sahada hangi panellerin "uçuşta taranacağı"

Senaryo None ise tüm paneller (panel_layout.json'daki 30 panel) sırayla taranır;
veri seti içinden rastgele bir görüntü beslenir.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """Tek senaryonun tanımı."""

    name: str
    target_class: int      # 0=hotspot, 1=mikro_catlak, 2=tozlanma
    panel_ids: list[int]   # bu senaryoda taranacak paneller
    description: str


# ── Standart senaryolar ──────────────────────────────────────────────────────

# Senaryo A — Tesisin %5'inde hafif kirlenme → "Bakımı ertele"
# 30 panelin yaklaşık %5'i = 2 panel
SCENARIO_A = Scenario(
    name="A",
    target_class=2,                     # tozlanma
    panel_ids=[5, 14],
    description="Hafif tozlanma — bakımı ertele",
)

# Senaryo B — 2 farklı uç noktada kritik hotspot → "Acil müdahale"
SCENARIO_B = Scenario(
    name="B",
    target_class=0,                     # hotspot
    panel_ids=[0, 29],
    description="Uç noktalarda kritik hotspot — acil müdahale",
)

# Senaryo C — Tesis genelinde dağınık mikro-çatlaklar → "Kapsamlı VRP rotası"
# Her 3. panel
SCENARIO_C = Scenario(
    name="C",
    target_class=1,                     # mikro_catlak
    panel_ids=[0, 3, 6, 9, 12, 15, 18, 21, 24, 27],
    description="Dağınık mikro çatlaklar — kapsamlı VRP rotası",
)

SCENARIOS: dict[str, Scenario] = {
    "A": SCENARIO_A,
    "B": SCENARIO_B,
    "C": SCENARIO_C,
}


def get(name: str | None) -> Scenario | None:
    """İsimden senaryo getirir; yoksa None döner (tam koşum modu)."""
    if name is None:
        return None
    return SCENARIOS.get(name.upper())
