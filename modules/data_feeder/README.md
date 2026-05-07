# Veri Akış Modülü (EE Simülasyonu)

Sistem mimarisinin **1. katmanı**. Gerçek bir İHA uçuşu yapılmadığı için bu
modül; önceden toplanmış termal/RGB veri setini sanki anlık otopilot
beslemesi gibi sıralı şekilde sisteme verir.

## Kapsam

- Veri seti taranır, etiketler 3 sınıfa (`hotspot=0`, `mikro_catlak=1`,
  `tozlanma=2`) remap edilmiş şekilde sınıflandırılır.
- Senaryoya göre hedef sınıfı içeren görüntüler ilgili panel ID'lerine
  eşlenir.
- Her kareyle birlikte `panel_id`, `gps [lat, lon]`, `timestamp`,
  `flight_altitude` meta verisi yayınlanır (kural §2.1).
- **Kapsam dışı:** Modül, arıza tespit kararı vermez; sadece ham görüntü
  + meta veri çıkarır.

## API

```python
from modules.data_feeder import DataFeeder

feeder = DataFeeder(seed=42)
for frame, meta in feeder.iter_frames(scenario="B"):
    # frame: numpy BGR ndarray
    # meta : {"panel_id": 0, "gps": [38.42, 27.14], ...}
    process(frame, meta)
```

## Senaryolar

| ID | Hedef sınıf  | Paneller             | Beklenen sonuç          |
| -- | ------------ | -------------------- | ----------------------- |
| A  | tozlanma     | 5, 14                | Bakımı ertele           |
| B  | hotspot      | 0, 29                | Acil müdahale rotası    |
| C  | mikro_catlak | 0, 3, 6, …, 27 (10x) | Kapsamlı VRP rotası     |
| —  | rastgele     | 0–29 tamamı          | Tam koşum               |

`scenario=None` verildiğinde tüm 30 panel sırayla tarama listesine alınır.
