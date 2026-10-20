# Arıza tiplerine göre onarım maliyeti, enerji kaybı ve geleneksel tespit

İlgili issue'lar: #6 (diyot/bypass/string sınıflarının taksonomi kararı), #10 (maliyet parametreleri kaynaksız).
Hazırlayan: araştırmacı, erişim tarihi 2026-10-20. Bu belge **karar vermez**; kararlar (taksonomi, maliyet parametreleri) kullanıcıdadır. Parametre önerileri "Öneri" bölümündedir.

Etiketler: **[K]** kaynakta doğrudan var; **[T]** tahmin / çıkarım (kaynaksız, doğrulanmamış); **[D]** doğrulanamadı (kaynağa erişilemedi veya bulunamadı).
Kaynak türleri: HM hakemli makale, ST standart, RK resmi/kurum raporu (IEA PVPS, NREL vb.), SUN sunum (kurum çalıştayı), UR üretici/tedarikçi, BL blog/haber.

## 0. Önemli sınırlar (önce okuyun)

- **NREL/TP-5C00-74840 (Walker 2020) tablolarına erişilemedi**: `nrel.gov`, `www.nrel.gov`, `docs.nrel.gov` alan adları ortamdan çözümlenmedi (`getaddrinfo ENOTFOUND`). Modül değişimi, termal denetim ve temizlik satır maliyetleri için NREL değeri **[D]**. Bu yüzden Avrupa kaynakları (IEA PVPS) öne çıkıyor.
- **SolarPower Europe O&M Best Practices (v5.0/v6.0) PDF'ine erişilemedi**; yalnızca sürüm bilgisi doğrulandı (v6.0, 18 Şubat 2025). Sayısal değer alınmadı.
- Türkiye için **birim fiyat bulunamadı**: panel temizliği (TL/MW veya TL/m2), GES O&M sözleşme bedeli (USD/kWp/yıl), Türkiye perakende modül fiyatı. Bunlar **[D]**; yerel teklif alınması gerekir.
- **Adam-saat süreleri** için yayımlanmış bir kaynak bulunamadı (diyot/bağlantı kutusu değişimi, konnektör onarımı, string yeniden bağlama). Tablodaki süreler **[T]** ve yalnızca büyüklük mertebesi içindir.
- Kur: yalnızca bilgi amaçlı, 09 Eylül 2026 sayfası: 1 USD ≈ 48,4 TL, 1 EUR ≈ 56,2 TL (BL, kur sitesi; TCMB'den doğrulanmadı, Ekim 2026 resmi kuru bulunamadı). Aşağıdaki hiçbir TL değeri kaynaklı değildir; EUR değerleri kaynaklıdır.

## 1. Özet tablo (arıza tipi × alanlar)

Modül = ~550-600 Wp sınıfı varsayımı (kaynaktaki 600 Wp örneğiyle uyumlu). "Kayıp" = arızalı birimin gücünde göreli kayıp.

| Arıza tipi (sınıf) | Tipik müdahale | Malzeme + işçilik | Süre (adam-saat) | Güç kaybı | Aciliyet | Geleneksel tespit (kapsama) |
|---|---|---|---|---|---|---|
| **Hotspot** (Single/Multi): ısınan hücre | Önce nedeni ayır: gölgeleme/kir ise temizlik; hücre/lehim hasarı ise modül değişimi (üretici garantisi varsa malzeme bedelsiz) | Modül ~0,10 €/Wp = ~60 € (600 Wp) + montaj ~30 € [K, SUN Köntges 2025]; garanti dışı işçilik üretici tarafından karşılanmaz [K, UR/PVEL] | ~0,5-1 sa/modül **[T]** (montaj 30 € bedelinden çıkarım) | Hücre ters öngerilimde ise bypass devreye girer: modülün ~1/3'ü; aktif olmayan alan <%8 ise ihmal edilebilir, >%8 doğrusal artar [K, RK T13-01 §6.2.2]. Kod'daki %20 kaynaksız | **Yüksek**: yangın riski B(f); hücre ters öngerilim yanık/yangın [K, RK T13-01 §6.2.7] | El tipi IR (yürüyüş), drone IR (IEC TS 62446-3); I-V eğrisi hotspot'u değil kaybı ölçer; EL hücre kusurunu gösterir ama sıcaklığı değil |
| **Bypass diyot arızası / bypass edilmiş alt dizi** (SingleDiode/MultiDiode, SingleByPassed/MultiByPassed) | Bağlantı kutusu veya diyot değişimi (lehimli/mühürlü kutuda çoğu zaman tüm modül değişir [K, BL]); gölge kaynaklıysa gölge giderme | Modül değişiminde yukarıdaki ~90 €/modül [K]; yalnız diyot onarımı için fiyat bulunamadı **[D]** (tek bir tedarikçi sözlüğü Rs 15.000-25.000/modül veriyor, düşük güven [UR/BL]) | ~0,5-1,5 sa/modül **[T]** | Aktif bypass: alt dizi başına ~1/3 güç (3 diyotlu modül) [K, RK T13-01 §6.2.2: "inactive area ≥50% → 1/3 kayıp"]; tedarikçi: %33-66 verim kaybı [UR]. Açık devre diyot: normal çalışmada kayıp yok, gölgede büyük kayıp [K, RK T13-01 §6.2.7] | **Yüksek (açık devre diyot: gizli güvenlik riski)**: açık devre diyot + gölgelenme → hücre ters akımla yanar [K, RK T13-01]; "bağlantı kutusu güvenlik ve performans riski" [K, SUN Köntges 2025] | Drone/el IR: **aktif** bypass alt dizisi daha sıcak görünür [K, RK T13-01 Tab.]; **açık devre diyot IR'de normal şartlarda görünmez**, ek yöntem gerekir (gece ters gerilim %3-5 Isc, sinyal iletim yöntemi) [K, SUN Köntges 2025]; bir tedarikçi sunumu drone taramasının bunu kaçırabileceğini söylüyor [BL/SUN, ikincil] |
| **String açık devre** (StringOpenCircuit) | Konnektör/sigorta/kablo/birleştirme kutusu bağlantısı onarımı veya string yeniden bağlama | Konnektör onarımı için fiyat bulunamadı **[D]**; malzeme küçük, işçilik baskın | ~0,25-1 sa/string **[T]** | String'in **tamamı** (~%100 × string uzunluğu, örn. 20-28 modül) [K, RK T13-01 §1: "kötü crimp'li konnektör bütün string'de toplam güç kaybı yapabilir"] | **Yüksek**: gevşek/kötü konnektör ark ve yangın yapabilir; PV yangın kaynaklarının %29'u konnektör [K, RK T13-01, Schmidt13 aktarımı]; yük altında konnektör ayrılmamalı [UR/BL] | **En ucuz yakalanan sınıf**: string izleme/SCADA'da sıfır akım; drone IR'de tüm string diğerlerinden farklı sıcaklıkta [K, RK T13-10 §2, "devre dışı modül/string daha sıcak"]; yürüyüşle yalnız Voc/Isc ölçümü bulur |
| **String ters polarite** (StringReversedPolarity) | Konnektör/kablo uçlarını doğru bağlama (commissioning hatası) | Malzeme ~0; işçilik | ~0,25-0,5 sa/string **[T]** | String çıkışı yok / evirici girişinde hata. Saha yaygınlığı için kaynak yok **[D]** | **Yüksek**: evirici giriş katını bozabilir, ark yapabilir [UR/BL, tek kaynak] | IEC 62446-1 polarite testi (Kategori 1, ~30 sn/string, çoklu ölçer) commissioning'de [ST via BL/UR]; işletmede SCADA string akımı. **IR ile tespit edilebilirliği doğrulanamadı [D]** |
| **Hücre çatlağı / fiziksel hasar** (Physical Damage, Defective) | Çatlak hücreli modül: izleme; kayıp büyükse değişim. Cam kırığı: acil değişim | Modül değişimi ~90 € [K] | ~0,5-1 sa/modül **[T]** | Çoğu çatlak 2 yılda anlamlı kayıp yapmaz; bir parkta 6 yılda modüllerin ~%50'si ≥%10 kayıp, %3,8'inde bypass devrede [K, RK T13-01 §6.2.2, Buerhop11]; inaktif alan ≥%50 → 1/3 kayıp | Çatlak: orta (B(f)); **cam kırığı yüksek**: yalıtım hatası, ark, yangın [K, SUN Köntges 2025] | Çatlak için en iyi EL (€1.500-2.500/MW, 2-4 sa/MW) [K, SUN Tsanakas 2025]; IR yalnız ısınanı yakalar; cam kırığı görsel/RGB drone; "çatlak saymaya gerek yok, yalnız yüksek kayıp + güvenlik" [K, SUN Köntges 2025] |
| **Elektriksel hasar** (Electrical Damage) | Yanık/ark izli modül veya bağlantı kutusu: modül ya da kutu değişimi | ~90 €/modül [K] | ~0,5-1,5 sa **[T]** | Kaynakta tanımlı değil; yanık izi çoğu zaman açık devre diyot veya kopuk hücre bağlantısıyla ilişkili [K, RK T13-01, yanık izi ve bypass diyot bölümleri] | **Yüksek**: doğrudan güvenlik sorunu C(f,m,e) örneği: kopuk hücre şeridi (>500 °C) [K, RK T13-01, hücre bağlantı şeridi bölümü] | Görsel + IR (sıcak bağlantı kutusu); taksonomi tanımı netleşmeli (bkz. §6) |
| **Tozlanma** (Dusty) | Yıkama/kuru temizlik | Türkiye TL/MW **[D]**; ABD konut fiyatları ilgisiz | Önceki kod: 7 dk/panel (kaynaksız); gerçek: toplu, MW başına saatler **[T]** | Konya çatı GES: ortalama kirlenme **%0,296/gün** (HM-dışı, tez), kuru mevsim optimum 31 gün/yılda 6 temizlik [K, tez 2024]; sanayi bölgesi Türkiye: %5-17 kayıp, ort. PR düşüşü %10,8 [K, HM özeti]; küresel ≥%3-4 [K, HM Ilse 2019] | **Düşük**; IEC TS 62446-3'e göre IR öncesi temizlik gerekir [K, SUN Tsanakas 2021] | RGB/IR drone (düzgün olmayan sıcaklık), PR/kirlenme istasyonu; yürüyüşle gözle |
| **Kuş pisliği** (Bird Drop) | Nokta temizlik | Küçük; temizlik ekibi | Dakikalar/panel **[T]** | Sistem düzeyinde %7,4 [K, HM Sustainability 2020]; panelin %30'u kaplı 25 günde %35 çıkış kaybı (tek deney) [K, HM Sukkur 2024]; ¼, ½, ¾ gölge → %33,7, %45,1, %92,6 [K, aynı 2020 makale] | **Orta**: lokal gölge hotspot yapabilir ("pointed heating – bird dropping", B(f)) [K, RK T13-01 IR tablosu] | Drone RGB/IR; yürüyüş |
| **Kar** (Snow) | Müdahale yok/doğal erime; mekanik temizlik hasar riski | Bakım maliyeti ~0 (sınıf bakım seçimi dışı önerilir) | – | ABD'de yıllık %0-16, düşük eğimli sabit sistemde >%9 [K, RK NREL/Marion 2013, ikincil özet]; Türkiye (Konya) sayı alınamadı **[D]** | Düşük (güvenlik: kar yükü hasarı ayrı) | Hava/uydu verisi, RGB drone |

## 2. Geleneksel tespit ile drone IR karşılaştırması

| Yöntem | €/MW | sa/MW | Kapsama | Kaynak |
|---|---|---|---|---|
| Drone IR | 450-650 | 0,4-0,8 | Hotspot, aktif bypass, açık string/modül, bağlantı kutusu ısınması; açık diyot ve çatlak çoğunlukla kaçar | [K, SUN Tsanakas 2025, slayt 4] (Avrupa; tipik aralık, denetlenmiş değil) |
| Drone RGB | 250-400 | 0,3-0,6 | Kir, gölge, bitki, montaj | aynı |
| Saha EL/PL | 1.500-2.500 | 2-4 | Hücre düzeyi çatlak, kusurlar | aynı |
| Saha I-V eğrisi | 900-1.400 | >4 (örnekleme) | Modül/string güç kaybı ölçümü; açık diyot dolaylı | aynı |
| Manuel/görsel (araç + ekip) | 400-800 / ziyaret | >4 | Doğrulama, onarım | aynı |
| "Manuel + el tipi IR" taban değer | 350 | – | Eski uygulama referansı (örnek: 100 MW) | [K, SUN Tsanakas 2025, slayt 14] |
| El tipi IR süresi | – | 15-20 sa / 4 MWp ≈ 3,75-5 | İdeal koşul | [K, RK IEA PVPS T13-10:2018 §1] |
| Drone IR süresi (T13-10) | – | 5-10 sa / 4 MWp ≈ 1,25-2,5 | İdeal koşul | aynı |
| Drone IR verimi (2021) | – | ~12 MW/gün (~3 MW/sa) | IEC uyumlu; uçak 100-150 MW/sa | [K, SUN Tsanakas 2021, slayt 13] |
| Drone IR (İtalya vaka, ikincil) | 800 €/gün, ~20 MW/gün | – | pv magazine özeti; birincil metne erişilemedi **[D]** | [BL, pv-magazine] |
| Tedarikçi vakası | – | 74 MW'ta 24 sa drone / 778 sa manuel (~0,32 vs ~10,5 sa/MW) | UR iddiası, ikincil özet | [UR, EagleNXT/Aerospec] |

Çelişki: Tsanakas 2025 sunumundaki 0,4-0,8 sa/MW ile T13-10'daki 1,25-2,5 sa/MW farklı; muhtemel neden: T13-10 uçuş + ön/arka hazırlığı ve eski kamera/uçuş koşullarını, Tsanakas ise yalnızca etkin uçuş verimini yansıtıyor (neden **[T]**). Bizim sistem (DJI M350 + H30T benzeri) için 12 MW/gün ≈ 0,67 sa/MW makul merkezdir.

Köntges (2025) uyarısı: arıza bulmak yalnızca yüksek kayıplı ve güvenlik arızaları için ekonomik; düşük arıza oranında bulmak karşılığını vermez [K, SUN Köntges 2025, slayt 10, 16]. Drone IR'ye Tsanakas örneği: ek denetim maliyeti (550-350) €/MW, yıllık fayda 29.760 €/100 MW, ilk yıl net +9.760 € [K, SUN Tsanakas 2025, slayt 14; varsayımlar: enerji 60 €/MWh, 1.600 MWh/MW/yıl].

## 3. Modül değişim ekonomisi (Köntges 2025) ve sonuç

Kaynak [K, SUN Köntges, Task 13 çalıştayı, 23 Ekim 2025, slayt 9] (EUR, 2025): modül 0,10 €/Wp → 600 Wp = 60 €; verim 1 kWh/Wp/yıl, enerji 0,05 €/kWh → 30 €/yıl/modül; montaj ~30 € (garanti durumu).
- %100 kayıplı modül değişim bedelini ~1 yılda öder; %10 kayıplı modül ~10 yılda.
- Bu mantık Türkiye için PTF ve verimle yeniden hesaplanmalıdır (karar kullanıcıda).

## 4. Matematik: kullanılabilir kayıp ve maliyet formülleri

Arıza `f` için, `n_f` etkilenen modül sayısı, `P` modül gücü (kWp), `Y_d` günlük özgül verim (kWh/kWp/gün), `c_e` enerji fiyatı (TL/kWh), `H` karar ufku (gün):

**Güç kaybı oranı (modül düzeyi):**
$$L_f = \begin{cases} \dfrac{1}{N_{sub}} \approx 0{,}33 & \text{aktif bypass / alt dizi devre dışı} \\ \max\!\left(0,\ \alpha\,(a_{in}-0{,}08)\right) & \text{çatlak, inaktif alan oranı } a_{in} \text{ (doğrusal, } a_{in}\ge 0{,}5 \Rightarrow 1/3) \\ 1 & \text{modül tamamen devre dışı} \end{cases}$$
`N_sub` = bypass diyot (alt dizi) sayısı (3 diyotlu 60 hücreli modül, [K, T13-01 §6.2.2]); `α` kaynakta ayrıca verilmemiş (**[D]**; "doğrusal artış" denmiş).

**String düzeyi:** string `S` modülden oluşur, açık devrede `L_str = 1` ve etkilenen modül sayısı `n_f = S`. Aktif bypass'ta MPPT altında kayıp ilk yaklaşım `n_f · L_f` (modül başına), seri akım uyumsuzluğu nedeniyle gerçek kayıp daha büyük olabilir; T13-01 Şekil 6.2.2 bunu niteliksel gösteriyor, sayısal katsayı **[D]**.

**Fırsat maliyeti (sabit kayıp):**
$$C_{opp}(f,H)=n_f\,L_f\,P\,Y_d\,c_e\,H$$

**Tozlanma (yağışla sıfırlanana dek doğrusal birikim, temiz başlangıç):** günlük oran `r` (Konya: 0,00296/gün), ufuk `H`:
$$C_{opp}^{toz}(H)= n\,P\,Y_d\,c_e\;\frac{r\,H^{2}}{2}\quad(\text{kümülatif kayıp}),\qquad L_{ort}=\tfrac{rH}{2}$$
Mevcut kod `%10/ay` = 0,33%/gün ve bunu sabit alıyor; ortalama kayıp aslında `rH/2`'dir (H=30 gün için ~%4,4).

**Bakım maliyeti (beklenen):**
$$C_{maint}(f)=\frac{t_f}{60}\,n_{ekip}\,w + \sum_k p_{f,k}\,m_k + c_{yol}$$
`t_f` dk, `w` TL/adam-saat, `m_k` malzeme, `p_{f,k}` onarım türü olasılığı (ör. diyot vs modül; kodun %70/%30'u kaynaksızdır **[D]**; PVEL ve Köntges çoğu zaman tüm modülün değiştiğini belirtir).

**Bakım karar kuralı ve geri ödeme süresi:**
$$\text{Bakım yap} \iff C_{maint}(f) < C_{opp}(f,H)\ \text{ veya güvenlik sınıfı C/yangın riski};\qquad T_{pay}=\frac{C_{maint}}{n_f L_f P Y_d c_e\cdot 365}\ \text{(yıl)}$$
Köntges örneği: `C_maint`=30 € (montaj, garantili), `L_f=1`, 30 €/yıl → `T_pay ≈ 1` yıl; `L_f=0,1` → ~10 yıl.

**Beklenen yangın riski maliyeti** (kod şu an yok sayıyor): $C_{fire}=p_{f}\,\cdot\,V_{varlık}$; `p_f` için kaynak **[D]**. Yalnızca nitel veri var: hotspot ve açık/kopuk bağlantılar B(f) veya C(f), konnektör PV yangınlarının %29'u [K, T13-01].

**Tespit maliyeti:** $C_{insp}=c_{MW}\cdot P_{tesis}$, drone IR için `c_MW`≈450-650 €/MW [K, SUN Tsanakas 2025].

**İşçilik tabanı (Türkiye 2026):** asgari ücret brüt 33.030 TL, net 28.075,5 TL, işveren maliyeti ~39.223-40.875 TL/ay (kaynaklar farklı SGK indirimi varsayıyor) [K, BL/EY/QNB özetleri; resmî kaynak (ÇSGB/SGK) doğrulanmadı]. Saatlik işveren maliyeti = 40.875 / 225 sa ≈ **182 TL/sa** (kendi hesabım; 225 sa/ay varsayımı) → koddaki 200 TL/sa asgari ücretli işçilik düzeyindedir, teknik personel (elektrik teknisyeni) için bu bir **alt sınırdır**; teknisyen ücreti için kaynak **[D]**.

## 5. Öneri (karar kullanıcıda)

1. **Kapsama alınmaya en uygun yeni sınıflar** (enerji kaybı ve aciliyet açısından): `StringOpenCircuit` (kayıp ~%100×string, ama SCADA ile ucuz yakalanır; drone yalnız yer belirler) ve **aktif** bypass/`ByPassed` (≈1/3 modül). Bu sınıfların maliyeti hotspot'tan yüksektir, issue #6'nın gerekçesiyle uyumlu.
2. **Taksonomi önerisi (artı/eksi):**
   - (a) Diyot ve bypass'ı tek sınıfta birleştir ("alt dizi arızası"): termalde aynı desen, etiket çelişkisi biter; kayıp 1/3 sabit. Eksi: açık devre diyot (gizli yangın riski) IR'de zaten görünmez.
   - (b) Tüm sınıfları ayrı tut: daha ince, ancak veri/ayırt edilebilirlik zayıf.
   - (c) Atılacaksa görüntüleri eğitimden çıkar (issue #6 seçenek 2).
   `StringReversedPolarity` işletmede nadir ve IR'de ayırt edilebilirliği kanıtlanmadı **[D]**; ayrı sınıf yapmamak makul.
3. **Kar** sınıfını bakım seçiminden çıkar (müdahale edilemez); **kuş pisliği/toz** için maliyeti "grup temizlik turu" olarak modelle, tek panel olarak değil.
4. **Yangın/güvenlik** terimi ekle: hotspot, açık devre/konnektör, elektriksel hasar, cam kırığı için zorunlu onarım (kodda `MUST_FIX_CLASSES` benzeri). Sayısal ceza için kaynak yok; parametre kullanıcı kararı.
5. **Parametre kaynak boşlukları** (teklif alınmalı): Türkiye'de modül fiyatı (TL/Wp), teknisyen TL/sa, temizlik TL/MW, adam-saat süreleri, diyot onarım olasılığı.
6. Sayı çelişkilerinde aralık kullan (ör. drone IR 0,4-2,5 sa/MW; kaynaklar arası farkın nedeni §2).

## 6. Taksonomi notu (veri seti)

"Defective" ve "Electrical Damage" sınıflarının tam tanımı bu araştırmada doğrulanamadı; etiket kılavuzuna bakılmalı. Bu belgede "Defective" = hücre/modül kusuru, "Electrical Damage" = yanık/ark izi/bağlantı kutusu hasarı varsayıldı **[T]**.

## 7. Kaynak listesi

| # | Kaynak | Tür | Tarih | Bağlantı | Kullanım |
|---|---|---|---|---|---|
| 1 | Köntges vd., *Review of Failures of Photovoltaic Modules*, IEA-PVPS T13-01:2014 | RK | Mart 2014 | https://iea-pvps.org/wp-content/uploads/2020/01/IEA-PVPS_T13-01_2014_Review_of_Failures_of_Photovoltaic_Modules_Final.pdf | Bypass diyot (§6.2.7), çatlak (§6.2.2), konnektör, güvenlik sınıfları, IR desen tablosu. Metin PDF'den `pdftotext` ile okundu |
| 2 | Jahn vd., *Review on IR and EL Imaging for PV Field Applications*, IEA-PVPS T13-10:2018 | RK | Mart 2018 | https://iea-pvps.org/wp-content/uploads/2020/01/Review_on_IR_and_EL_Imaging_for_PV_Field_Applications_by_Task_13.pdf | El tipi/drone IR ve EL süreleri (4 MWp), IR ile tespit edilen arızalar. PDF okundu |
| 3 | Tsanakas, *Advances needed in PV plants inspections*, Task 13 çalıştayı, ISFH | SUN | 23 Ekim 2025 | https://iea-pvps.org/wp-content/uploads/2025/08/03_Ioannis-Tsanakas_Advances-needed-in-PV-park-inspection.pdf | €/MW ve sa/MW tablosu (slayt 4), ROI örneği (slayt 14). PDF okundu |
| 4 | Tsanakas, *Aerial Inspections and Diagnostics of PV Power Plants*, Task 13 O&M çalıştayı | SUN | 30 Eylül 2021 | https://iea-pvps.org/wp-content/uploads/2021/10/03_I.-TSANAKAS_-Aerial-Inspections-for-Optimized-OM.pdf | 12 MW/gün drone IR, IEC TS 62446-3 özeti, O&M benchmark 8-15 k€/MW/yıl. PDF okundu |
| 5 | Köntges, *Failure in current PV systems and their relevance to find them*, Task 13 çalıştayı | SUN | 23 Ekim 2025 | https://iea-pvps.org/wp-content/uploads/2025/08/02_Koentges_Failures-in-current-PV-systems-and-their-relevance-to-find-them.pdf | Modül değişim maliyet yapısı (slayt 9), kayıp bypass diyot tespiti, "yalnız yüksek kayıp + güvenlik" (slayt 10, 16). PDF okundu |
| 6 | Walker vd., *Model of O&M Costs for PV Systems*, NREL/TP-5C00-74840 | RK | Haz 2020 | https://www.nrel.gov/docs/fy20osti/74840.pdf | **Erişilemedi [D]**; yalnızca arama özeti (yöntem). Sayı alınmadı |
| 7 | SolarPower Europe, *O&M Best Practice Guidelines v6.0* | RK/sektör | 18 Şub 2025 | https://www.solarpowereurope.org/insights/thematic-reports/operation-and-maintenance-best-practice-guidelines-version-6-0 | Yalnızca sürüm doğrulandı; sayı alınmadı [D] |
| 8 | Ilse vd., *Techno-Economic Assessment of Soiling Losses…*, Joule 3(10):2303 | HM | 2019 | https://elib.dlr.de/129424 | Küresel kirlenme kaybı ≥%3-4 (özet); tam metin okunmadı |
| 9 | Erbakan Üniv. tezi, toz birikimi ve temizlik sıklığı (Konya, 1,976 MWp) | tez | 2024 | https://acikerisim.erbakan.edu.tr/items/1173eca0-c779-49a7-a527-4ceb59c199e7 | Günlük kirlenme %0,2959, 31 gün/6 temizlik, 3 temizlikten %18 maliyet düşüşü (özet) |
| 10 | Sanayi bölgesi rooftop PV kirlenme ve termal stres (Türkiye) | HM (özet) | – | https://avesis.uludag.edu.tr/yayin/8672c9dd-0600-40f1-abea-a8b09fe8e04c/quantifying-the-impact-of-soiling-and-thermal-stress-on-rooftop-pv-performance-seasonal-analysis-from-an-industrial-urban-region-in-turkiye | %5-17 kayıp, ort. PR düşüşü %10,8 (arama özeti, tam metin okunmadı) |
| 11 | Çevresel etkiler (toz, su, kuş pisliği, gölge), Sustainability 12(2):608 | HM | 2020 | https://www.mdpi.com/2071-1050/12/2/608/xml | Kuş pisliği %7,4; gölge %33,7/45,1/92,6 (arama özeti; tam metin okunmadı) |
| 12 | Kuş pisliği deneyi, Sukkur IBA J. Emerging Technologies | HM | Mayıs 2024 | https://doaj.org/article/71c698b467fa4f199b38b54de3ce5255 | %30 kaplama, 25 gün, %35 kayıp (arama özeti) |
| 13 | Marion vd. kar modeli (SAM) | RK | 2013 | https://research-hub.nrel.gov/en/publications/integration-validation-and-application-of-a-pv-snow-coverage-mode/ | Yıllık kar kaybı 0-16%, >9% düşük eğim (ikincil özet) |
| 14 | IEC 62446-1 polarite/Voc testi özetleri | ST (ikincil UR/BL) | – | https://www.surgepv.com/blog/solar-polarity-test ; https://www.wattuneed.com/en/measure-pv-string-voc-isc-riso.htm | Standart metnine erişilmedi [D]; ters polarite riski ve test süresi blog iddiasıdır |
| 15 | IEC TS 62446-3:2017 | ST | 2017 | – | Standart metnine erişilmedi [D]; yalnızca Tsanakas 2021 özetinden dolaylı (hava koşulu, temizlik, yılda en az 2 denetim önerisi) |
| 16 | pv magazine, Drones vs. aircrafts for PV plant inspection | BL | – | https://www.pv-magazine.com/?p=35598 | İtalya vakası 800 €/gün, 20 MW/gün (arama özeti; metin okunmadı) |
| 17 | EagleNXT / Aerospec vaka çalışmaları | UR | 2018, 2020 | https://eaglenxt.com/case-study/case-study-increasing-solar-inspection-efficiency-with-drones/ ; https://www.suasnews.com/2020/08/aerospec-aerial-inspection-roi-1915-mw-in-potential-savings/ | Tedarikçi iddiaları; sadece yön göstergesi |
| 18 | PVEL Module Scorecard, bypass diyot vakası (12 MW Tayvan) | UR/RK | 2023 | https://2023modulescorecard.pvel.com/failures/ | İşçilik garanti dışı (arama özeti) |
| 19 | Asgari ücret 2026 özetleri (EY, QNB, vb.) | BL/kurumsal | 2026 | https://www.ey.com/tr_tr/insights/tax/2026-asgari-ucret ; https://www.qnbinvest.com.tr/investodak/qnbarastirma/2026-asgari-ucret-aciklandi-net-28075-tl | Brüt 33.030, net 28.075,5 TL, işveren maliyeti ~39.2-40.9 k TL |
| 20 | Kur sayfası (9 Eylül 2026) | BL | 2026-09-09 | arama sonucu, tcmb.gov.tr ile doğrulanmadı | USD 48,4, EUR 56,2 TL (yalnız bilgi) |
| 21 | OPIS / sun.store modül fiyatları (arama özeti) | BL | Tem-Eyl 2026 | https://www.pv-tech.org/european-pv-module-prices-ease-out-in-september/ | TOPCon FOB Çin 0,109 $/W; Avrupa 0,114 €/Wp (birincil metin okunmadı) |
| 22 | Raptor Maps Global Solar Report 2025 | UR | 2025 | https://pages.raptormaps.com/hubfs/Marketing%20Content%20for%20Website/2025%20Raptor%20Maps%20Global%20Solar%20Report%20compressed.pdf | PDF 10 MB sınırını aştığı için okunamadı [D]; yalnızca string+birleştirme kutusu kayıp payı (%26,9 + %21,5, pv magazine ABD Şub 2026) |

## 8. Açık konular

- NREL 74840 ve SolarPower Europe v6.0 sayısal tablolarına erişim yok; ortamdan erişimi olan biri indirip eklenebilir.
- Türkiye yerel fiyat teklifleri (modül, teknisyen, temizlik, drone hizmeti TL/MW) toplanmadan TL parametreleri kaynaklı olamaz.
- Hotspot/bypass/string arızalarının saha düzeyindeki yaygınlığı ve ΔT→güç kaybı katsayıları için hakemli, kalibre edilmiş kaynak bulunamadı (yalnız tedarikçi bantları).
