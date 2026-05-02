# YZ Modülü (`ai_inference`) — Bilgisayar Mühendisliği

Bu modül, YOLO26 modeli kullanarak GES termal görüntülerindeki arızaları tespit eder (İP 4).

## Özellikler
- Sadece inference (çıkarım) yapar.
- Çıktılarını projenin ortak JSON arayüzüne (şemasına) göre doğrular.
- `hotspot`, `mikro_catlak`, `tozlanma` sınıflarını tespit eder.
- Metrik değerlendirme (`metrics.py`) yeteneklerine sahiptir.

## Kullanım

Bu modül `main.py` tarafından çağrılır. Doğrudan eğitim yapmak için ana dizindeki `scripts/train_yolo26.py` scriptini kullanın.

## Kurallar
- Modül kendi hata yönetimini yapar (pipeline çökmez).
- Geçersiz JSON çıktıları dosyaya yazılmaz, sadece loglanır.
