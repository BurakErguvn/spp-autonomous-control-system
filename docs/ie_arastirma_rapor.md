# Endüstri Mühendisliği Araştırma İçeriği Cevapları

Sistemin optimizasyon modülünde şu an varsayılan olarak kullanılan parametrelerin listesini içermektedir. Endüstri Mühendisliği ekibinin literatür taraması veya sektör araştırması yaparak bu değişkenlerin gerçek dünyadaki karşılıklarını bulması ve modüle entegre etmesi gerekmektedir.

## Fırsat Maliyeti (Üretim Kaybı) Parametreleri

• Enerji Birim Fiyatı (PTF / YEKDEM):

Türkiye’de elektrik satış fiyatı EPİAŞ tarafından belirlenen PTF’ye göre değişmektedir. Ortalama değer 1.5–2.5 TL/kWh aralığındadır. Bu çalışmada hesaplama kolaylığı açısından 2 TL/kWh alınmıştır. YEKDEM kapsamında ise bu değer yaklaşık 4 TL/kWh seviyesine çıkabilmektedir.

    • Hotspot (Isınma Noktası) Kaybı:

Hotspot arızası panel verimini doğrudan düşürmektedir. Literatürde %10–%30 arası kayıp görülmektedir. Bu çalışmada ortalama %20 üretim kaybı kabul edilmiştir.

    • Mikro Çatlak Kaybı:

Mikro çatlaklar başlangıçta düşük etkili olup yaklaşık %5 verim kaybı oluşturur. Ancak zamanla ilerleyerek bu kayıp artabilir ve panel arızasına dönüşebilir. Bu nedenle modelde zamanla artan kayıp olarak düşünülmelidir.

    • Tozlanma (Soiling) Kaybı:

Tozlanma panel verimini kademeli olarak düşürmektedir. Aylık bazda %5–%20 arası kayıp oluşabilir. Bu çalışmada ortalama %10 aylık kayıp kabul edilmiştir.

## Bakım Maliyeti Parametreleri

Optimizasyon algoritmasının "bu arızayı tamir etmenin masrafı nedir?" sorusuna gerçekçi cevap verebilmesi için:
• İşçilik Maliyeti:

GES bakım personeli için saatlik maliyet ortalama 150– 300 TL/saat aralığındadır. Modelde 200 TL/saat alınması dengeli bir varsayımdır.

    • Müdahale (Tamir) Süreleri:

Hotspot müdahalesi: 30– 60 dk (ortalama 45 dk)
Panel değişimi: 1–2 saat
Panel temizliği: 5–10 dk/panel (ortalama 7 dk)
Bu süreler kapasite planlama ve rota optimizasyonu için doğrudan kullanılmalıdır.

    • Malzeme Değişim Maliyetleri:

Hotspot her zaman panel değişimi gerektirmez.
Bypass diyot değişimi: 50–200 TL
Panel değişimi: 3000–6000 TL
Modelde arızaların %70’i diyot değişimi, %30’u panel değişimi olarak alınabilir.

    • Ulaşım ve Lojistik:

Bakım araçlarının yakıt maliyeti ortalama 2–4 TL/km aralığındadır. Bu çalışmada 3 TL/km alınmıştır.

## Operasyonel Kısıtlar (MILP ve VRP Kısıtları)

Karar destek sisteminin matematiksel (MILP) kısıtlarına yazılacak gerçek dünya sınırları:
• Günlük Mesai Sınırı:
Bakım ekipleri için günlük çalışma süresi maksimum 8 saat olarak kabul edilmiştir.

    • Ekip Sayısı:

Ortalama 10 MW büyüklüğünde bir GES için 2–4 ekip bulunur. Modelde 3 ekip kabul edilmiştir.

    • İHA Uçuş ve Denetim Sınırı:

İHA’ların uçuş süresi 20–40 dakika aralığındadır. Bu sürede yaklaşık 500–1500 panel taranabilir. Modelde 30 dakika ve 1000 panel alınmıştı.

## Senaryo Analizi İçin Kıyaslama Metrikleri

• Geleneksel Bakım Sıklığı:
İHA kullanılmadan önce paneller genellikle yılda 1–2 kez manuel olarak kontrol edilmektedir. Bu yöntemin yıllık maliyeti yaklaşık 300.000–800.000 TL aralığındadır. Bu değer, önerilen sistemin sağlayacağı tasarrufu göstermek için referans alınmıştır.
