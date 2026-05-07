# DJI Matrice 350 RTK

## Ticari Endüstriyel İHA İncelemesi:

GES denetimlerinde endüstri standardı olarak kabul edilen DJI Matrice 350 RTK platformu, projenin "Sanal Prototipi" olarak seçilmiştir. Literatür taraması sonucunda cihazın şu özellikleri ön plana çıkmaktadır:
• Platform Dayanıklılığı: IP55 koruma sınıfı, sahada karşılaşılabilecek toz ve su sıçramalarına karşı sistemin otonom görevini sürdürmesini sağlar.
• Konumlandırma Hassasiyeti: D-RTK 2 desteği ile yatayda ±0.1 m ve dikeyde ±0.1 m hassasiyet sunar. Bu, CS ekibinin tespit ettiği arızaların koordinat bazlı (santimetrik) eşleştirilmesi için kritiktir.
• Yük Kapasitesi: Maksimum kalkış ağırlığı (MTOW) 9.2 kg olup, yaklaşık 2.7 kg'lık ek faydalı yük (payload) kapasitesine sahiptir.

## Teorik Uçuş Dinamikleri

Sanal simülasyon ortamında (Gazebo/AirSim) İHA'nın fiziksel motoruna girilecek olan "Gerçek Dünya" kısıtları şu şekilde modellenmiştir:
A. Kaldırma Kuvveti (Thrust) Analizi
Datasheet verilerine göre operasyonel ağırlık (Gövde + 2x TB65 Batarya + Zenmuse H20T) yaklaşık 7.27 kg'dır.
• Yerçekimi Kuvveti (G): 7.27 kg x 9.81 m/s2 71.32 N
• Gerekli Toplam İtme (T): Dinamik manevralar ve rüzgar direnci için 2:1 itme-ağırlık oranı baz alınarak toplam itki 142.64 N olarak belirlenmiştir.
• Motor Başına Nominal İtki: 4 motorlu (quadcopter) yapı için motor başına düşen yük 35.66 N'dur.

## Rüzgar Direnci ve Aerodinamik Sürüklenme

GES sahaları açık alanlar olduğu için İHA'nın rüzgar dayanımı denetim kalitesini doğrudan etkiler.
• Limit Değer: Maksimum rüzgar direnci 12 m/s (43.2 km/h) olarak belirlenmiştir.
• Sanal Model: Simülasyonda 12 m/s üzerindeki rüzgar hızlarında, İHA'nın maksimum eğim açısının (Pitch: 30°) yetersiz kalacağı ve görüntü stabilizasyonunun bozulacağı (motion blur) teorik olarak kabul edilmiştir.

## Termal Kamera ve Sensör Gereksinimleri (Zenmuse H20T)

Yapay zekâ (CS) modelinin eğitileceği verilerin kalitesini belirleyen optik ve radyometrik gereksinimler şunlardır:
• Termal Çözünürlük: 640x512 px (Radyometrik).
• Termal Duyarlılık (NETD): ≤ 50 mK (0.05°C). Bu değer, panel üzerindeki "mikro-çatlak" ve "hotspot" arızalarını ayırt etmek için gereken hassasiyeti sağlar.
• Radyometrik Veri: Sıcaklık bilgilerinin ham olarak işlenebilmesi için R-JPEG formatı tercih edilmiştir.
C. GSD (Ground Sample Distance) Hesaplaması
Simülasyonda drone'un panelleri ne kadar detaylı göreceğini belirleyen matematiksel ispat:
• Parametreler: Odak uzaklığı (f) = 13.5 mm, Piksel aralığı (p) = 17 µm, Uçuş yüksekliği (H) = 20 m.
• Formül: GSD = (p x H) / f
• Hesap: (17 x 10-6 x 20) / (13.5 x 10-3) 0.025 m
Sonuç: 20 metre irtifada yerdeki her piksel 2.5 cm'lik bir alanı temsil eder. Bu çözünürlük, GES panellerindeki hücre (cell) bazlı ısınmaları tespit etmek için yeterlidir.

## Donanım Blok Diyagramı ve Veri Akış Mimarisi

Sistemin disiplinler arası veri akış mimarisi şu bloklardan oluşmaktadır: 1. Güç Bloğu: 2 adet TB65 Akıllı Batarya (5880 mAh, 44.76V) → Güç Dağıtım Kartı (PDB). 2. Sensör ve Veri Bloğu: Zenmuse H20T (Termal + RGB) →Gimbal Stabilizasyon $\rightarrow$ O3 Enterprise Görüntü Aktarımı. 3. Kontrol Bloğu: Dual RTK Antenleri + IMU →Uçuş Kontrolcüsü (FC). 4. Haberleşme Bloğu: 2.4/5.8 GHz Dijital Link →Yer Kontrol İstasyonu (GCS).
