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

## Senaryolar ve Tasarım Amaçları

Sistemdeki test senaryoları, Yapay Zeka ve Optimizasyon (MILP/VRP) modüllerinin kısıtlarını ve mantıksal karar mekanizmalarını doğrulamak için özel olarak tasarlanmıştır.

| ID | Hedef Sınıf | Taranan Paneller | Beklenen Sonuç | Tasarım Amacı ve Matematiksel/Operasyonel Mantık |
| :--- | :--- | :--- | :--- | :--- |
| **A** | Tozlanma | `5, 14` | Bakımı ertele | **Akıllı Erteleme Kontrolü:** Tesisin çok küçük bir kısmında (%5) hafif tozlanma simüle edilir. Panellerin temizleme işçilik ve yakıt maliyeti, getirecekleri enerji üretim kazancından yüksek olduğu için MILP modelinin bu bakımı "ekonomik dışı" bularak ertelemesi (0 görev) beklenir. |
| **B** | Hotspot | `0, 29` | Acil müdahale rotası | **Güvenlik (Must-Fix) ve Coğrafi Uç Noktalar:** Yangın riski oluşturan hotspot arızaları ekonomik fizibiliteden bağımsız olarak zorunlu tamir edilmelidir. Ayrıca 0 ve 29. paneller santralin coğrafi olarak birbirine en zıt köşeleridir. VRP rotalama algoritmasının bu uzak iki zıt noktaya minimum seyahat maliyetiyle nasıl ekip yönlendireceğini doğrular. |
| **C** | Mikro Çatlak | `0, 3, 6, …, 27` (10x) | Kapsamlı VRP rotası | **Kapasite ve Yük Dağılımı (Load Balancing):** Mikro çatlakların tamir süresi uzundur (panel başına 60 dk). Dağınık 10 panelin tamiri, ekiplerin günlük mesai kapasitelerini (3 ekip x 8 saat = 24 saat) zorlar. VRP çözücünün iş yükünü 3 ayrı ekibe en kısa seyahat mesafesiyle ve dengeli şekilde nasıl paylaştıracağını (subtour eliminasyonunu) doğrular. |
| **—** | Rastgele | `0–29` (Tümü) | Tam Koşum | **Genel Sistem Testi:** İHA'nın tüm santrali tarayarak hem sağlıklı hem arızalı panelleri analiz ettiği tam simülasyon modudur. |

`scenario=None` (veya belirtilmediğinde) tüm 30 panel sırayla tarama listesine alınır ve veri setinden rastgele görüntüler beslenir.
