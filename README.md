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
5. [**Eğitim ve Optimizasyon Raporu**](./dokumanlar/eğitim_rapor_makalesi.md)
   Yapay Zeka (YOLO26) modelinin eğitim sürecini, donanımsal kısıtları ve nesne tespitinde çıkarılan performans metriklerini (mAP) akademik bir dille özetleyen sonuç raporudur.

---

_Bu çalışma; Bilgisayar Mühendisliği, Endüstri Mühendisliği ve Elektrik-Elektronik Mühendisliği öğrencilerinin disiplinlerarası ortak projesi olarak geliştirilmiştir._
