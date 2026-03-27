GÜNEŞ ENERJİSİ SANTRALLERİNDE (GES) OTONOM İHA'LAR İLE TERMAL DENETİM VE KESTİRİMCİ BAKIM OPTİMİZASYON SİSTEMİ
İŞ PAKETLERİ VE ZAMAN ÇİZELGESİ
Proje Ekibi Dağılımı: 3 Bilgisayar Müh. (CS), 2 Elektrik-Elektronik Müh. (EE), 3 Endüstri Müh. (IE)
Proje Niteliği: Kavramsal Tasarım, Algoritma Geliştirme ve Bilgisayar Destekli Simülasyon

1. İŞ PAKETLERİ (WBS - Work Breakdown Structure)
   İP 1: Literatür Taraması, Gereksinim Analizi ve Sistem Mimarisi Tasarımı (Tüm Ekip)
   Açıklama: Projenin kavramsal sınırlarının çizilmesi ve disiplinler arası veri akış mimarisinin (Blok diyagramlar) tasarlanması.

CS: GES termal görüntüleri kullanılarak eğitilecek Derin Öğrenme (CNN/YOLO) modelleri için açık kaynak veri setlerinin taranması. Sistem mimarisinin yazılım bileşenlerinin belirlenmesi.
CS Alt Görevleri:
Termal görüntülerde nesne tespiti (Object Detection) için YOLOv8, Faster R-CNN ve U-Net gibi güncel Derin Öğrenme mimarilerinin literatürde karşılaştırılması.
Yazılımın genel akış şemasının (UML diyagramları) ve modüler mimarisinin tasarlanması.

EE: Literatürdeki ticari endüstriyel İHA'ların (ör. DJI Matrice serisi) özelliklerinin incelenmesi. Termal kamera (ör. FLIR) ve sensör gereksinimlerinin teorik olarak belirlenmesi.
EE Alt Görevleri:
Sanal ortamda kullanılacak İHA'nın teorik uçuş dinamiklerinin araştırılması (kaldırma kuvveti, rüzgar direnci).
Endüstriyel termal kameraların (Örn: FLIR Vue Pro) çözünürlük, FOV (Görüş Alanı) ve piksel başına düşen sıcaklık hassasiyeti (radiometric data) değerlerinin belirlenmesi.

IE: GES arızalarının (hotspot, mikro-çatlak) yol açtığı güç kaybı hesaplama yöntemlerinin ve Kestirimci Bakım / Araç Rotalama Problemi (VRP) modellerinin literatürde incelenmesi.
IE Alt Görevleri:
GES panellerindeki kirlenme, mikro-çatlak ve hotspot (ısınma noktası) arızalarının enerji üretim verimliliğine (%) teorik etkisinin formülize edilmesi.
Literatürdeki Araç Rotalama Problemi (VRP) ve Gezgin Satıcı Problemi (TSP) algoritmalarının bakım planlamasındaki kullanımının incelenmesi.

İP 2: Donanım Tasarımı, Güç/Haberleşme Bütçesi ve Veri Seti Hazırlığı (EE + CS)
Açıklama: Sistemin fiziksel sınırlarının teorik olarak hesaplanması ve yapay zeka eğitim verilerinin hazırlanması.

EE: Seçilen teorik donanımların (İHA + Kamera + Gömülü Sistem) "Güç Bütçesi" (Power Budget) hesaplamalarının yapılması (Maksimum uçuş süresi ne kadar olacak?). Toplanan verilerin merkeze aktarımı için gerekli bant genişliği ve haberleşme protokollerinin (LoRa/5G) kısıt analizleri.
EE Alt Görevleri:
Güç Bütçesi (Power Budget): İHA'nın taşıyacağı batarya kapasitesi (mAh), motorların çektiği akım ve faydalı yük (kamera) ağırlığına göre "Maksimum Teorik Uçuş Süresi" denklemlerinin kurulması.
Haberleşme Bütçesi (Link Budget): Yüksek çözünürlüklü görüntülerin yer istasyonuna aktarımı için gereken bant genişliği (Bandwidth) hesaplamaları.

CS: Kaggle veya GitHub üzerinden bulunan açık kaynak termal GES veri setlerinin (hotspot, tozlanma vb.) etiketlenmesi, veri artırma (data augmentation) işlemlerinin yapılması ve yapay zeka eğitimi için yerel Python/Linux ortamlarının hazırlanması.
CS Alt Görevleri:
Kaggle veya üniversite veritabanlarından açık kaynaklı GES termal drone görüntülerinin toplanması.
Veri setinin Roboflow veya CVAT araçları ile "Sağlam", "Hotspot", "Tozlanma" olarak etiketlenmesi.
Model eğitimi için Linux tabanlı yerel geliştirme ortamının (Python, CUDA, PyTorch/TensorFlow) kurulması.

IE Alt Görevleri:
Sistemin optimizasyon modelinde kullanılacak sabit ve değişken maliyet parametrelerinin (Teknisyen saat ücreti, 1 kWh elektrik piyasa fiyatı, ulaşım yakıt maliyeti) tanımlanması.

İP 3: ARA RAPOR Hazırlığı ve Tasarımın Kesinleşmesi (Tüm Ekip)
Açıklama: İlk 4 haftalık kavramsal tasarım sürecinin raporlaştırılması.
Görevler: Sistem mimarisi şemalarının çizilmesi, matematiksel optimizasyon formüllerinin (IE) ve donanım seçim gerekçelerinin (EE) akademik yazım kurallarına uygun olarak rapora aktarılması.

İP 4: Yapay Zeka (Görüntü İşleme) Modelinin Geliştirilmesi (CS)
Açıklama: Teorik dronedan geldiği varsayılan görüntülerin işlenmesi.
Görevler: Etiketli veriler kullanılarak termal görüntülerden otonom arıza tespiti yapan modelin eğitilmesi. Karmaşıklık matrisi (Confusion Matrix) üzerinden doğruluk (Accuracy), kesinlik (Precision) ve duyarlılık (Recall) metriklerinin çıkarılması.
CS Odaklı Görevler:
Etiketlenmiş veriler üzerinde Python kullanılarak seçilen CNN/YOLO modelinin eğitilmesi.
Aşırı öğrenmeyi (Overfitting) engellemek için veri artırma (Data Augmentation - döndürme, bulanıklaştırma, kontrast ayarı) tekniklerinin uygulanması.
Modelin performans metriklerinin (mAP - Mean Average Precision, F1-Score, Confusion Matrix) çıkarılıp raporlanması.
Model çıktısının koordinat ve arıza tipi olarak .json veya .csv formatında dışa aktarılacak şekilde yapılandırılması.

İP 5: Bakım Optimizasyonu ve Karar Destek Algoritmalarının Kurulması (IE)
Açıklama: Üretim kaybı ve bakım maliyetlerini minimize edecek kararların matematiksel olarak modellenmesi.
Görevler: Yapay zekanın tespit ettiği varsayılan arızalar için "Fırsat Maliyeti" (Üretilemeyen enerjinin maddi karşılığı) ile "Bakım Maliyeti"nin (Personel, ekipman, araç) karşılaştırıldığı Karma Tamsayılı Doğrusal Programlama (MILP) modelinin kurulması. Bakım ekiplerinin gün bazlı rotalarının çıkarılması.
IE Odaklı Görevler:
Karma Tamsayılı Doğrusal Programlama (MILP) modelinin matematiksel olarak kurulması.
Amaç Fonksiyonu: Min(Bakım Maliyeti + Üretilemeyen Enerjinin Fırsat Maliyeti).
Kısıtlar (Constraints): Günlük mesai saatleri sınırı, İHA'nın maksimum uçuş/denetim süresi, arıza büyüme hızı.
Optimizasyon modelinin Python üzerinde PuLP, Gurobi veya SciPy kütüphaneleri kullanılarak koda dökülmesi.

İP 6: Sistem Entegrasyonu ve Senaryo Bazlı Simülasyon (CS + IE)
Açıklama: Yazılım ve Endüstri mühendisliği algoritmalarının birleştirilerek test edilmesi.
Görevler: CS ekibinin geliştirdiği YZ algoritmasının çıktılarının (tespit edilen arızalar), IE ekibinin Python veya optimizasyon çözücülerinde (Gurobi/CPLEX) hazırladığı algoritmaya otomatik girdi olarak beslendiği bir "Simülasyon Boru Hattı" (Pipeline) oluşturulması.
Ortak Görevler (CS + IE):
Yapay zekanın ürettiği arıza dosyalarının, optimizasyon algoritması tarafından otomatik olarak okunup işlendiği veri akışının (pipeline) sağlanması.
Arayüz Geliştirme: Modern bir Python GUI kütüphanesi (PyQt6 veya CustomTkinter) kullanılarak bir masaüstü uygulaması geliştirilmesi.
Bu arayüzde; santralin sanal bir haritasının bulunması, YZ'nin bulduğu arızaların haritada kırmızı işaretlenmesi ve optimizasyon algoritmasının "Bugün 3 numaralı invertör bölgesine gidilmeli" sonucunu ekrana yazdırması.

İP 7: Senaryo Analizleri ve Fayda Doğrulaması (Tüm Ekip)
Açıklama: Kurulan teorik sistemin geleneksel yöntemlere göre üstünlüğünün kanıtlanması.
Görevler: 3 farklı senaryo oluşturulması (Örn: Hafif hasarlı santral, çoklu kritik hasarlı santral, dağınık yerleşimli santral). Bu senaryolarda "İnsan ile manuel kontrol" vs "Önerilen Otonom Sistem" karşılaştırması yapılarak elde edilen teorik zaman ve maliyet kazançlarının istatistiksel olarak belgelenmesi.
Ortak Görevler:
Tasarlanan yazılım üzerinde 3 farklı "Sanal GES Hasar Senaryosu" yaratılması:
Senaryo A: Tesisin %5'inde hafif kirlenme (Bakımı erteleme kararı beklenir).
Senaryo B: 2 farklı uç noktada kritik hotspot (Acil müdahale rotası beklenir).
Senaryo C: Tesis genelinde dağınık mikro-çatlaklar (Kapsamlı VRP rotası beklenir).
Geleneksel "Arıza olunca git (Run-to-failure)" veya "Periyodik bakım" yaklaşımları ile geliştirdiğiniz "Kestirimci Bakım" algoritmasının sonuçlarının Excel/Python grafiklerinde karşılaştırılması. (Örn: "Algoritmamız aylık %14 maliyet tasarrufu sağlamıştır").

İP 8: FİNAL RAPORU ve Proje Sunumu Hazırlığı (Tüm Ekip)
Açıklama: Projenin akademik olarak belgelenmesi ve teslimi.
Görevler: Simülasyon sonuçlarının, senaryo analizlerinin ve disiplinler arası tasarım mimarisinin final raporuna dönüştürülmesi. Jüri sunumunun hazırlanması.
