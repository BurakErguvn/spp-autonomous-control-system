# Endüstri Mühendisliği (IE) Araştırma ve Gerçek Değer Atama Görevleri

Bu doküman, sistemin optimizasyon (MILP ve VRP) modülünde şu an varsayılan (dummy) olarak kullanılan parametrelerin listesini içermektedir. Endüstri Mühendisliği ekibinin literatür taraması veya sektör araştırması yaparak bu değişkenlerin **gerçek dünyadaki karşılıklarını (referanslarıyla birlikte)** bulması ve modüle entegre etmesi gerekmektedir.

## 1. Fırsat Maliyeti (Üretim Kaybı) Parametreleri
Sistemin "bu arızayı tamir etmezsek ne kadar para kaybederiz?" sorusunu cevaplayabilmesi için aşağıdaki verilerin endüstri standardı karşılıkları bulunmalıdır:

* **Enerji Birim Fiyatı (PTF / YEKDEM):** 1 kWh elektriğin anlık veya ortalama şebekeye satış fiyatı nedir? (Örn: EPİAŞ verilerine göre güncel piyasa takas fiyatı veya YEKDEM teşvik fiyatı).
* **Hotspot (Isınma Noktası) Kaybı:** Bir panelde hotspot oluştuğunda panelin günlük üretim verimi ortalama % kaç veya kaç kWh düşer?
* **Mikro Çatlak Kaybı:** Mikro çatlakların panel gücüne (watt) etkisi nedir? Zamanla büyüme veya paneli tamamen bozma hızı/olasılığı nedir?
* **Tozlanma (Soiling) Kaybı:** Tozlanma/kirlenme durumunda bir panelin verimi günlük/aylık bazda ne kadar düşer?

## 2. Bakım Maliyeti Parametreleri
Optimizasyon algoritmasının "bu arızayı tamir etmenin masrafı nedir?" sorusuna gerçekçi cevap verebilmesi için:

* **İşçilik Maliyeti:** GES bakım teknisyenlerinin saatlik veya günlük ücreti ne kadardır?
* **Müdahale (Tamir) Süreleri:** 
  * Bir hotspot arızasının onarımı (veya panel değişimi) ortalama kaç dakika/saat sürer?
  * Kirlenme durumunda panel temizliği ne kadar sürer?
* **Malzeme Değişim Maliyetleri:** Hotspot olan bir panel her zaman tamamen değiştirilmeli midir, yoksa bypass diyotu mu değiştirilir? Komple panel değişim maliyeti (parça fiyatı) ne kadardır?
* **Ulaşım ve Lojistik:** Bakım aracının sahada harcadığı yakıt maliyeti (kilometre başına) ne kadardır?

## 3. Operasyonel Kısıtlar (MILP ve VRP Kısıtları)
Karar destek sisteminin matematiksel (MILP) kısıtlarına yazılacak gerçek dünya sınırları:

* **Günlük Mesai Sınırı:** Bakım ekibi sahada günde maksimum kaç saat çalışabilir? (Algoritmada günlük görev sınırını belirleyecek).
* **Ekip Sayısı:** Ortalama büyüklükteki (örneğin 10 MW) bir santralde kaç adet bakım ekibi / aracı bulunur? (Eğer birden fazla araç varsa Çoklu Araç Rotalama - CVRP algoritmasına geçilmelidir).
* **İHA Uçuş ve Denetim Sınırı:** İHA'nın pili kaç dakika dayanır ve bu sürede kaç panelin termal fotoğrafını çekebilir? (Bu veri EE ekibi ile ortak belirlenecektir).

## 4. Senaryo Analizi İçin Kıyaslama Metrikleri (Hafta 13)
* **Geleneksel Bakım Sıklığı:** Mevcut santrallerde İHA ve otonom sistemler KULLANILMADAN önce paneller yılda veya ayda kaç kez insan gücüyle (el termaliyle) kontrol edilmektedir? Bunun santrale yıllık maliyeti ne kadardır? (Projemizin yaratacağı maliyet tasarrufunu (ROI) kanıtlamak için bu bilgi şarttır).
