# Veri seti genişletme araştırması (Issue #6)

Tarih: 2026-10-20. Yöntem: yalnızca sayfa/metadata okundu, hiçbir veri seti indirilmedi. "Doğrulanamadı" = sayfaya erişilemedi veya sayfa söylemiyor. Kaynak türleri: [H] hakemli makale/veri makalesi, [P] preprint (arXiv), [R] resmi/kurumsal depo, [K] topluluk platformu, [İ] ikincil (arama özeti/blog).

## 0. Mevcut setin kökeni (yerel dosyalardan, ölçüldü)

- `data/SOLAR PANEL DET.v1i.yolo26/data.yaml`: 15 sınıf, "Veri Seti 1 (0-6)" ve "Veri Seti 2 (7-14)" diye iki ayrı kaynağın elle birleştirilmiş hali; `roboflow.workspace: solarpanels-odahn`, `project: anomalies-detection-blv72`, `version: 14`, `license: Private`.
- `README.roboflow.txt`/`README.dataset.txt`: başka bir proje adresi (`universe.roboflow.com/solar-panel-defect-team-9/solar-panel-det`), "CC BY 4.0", "1857 görüntü", 640x640 stretch, kaynak görüntü başına 3 artırılmış sürüm (çevirme, kırpma, ±15° döndürme, parlaklık). Bu sayfaya WebFetch ile erişilemedi (doğrulanamadı).
- **Lisans çelişkisi:** README "CC BY 4.0", `data.yaml` "Private". Birleştirilmiş setin yeniden dağıtım hakkı belirsiz; repo herkese açık olduğundan ham görüntü/etiket repoya konmamalı (`data/` zaten git dışı).
- RGB sınıflar (Bird Drop, Dusty, Electrical Damage, Physical Damage, Snow, Defective, Non Defective) büyük olasılıkla Kaggle "Solar Panel Images" (pythonafroz) tarzı sınıflandırma setinden türemiş: benzer sınıf adları (Bird-drop, Clean, Dusty, Electrical-damage, Physical-damage, Snow-covered) [[HF veri notu, İ]](https://huggingface.co/spaces/Abs6187/TechTrident/blob/main/data/data_info.txt). Bu bir **çıkarım**; kesin eşleşme doğrulanamadı. SolarFCD makalesi bu setin lisansını "bilinmiyor, izin belirsiz" olarak işaretliyor ([arXiv 2604.23662 HTML](https://arxiv.org/html/2604.23662), [P]).
- 8 termal sınıfın (SingleHotSpot ... StringReversedPolarity) özgün kaynağı **bulunamadı**: bu sınıf adlarını içeren bir yayın/veri seti araması sonuçsuz kaldı. Termal kısmın bilinen açık setlerden türetilip türetilmediği kanıtlanamıyor.
- Yerel denetim: 9196 görüntü, 3115 kaynak gövde, 645 yakın kopya çifti (`outputs/reports/dataset_audit.md`, dal `claude/sad-margulis-eb217f`). 9196 artırılmış kopyaları içerir; bağımsız örnek sayısı daha düşüktür, genişletme hedefi buna göre değerlendirilmeli.

## 1. Aday açık veri setleri

### A. InfraredSolarModules (Raptor Maps)
- Kaynak: [GitHub README](https://github.com/RaptorMaps/InfraredSolarModules) [R]; ICLR 2020 AI4Earth atölyesi ([SlidesLive kaydı](https://slideslive.com/38926354/infrared-solar-module-dataset-for-anomaly-detection), yazar listesi doğrulanamadı).
- Lisans: **MIT** (README'de doğrulandı).
- Modalite/platform: kızılötesi; palet/radiometrik durumu ve çekim platformu README'de belirtilmemiş (doğrulanamadı).
- Çözünürlük: **24x40 px** modül kırpması, JPEG; GSD/irtifa yok.
- Etiket: yalnızca kırpma sınıfı (`module_metadata.json`).
- Sınıflar: Cell 1877, Cell-Multi 1288, Cracking 941, Hot-Spot 251 (ince film), Hot-Spot-Multi 247, Shadowing 1056, Diode 1499, Diode-Multi 175, Vegetation 1639, Soiling 205, Offline-Module 828, No-Anomaly 10000 (toplam 20006; README "20000" diyor).
- Eşlenebilirlik: Cell ~ SingleHotSpot, Cell-Multi ~ MultiHotSpot, Diode ~ SingleDiode/SingleByPassed (ayrım belirsiz), Diode-Multi ~ MultiDiode/MultiByPassed. Offline-Module modül düzeyi; StringOpenCircuit dizi düzeyi, **eşleme belirsiz**. Ters kutuplaşma karşılığı yok.

### B. PVF-10
- Kaynak: Wang ve ark., Applied Energy 376, 2024, DOI 10.1016/j.apenergy.2024.124187 ([IDEAS](https://ideas.repec.org/a/eee/appene/v376y2024ipas0306261924015708.html)) [H].
- Lisans/erişim: **doğrulanamadı** (sayfa veri deposu veya lisans vermiyor; ScienceDirect tam metni erişilemedi; indirme adresi bulunamadı).
- Modalite: UAV termal IR, 8 santralden. Bir sonraki çalışma 112x112 sürümünü kullanıyor ([arXiv 2607.09205](https://arxiv.org/html/2607.09205), [P]); GSD doğrulanamadı.
- Etiket: sınıflandırma kırpması. 5579 kırpma, 10 sınıf: substring open circuit, panel short circuit, string short circuit, debris covering, shadowed panel, bottom dirt, broken panel, junction box overheating, overheated cell, healthy. Sınıf başına sayı doğrulanamadı; bir kaynak "8k" diyor (çelişki).
- Eşlenebilirlik: substring open circuit ~ StringOpenCircuit (kısmi), overheated cell ~ SingleHotSpot. Erişim için yazarlara başvuru gerekebilir.

### C. sUAS Infrared Image Dataset for PV Module Fault Classification (Louisiana Üniv.)
- Kaynak: [Zenodo, DOI 10.5281/zenodo.20860870](https://zenodo.org/records/20860870) [R], yayın tarihi 25 Haziran 2026.
- Lisans: **CC BY 4.0**.
- Modalite: sUAS termal ortomozaikten; 8-bit gri (bir arama özetinde; sayfa sensör/irtifayı söylemiyor, doğrulanamadı).
- Çözünürlük: ortomozaik 3.13 cm/px.
- Etiket: ortomozaikten kırpılmış modüller, klasör = sınıf.
- Sınıflar: Cell 249, Multi-Cell 96, Open-Circuit Substring 26, Open-Circuit 431, Open-Circuit Multi-Substring 2, Short-Circuit Substring 15, Short Circuit 21, Normal 2835 (toplam 3675, sayfadaki sayılardan toplanarak türetildi).
- Eşlenebilirlik: Cell ~ SingleHotSpot, Multi-Cell ~ MultiHotSpot, Open-Circuit (Sub)string ~ StringOpenCircuit. Gri ve drone: alan olarak bize en yakın aday, ancak sayılar küçük.

### D. Alfaro-Mejía ve ark. (Universidad del Valle)
- Kaynak: [Data in Brief 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6811936/) [H]; [Mendeley, DOI 10.17632/82vzccxb6y.2](https://data.mendeley.com/datasets/82vzccxb6y/2).
- Lisans: CC BY 4.0 (Mendeley sayfası).
- Platform: DJI Matrice 100 + Zenmuse XT, 7.5-13 µm; uçuş yüksekliği panel tabanından 2.3-2.7 m.
- Çözünürlük: 336x256, JPG. Etiket: hücre düzeyi hotspot / snail trail / sağlam (renk şemasıyla; kutu dosyası yok, sınıf başı sayı verilmemiş).
- Boyut: 277 görüntü. Çok küçük ve çok alçak irtifa (bizim GSD'den çok farklı); bbox yeniden etiketlemesi gerekir.

### E. PVMD (Bello ve ark., TUT Güney Afrika)
- Kaynak: [Data in Brief 2024, PMC11683254](https://pmc.ncbi.nlm.nih.gov/articles/PMC11683254/) [H]; [Mendeley, DOI 10.17632/5ssmfpgrpc.1](https://data.mendeley.com/datasets/5ssmfpgrpc/1).
- Lisans: makale "erişim kısıtı yok" diyor, veri lisansı ayrıca belirtilmemiş; SolarFCD makalesi CC BY 4.0 yazıyor ([arXiv HTML](https://arxiv.org/html/2604.23662), ikincil).
- Platform: DJI Mavic 3 Thermal (640x512), 5 Eylül 2024; irtifa belirtilmemiş. Görüntüler 512x512x3'e kırpılmış (renk paletli).
- Etiket: klasör = sınıf, bbox yok. Sınıflar: Hotspots 350, Cracks 350, Shadings 300 (toplam 1000, **artırılmış görüntüler dahil**).
- Değerlendirme: yalnızca hotspot (+ çatlak) için küçük ek; bbox yok, artırılmış kopyalar var.

### F. Bird Droppings Thermal (TRSAI, Mısır)
- [Mendeley, DOI 10.17632/8sxfmrpfpv.1](https://data.mendeley.com/datasets/8sxfmrpfpv); CC BY 4.0; el tipi UTi165A, 160x120; 410 (v1) / 850 (v2) görüntü; etiket biçimi doğrulanamadı. Drone değil, düşük çözünürlük: ek değeri düşük.

### G. Raptor Maps hava IR çalışması (taksonomi referansı)
- [arXiv 2503.02128](https://arxiv.org/html/2503.02128v1) [P]: 6155 santral, 2.2-6.5 cm GSD, yatay kutu etiketi; sınıflar hotspot, multi-hotspot, diode bypass, single panel outage, string outage, misaligned. **Veri yayımı belirtilmemiş**; erişilemez. Yalnızca taksonomi referansı olarak değerli (Single/Multi ayrımı endüstride kullanılıyor).

### H. Roboflow Universe projeleri
- Örnekler: [hotspot-detection-in-solar](https://universe.roboflow.com/nepalianpr/hotspot-detection-in-solar) (204 görüntü), [AUS hotspot](https://universe.roboflow.com/american-university-of-sharjah/hotspot-detection-in-solar-panel) (~1000 görüntü) [K]. Lisans CC BY (arama özeti; tek tek doğrulanmalı). Termal/drone olup olmadığı **doğrulanamadı**. Tek sınıf "hotspot" (sınıf ayrımı yok), köken belirsiz.

### I. SolarFCD
- [arXiv 2604.23662](https://arxiv.org/html/2604.23662) [P], 4435 görüntü (3078 benzersiz), 4 kaba görüntü sınıfı. PVMD ve iki RGB setin derlemesi; "en kısıtlayıcı kaynak lisansı" geçerli. **Yeni bilgi içermez, kullanılmamalı.**

### Elenenler / erişilemeyenler
- Cvetek benzeri 4.3 M IR modül görüntülü çalışma ([arXiv 2106.07314](https://arxiv.org/abs/2106.07314)): 107842 modül, 10 anomali sınıfı; veri yayımı belirtilmiyor (doğrulanamadı).
- [arXiv 2111.11709](https://arxiv.org/abs/2111.11709): 640x512 radyometrik LWIR hotspot seti; veri bağlantısı yok.
- Not: Kaggle, figshare ve IEEE DataPort taraması kapsamlı değil; "bulunamadı" ifadesi "yok" demek değildir.

## 2. Uyum riskleri

### 2.1 Sınıflandırma kırpmaları -> tespit

- **Doğrudan kullanılamaz:** kırpmada konum bilgisi yok; kutuyu "tüm görüntü" yapmak, çok panelli ve küçük nesneli gerçek karelerle uyuşmaz (kısayol öğrenme riski; bizim çıkarım).
- **24x40 px (A):** 640'a ölçeklenince dokusuz; yalnızca (i) ikinci aşama modül sınıflandırıcı (YOLO tespit, kırpma, sınıflandırıcı) veya (ii) kolaj üretimi için anlamlı.
- **Kolaj/ortomozaik yaklaşımı:** kırpmaları sentetik ızgara görüntüye yerleştirip kutuları otomatik üretmek mümkün; PV'de başarısını gösteren kaynak bulunamadı (doğrulanamadı). Valid/test yalnızca gerçek görüntülerle olmalı.
- **C:** kırpmalar ortomozaikten; sayfada ham ortomozaik görünmüyor, kutu üretimi mümkün değil.

### 2.2 Alan kayması

- **Palet/radiometri:** bizim termal görüntülerin çoğu gri (denetim: train 6372 gri, 985 RGB). Renk paletli setler (D, E) griye çevrilince palet bilgisi kaybolur; radiometrik veri hiçbir adayda doğrulanamadı.
- **İrtifa/GSD:** D ~2-3 m; C 3.13 cm/px; G 2.2-6.5 cm; bizim DJI uçuşu için GSD `ucus-planlayici` kararına bağlı. Nesne piksel boyutu eşleşmeden ölçek kayması yüksek.
- **Sensör çözünürlüğü:** 160x120 (F), 336x256 (D), 640x512 (E); mevcut set 640x640'a stretch.
- **Etiket tanımı:** A'da "Diode" etkin bypass diyodu, genelde modülün ~1/3'ü ([README](https://github.com/RaptorMaps/InfraredSolarModules)); bizim SingleDiode ile SingleByPassed farkı belgelenmemiş. Tanım netleşmeden eşleme yapılamaz.

### 2.3 Çapraz-veri kopyası / sızıntı

- Roboflow termal kısmının bilinen açık setlerden derlenmiş olması **mümkün ama kanıtlanamadı** (kaynak belirsiz, lisans `Private`). A (modül kırpması) ile birebir eşleşme olasılığı düşük; kaynak kareler bizim görüntülerle örtüşebilir. C, D, E tam kare/kırpma olduğundan örtüşme olasılığı daha yüksek (tahmin).
- **Kontrol yöntemi (indirme sonrası, kullanıcı onayıyla):** (1) `scripts/audit_and_fix_dataset.py` içindeki dHash (<=4, çevirme duyarsız) + NCC (>=0.85) hattını aday set ile mevcut set arasında çalıştır; (2) bizim kutu kırpmalarını adayın kırpma boyutuna (24x40, 112x112) küçültüp pHash ile karşılaştır; (3) eşleşen aday görüntüleri çıkar; (4) aday setten gelen veriyi `kaynak` alanıyla etiketle ve valid/test'e **hiç** koyma; aynı gruplama kuralını (grup bazlı bölme) uygula.
- Set içi kopyalama zaten yüksek (645 çift, 401'i farklı gövdeler arası); yeniden bölme bunu giderdi, yeni veri aynı kuralla eklenmeli.

## 3. Alternatifler

1. **Sınıf birleştirme:** ek veri gerektirmez. Yerel sayılar (`dataset_audit.md`): Single+Multi hotspot (7636+5297) = 12933; Diode grubu 1982+1047 = 3029; ByPassed grubu 3252+391 = 3643; Diode+ByPassed = 6672. Endüstri taksonomisi Single/Multi'yi ayrı tutuyor ([arXiv 2503.02128](https://arxiv.org/html/2503.02128v1)); birleştirme bilgi kaybıdır. ByPassed/Diode birleştirmesi etiket tanımına bağlı bir varsayım.
2. **Sentetik veri:** MDPI Energies 18(4):776'da PV arıza sınıflandırmasında difüzyon tabanlı artırmanın GAN ve geometrik artırmadan iyi olduğu bildiriliyor ([MDPI](https://www.mdpi.com/1996-1073/18/4/776); tam metne erişilemedi, 403; yalnızca arama özeti [İ]). **Sınıflandırma çalışması**; YOLO tespiti için eşleşmiş taban çizgili karşılaştırma bulunamadı. Sentetik veri yalnızca eğitim bölmesine girmeli.
3. **Standart artırma:** bir YOLOv8 çalışması 2000 IR görüntüyü 3600'e artırıp mAP@0.5 = 0.7628 bildiriyor ([Uludağ yayını, İ](https://avesis.uludag.edu.tr/yayin/b654d7d4-49c2-446e-81f3-8acf02a585be/anomaly-detection-in-photovoltaic-panels-via-yolov8-based-deep-learning-framework); tam metin doğrulanamadı). Mevcut set zaten 3x artırılmış; ek marjinal kazanç düşük olabilir (tahmin).
4. **Yarı-otomatik etiketleme:** termal PV'ye özel sahte-etiket/aktif öğrenme çalışması bulunamadı. EL görüntülerinde PV-S3, %20 etiketle denetimli tabanı geçip etiketleme maliyetini ~%80 azaltıyor ([arXiv 2404.13693](https://arxiv.org/abs/2404.13693v4), [P], farklı modalite). Pratik yol: mevcut YOLO ile kendi drone görüntülerimizi ön-etiketleyip insan düzeltmesi.

## 4. Seçenekler ve öneri

Hiçbir açık sette **StringReversedPolarity** ve belirgin **ByPassed** karşılığı bulunamadı. Açık setlerin çoğu sınıflandırma kırpması; bbox veren yok (G yayımlanmamış).

**S1: Yalnızca sınıf birleştirme.** Ek veri yok. Artı: lisans/sızıntı riski yok, hemen uygulanır. Eksi: bilgi kaybı; sınıf tanımı kararı gerekir. Kazanım: yeni örnek yok; birleşik sınıflar Diode+ByPassed 6672, Hotspot 12933. StringOpenCircuit (1266) ve ReversedPolarity (124) zayıf kalır.

**S2: S1 + açık kırpma setleriyle ikinci aşama sınıflandırıcı.** Kaynaklar: A (MIT), C (CC BY), E (belirsiz lisans). Artı: yapıya uygun, lisanslar nispeten açık. Eksi: iki aşamalı mimari değişikliği; alan kayması (24x40, palet); A'da ByPassed/ReversedPolarity yok; E'de artırılmış kopyalar. Kazanım (tespit instance'ı değil, **kırpma**): A Cell+Cell-Multi 3165, Diode 1499, Diode-Multi 175; C open-circuit ~459 (431+26+2); E hotspot en fazla 350.

**S3: S1 + kendi drone verisi (yarı-otomatik etiketleme).** Artı: alan eşleşmesi, eksik sınıflara hedefli. Eksi: uçuş/zaman gerekir. Kazanım ölçülemez (veri henüz yok).

**Öneri (karar kullanıcıya ait):** S1'i başlangıç al; ikinci aşama istenirse yalnızca C ve A'yı sızıntı kontrolünden sonra kullan; D ve E öncelikli değil. ReversedPolarity ve MultiByPassed için açık veri bulunamadığından bu sınıflar birleştirilmeli ya da S3 ile toplanmalı; açık veriyle bu sınıfların sayısını artırma beklentisi gerçekçi değil.

## 5. Açık sorular

(a) Diode ile ByPassed tanım farkı (Roboflow etiketçisi). (b) PVF-10 herkese açık mı (yazarlara sorulmalı). (c) Roboflow termal kısmının kökeni. (d) Birleştirilmiş setin lisansı (Private mi CC BY 4.0 mı).
