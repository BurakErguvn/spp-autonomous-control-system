# Güneş Enerjisi Santralleri (GES) Otonom Denetim Sistemi

Bu proje, Güneş Enerjisi Santrallerinde (GES) meydana gelen _hotspot, mikro çatlak ve tozlanma_ gibi anormallikleri İHA verileri ile otonom olarak tespit etmek ve Endüstri Mühendisliği tabanlı optimizasyon (MILP/VRP) algoritmalarıyla en uygun kestirimci bakım planını (ve rotasını) çıkarmak üzere geliştirilmiştir.

## 📚 Proje Dokümantasyonu

Projenin tüm akademik, yapısal ve iş süreçleri ile ilgili detaylı dokümantasyonlar derlenerek `dokumanlar/` klasörü altına toplanmıştır. İlgili bağlantılara aşağıdan tıklayarak ulaşabilirsiniz:

1. [**Proje İçeriği ve Temel Kapsam**](./dokumanlar/proje_içeriği.md)
   Projenin genel hedeflerini, kullanılacak yöntemleri ve çözmek istediği problemleri barındırır.
2. [**Sistem Mimarisi**](./dokumanlar/sistem_mimarisi.md)
   4 Katmanlı (Veri Akışı, YZ, Optimizasyon, GUI) sistemin nasıl çalıştığını ve modüllerin birbirleriyle olan JSON tabanlı iletişimini açıklar.
3. [**İş Paketi ve Takvim**](./dokumanlar/iş_paketi.md)
   Haftalık iş dağılımını, disiplinler arası görevleri ve güncel ilerleme durumunu takip edebileceğiniz proje yönetim dosyasıdır.
4. [**Endüstri Mühendisliği Araştırma Parametreleri**](./dokumanlar/IE_Arastirma_Parametreleri.md)
   MILP ve VRP tabanlı bakım optimizasyonunda kullanılan maliyet, zaman ve kapasite kısıtlarının (panel temizleme süresi, teknisyen ücreti vb.) listesini barındırır.
5. [**Endüstri Mühendisliği Araştırma Cevapları**](./dokumanlar/ie_arastirma_rapor.md)
   IE ekibinin literatür taraması sonucu yukarıdaki parametrelerin gerçek dünya karşılıklarını (PTF, işçilik ücreti, bakım süreleri vb.) içerir.
6. [**Parametre Tablosu (CSV)**](./dokumanlar/Parametre%20Tablosu.csv)
   Optimizasyon modülünün doğrudan kullandığı sayısal sabitlerin tek tablolu özeti.
7. [**Donanım — DJI Matrice 350 RTK**](./dokumanlar/DJI%20Matrice%20350%20RTK/dji_matrice_350.md)
   Ticari endüstriyel İHA platformu, uçuş dinamikleri ve termal kamera (Zenmuse H20T) gereksinimleri.
8. [**Donanım Mimarisi & Güç Bütçesi**](./dokumanlar/DJI%20Matrice%20350%20RTK/donanım_mimarisi.md)
   İHA aerodinamiği, gömülü sistem (STM32), güç dağıtımı ve LoRa haberleşmesi.
9. [**Eğitim ve Optimizasyon Raporu**](./dokumanlar/eğitim_rapor_makalesi.md)
   Yapay Zeka (YOLO26) modelinin eğitim sürecini, donanımsal kısıtları ve nesne tespitinde çıkarılan performans metriklerini (mAP) akademik bir dille özetleyen sonuç raporudur.
10. [**Final Rapor**](./dokumanlar/final_rapor.md)
    Sistem geneli bütünleşik teslim raporu (Hafta 14-15) — donanım, YZ, IE ve senaryo sonuçlarının birleştirildiği teknik dokümantasyon.

## Hızlı Başlangıç

```bash
pip install -r requirements.txt

# Tek senaryo (GUI ile)
python main.py --scenario B

# Tüm senaryoları sırayla koş + karşılaştırma raporu üret
python scripts/run_scenarios.py
python scripts/comparison_report.py

# YOLO ortamı kurulu değilse: sentetik fault verisiyle yalnızca IE modülü
python scripts/run_scenarios.py --no-inference
```

---

_Bu çalışma; Bilgisayar Mühendisliği, Endüstri Mühendisliği ve Elektrik-Elektronik Mühendisliği öğrencilerinin disiplinlerarası ortak projesi olarak geliştirilmiştir._
