"""EE Simülasyon — Veri Akış Modülü.

Dışa açılan bileşenler:
    DataFeeder : Senaryo bazlı görüntü besleyicisi
    Scenario   : Senaryo veri sınıfı
    SCENARIOS  : Standart senaryo katalogu (A/B/C)
"""

from .feeder import DataFeeder
from .scenarios import SCENARIOS, Scenario, get as get_scenario

__all__ = ["DataFeeder", "Scenario", "SCENARIOS", "get_scenario"]
