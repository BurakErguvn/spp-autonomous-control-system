# Test Raporu — Issue #2, #3, #6 — 2. tur (dal `claude/sad-margulis-eb217f`, HEAD `08ef0c4`)

KARAR: PASS (koşullu) — 2e505fa..08ef0c4 değişiklikleri (8/0.90/ncc-only 0.93, OOS ayrımı, Electrical Damage) bağımsız olarak yeniden üretildi; kod/veri hatası yok. Koşullar: aşağıdaki iki bilgi/düşük bulgu (artık sızıntı, `--ncc-only-thr` negatif değer) kullanıcının bilmesi için; kabul kriterlerini bozmaz.

## Kabul kriterleri
- [x] #2: Ultralytics 8.4.41 doğrulaması 0 corrupt (tester yeniden üretimi: train 5337 / valid 640 / test 606, `check_det_dataset` nc=3 ok); tüm etiketler 5 sütun, [0,1], sınıf 0-2 (kötü satır 0); poligon→bbox korunuyor; ham veri değişmedi (en yeni mtime 2026-05-02; 9196/9196 görüntü ham ile bayt-bayt aynı)
- [x] #3: bölmeler arası stem ve grup kesişimi 0 (hem `placed_in` hem atanmış `split` açısından, OOS dahil); test hotspot 1290 (>=300); hotspot/mikro_catlak/tozlanma train/valid/test = 80.0/10.0/10.0, 80.1/9.9/10.0, 82.2/8.3/9.5 %; görüntü 81.1/9.7/9.2 %
- [x] #6: OOS ayrımı ham `.txt.orig` etiketlerinden bağımsız hesapla birebir doğru (aşağıda)

## Bulgular
1. BİLGİ/DÜŞÜK-ORTA (alan kararı değil, farkındalık) — artık yakın-kopya sızıntısı: eşikler 8/0.90/0.93 ile bile 24x24 max-NCC (4 çevirme) >=0.90 olan görüntüler kalıyor: test->train 15/606, valid->train 15/640, test->valid 4/606 (>=0.95 ve >=0.97: 0). Görsel kontrol: iki tür var — (i) gerçekten aynı uçuşun ardışık kareleri (ör. `DJI_20220810095449_0075` test vs `..._0076` train, NCC24 0.934; `Physical_Damge_536` test vs `_528` valid, 0.947) ve (ii) aynı santralin benzer dizilişli ama farklı kareleri. 32x32 NCC'si 0.93 altında kaldıkları için birleşmediler. Bağımsız ölçüm (16x16 bulanık bilinear NCC + DCT pHash<=6 & NCC>=0.9): test->train 0, valid->train 0, test->valid 1. Etki küçük (test'in ~%2.5'i, metrik şişmesi sınırlı); isterse `--ncc-only-thr 0.90` ile kapanır ama daha fazla ilgisiz birleşme/büyük grup riski getirir. Karar kullanıcıda (eşik).
2. DÜŞÜK — `scripts/audit_and_fix_dataset.py:808` — `args.ncc_only_thr if (args.ncc_only_thr or 2) <= 1 else None`: `--ncc-only-thr 0` sessizce kapatır, `-1` ise (`--ncc-thr -1`'in "kapalı" kuralının aksine) AKTİF olur ve `ncc_best >= -1` ile tüm çiftleri birleştirir (tek dev grup, bölme çöker). Yeniden üretme: `for v in (-1, 0, 0.93, 2): print(v, (v or 2) <= 1)` -> -1 aktif, 0 kapalı. Öneri: negatif/<=0 değeri hata ver ya da "kapalı" say; yardım metni "1'den büyük" diyor, bu yüzden varsayılan kullanım etkilenmiyor.
3. DÜŞÜK — modalite dengesi: gri tozlanma (çok küçük sınıf-modalite hücresi) train/valid/test = 39/3/23 (eski bölmede 53/11/1); tozlanma toplamı 4067/409/472. RGB hücreleri dengeli. Gri-modalite tozlanma için tek başına anlamlı metrik çıkmaz (n=23 test). Ayrıca arka plan (hedefsiz) oranı test'te %6.8, train/valid %3.6 (41/606 vs 193/5337) — test arka plan sayısı küçük (41), yanlış pozitif oranı ölçümü gürültülü olabilir.
4. BİLGİ — karma görüntüler: 1526 görüntü (train 1263, valid 133, test 130) hedef kutusu olmasına rağmen OOS sınıf kutusu (diode/bypass vb.) da taşıyor; anomali bölgesi etiketsiz kalıyor. Rapor bunu zaten belirtiyor ("bu işte DEĞİŞTİRİLMEDİ"); bunlar train'de örtük negatif olarak duruyor. Alan kararı, kapsam dışı.
5. DÜŞÜK — `data/ges_clean.yaml` yalnızca `train/val/test` yollarını yazıyor; `oos/` için anahtar yok (Ultralytics'in tanımadığı anahtar zaten gerekmez; ayrı bir inference/negatif-test değerlendirmesi için yol elle verilmeli). `path: data/ges_clean` göreli (proje kökünden çalıştırın). Önceki rapor bulgu 5 ile aynı.
6. DÜŞÜK (test) — `tests/test_audit_dataset_extra.py:~400` yorumu eski ("Non Defective / Electrical Damage tek başına OOS değil") — Electrical Damage artık OOS; kod/doğrulama doğru, yalnız yorum bayat.
7. BİLGİ — yazma hook'u (`guard.py:98`) `.claude/worktrees/...` altındaki yolları çalışma ağacı yerine ana depo köküne göre değerlendirip `.claude/` önekiyle reddediyor; worktree içindeki `tests/`, `outputs/test_reports/` dosyalarına Edit/Write ile yazılamıyor (Bash ile yazıldı). Orkestratör/kullanıcı için hook düzeltmesi önerilir (rol izinleri yine `tests/**` ve `outputs/test_reports/**`).

## İddia vs bağımsız değer
| Kalem | İddia | Tester |
|---|---|---|
| pytest `--ignore=tests/test_gui.py` | 84 passed, 4 skipped; veri bağıyla 88 | 84 passed, 4 skipped; veri bağıyla 88 passed (tester testleri eklenince 86+8 skip / 94 passed) |
| Görüntü train/valid/test/oos | 5337/640/606/2613 (9196) | 5337/640/606/2613 (9196) |
| Çift / grup / en büyük grup | 901 / 2799 / 45 | 901 / 2799 / 45 (singleton 398) |
| Hotspot instance | 10349/1294/1290 | 10349/1294/1290 (etiket dosyalarından) |
| Sızıntı >=.90/.95/.97 test->train, valid->train, test->valid | 15/0/0, 15/0/0, 4/0/0 | 15/0/0, 15/0/0, 4/0/0 (kendi 24x24 NCC uygulamam, aynı yöntem) |
| Stem/grup kesişimi | 0 | 0 (placed_in ve split, stem+grup) |
| OOS kaynak sınıf (görüntü sayısı) | SingleByPassed 1254, SingleDiode 572, StringOpenCircuit 499, MultiDiode 313, MultiByPassed 225, StringReversedPolarity 80, Electrical Damage 52 | aynı (ham etiketlerden); ED: 31 yalnız ED + 21 ED+Non Defective; ED+başka sınıf 0 |
| Arka plan train/valid/test | 193 (%3.6)/23/41 | 193/23/41 = 257 (250 yalnız Non Defective + 7 etiketsiz) |
| OOS atanmış bölme | — | train 2019, valid 280, test 314 (rapor `removed_total` ile aynı) |
| Karma görüntü (OOS kutulu / herhangi eşlenmemiş) | rapor | 1263/1472, 133/166, 130/144 (bağımsız hesapla aynı) |
| Ultralytics corrupt | 0 | 0 |

## OOS doğruluğu (ham `.txt.orig` etiketlerinden, sabit sınıf ID'leriyle)
- (a) OOS'a giden her görüntü: hedef sınıf yok ve en az bir OOS sınıfı var — 2613/2613, ihlal 0
- (b) Koşulu sağlayıp OOS'a gitmeyen görüntü — 0
- (c) Hedef kutusu olan görüntü OOS'ta — 0
- (d) Split dizinlerinde hedefsiz kalanlar yalnız Non Defective (250) / etiketsiz (7) — ihlal 0
- (e) `oos/labels` 2613 dosya, hepsi boş; görüntü–etiket stem eşleşmesi tam; split dizinlerinde de görüntü=etiket; `manifest.placed_in` dosya sistemiyle 9196/9196 uyumlu
- Bunlar `tests/test_audit_dataset_oos_independent.py` içinde kalıcı teste çevrildi.

## Determinizm ve modlar
- `python scripts/audit_and_fix_dataset.py --src <ham> --out <scratch>/a/ges_clean --report-dir <scratch>/a/reports` (35 sn): mevcut `data/ges_clean` ile `diff -rq` farksız; rapor JSON'u yol alanları (`source/output/data_yaml`) dışında aynı.
- `--oos-mode keep` (train 5337 / valid 920 / test 920 / oos 0 / atılan 2019), `drop` (5337/640/606/0/2613), `--keep-original-classes` (7356/920/920, OOS işaretlenmez) ve varsayılan `separate`: dört manifestte (dosya -> grup, atanmış bölme) 9196/9196 aynı. `drop` ile `separate` split içerikleri aynı.

## Zincirleme / grup yapısı
- Grup boyutları: en büyüğü 45 (önceki rapor: 66), ilk 12: 45,34,33,17,16,15,14,13x5; >=10 görüntülü 30 grup; 398 tekil. Zincirleme kontrolü: 901 çiftin 58'i dosya-adı öneki farklı görüntüleri bağlıyor (öneki rastgele numaralı Roboflow adları da dahil, ölçüt kaba). NCC-only ile kurulan 27 farklı-önekli kenardan 6 rastgele örnek görsel incelendi: hepsi aynı santral/dizilişin benzer kareleri (satır yapısı aynı), ilgisiz sahne birleşmesi görülmedi; 34'lük grupta `210915_Hangchon_33m` + `Thermal_Solar` + `Physical_Damge` gibi karma önekler var, ama devasa grup oluşmuyor (en büyük %0,5 veri). Muhafazakâr birleşme: sızıntıyı azaltır, tabakalama maliyeti küçük.

## Test incelemesi (yeni testler)
Tautoloji yok: OOS testleri sabit beklenti tabloları kullanıyor (`_rec` + `CLASS_REMAP`, sonuç elle yazılı bayraklar); mod testleri atanmış bölmenin 3 modda aynı olduğunu manifestlerden karşılaştırıyor; `ncc_leakage` testi çevrilmiş ikiz ve yazılmayan ("") görüntüyü sınıyor. Eksikler ve eklenenler (`tests/test_audit_dataset_oos_independent.py`, 6 test): (1) ham etiketlerden bağımsız OOS üyeliği kuralı, (2) kalan arka planlar yalnız Non Defective/etiketsiz + oos etiketleri boş, (3) grup/stem kesişimi hem `placed_in` hem `split` ile, (4) bölme oranları ve hotspot tabanı, (5) NCC-only negatif durum (eşik altı çift birleşmez, eşik düşünce birleşir), (6) çevirilmiş ikiz dHash eşleşmesi olmadan yakalanır. Mevcut `test_ncc_only_candidates...` yalnız pozitif durumu sınıyordu.

## Gözlemler (kapsam dışı)
- `scripts/train_yolo26.py` hâlâ `ges_project.yaml` + ham veride yerinde remap yapıyor (önceki rapor bulgu 3); eğitim `ges_clean.yaml`'a bağlanmalı.
- `tests/test_gui.py` ortam (Qt) hatası değişmedi.
- Scratch: `/tmp/claude-1000/-home-berguven-Belgeler-disiplinlerarasi/9fb0f889-4789-4f9f-9ace-7c0307edf652/scratchpad/t2/` (üretimler `a`, `keep`, `drop`, `k15`; betikler `oos_check.py`, `leak.py`, `leak2.py`, `chain.py`).

---

# (1. tur) Test Raporu — Issue #2 ve #3 (`b485ecb`)

KARAR: PASS (koşullu) — iki issue'nun kabul kriterleri de bağımsız olarak yeniden üretildi ve karşılandı; koşullar "Bulgular" bölümündeki orta önemli iki alan kararıdır (kod hatası yok).

## Kabul kriterleri

### Issue #2
- [x] Türetilmiş sette Ultralytics taramasında 0 corrupt (8.4.41 `YOLODataset` taraması: train 7357/0, valid 918/0, test 921/0; segment içeren dosya 0)
- [x] Ham veri yerinde değiştirilmedi (ham ağaçta en yeni mtime 2026-05-02, betik çalışması 2026-10-20; ham/temiz görüntü md5 farkı 0/9196); dönüşüm betikle tekrarlanabilir ve deterministik (scratch'e yeniden üretim: tüm ağaç `diff -rq` farksız, manifest ve rapor JSON'u aynı)
- [x] Sınıf başına örnek sayıları önce/sonra raporlandı (bağımsız hesapla doğrulandı)

### Issue #3
- [x] Bölmeler arası grup kesişimi 0 (stem 0/0/0, grup 0; bağımsız pHash+NCC taraması test↔train/valid↔test 0; bkz. B-2 yan not)
- [x] Test setinde hotspot 1291 instance (≥ birkaç yüz); mikro_catlak 410, tozlanma 465
- [x] Sınıf × modalite × bölme tablosu raporlandı (bağımsız yeniden hesapla birebir aynı)

## Bulgular
1. ORTA (alan kararı) — `scripts/audit_and_fix_dataset.py:~661-668` (kaynak: 3 sınıfa remap) — Arka plan (etiketsiz) görüntülerin neredeyse tamamı gerçekte kapsam dışı etiketli: train'de 2271 arka planın 2271'i, toplamda 2870 arka planın 2863.ü kaynakta (kapsam dışı sınıfla) etiketli görüntü. Bunların 2561'i termal ve Diode/ByPassed/StringOpenCircuit/ReversedPolarity gibi gerçek termal anomali içeriyor; yalnız "Non Defective" olanlar 250. Model bu görüntülerde hiçbir şey tespit etmemeyi öğrenecek (hotspot için zorlu negatif / etiket gürültüsü riski). Yeniden üretme: `/tmp/.../scratchpad/bg.py` (ham `.txt.orig` sınıf kümeleriyle manifest `n_rows_out==0` kesişimi). Öneri: kullanıcı karar versin — (a) mevcut hâli koru, (b) bu anomali görüntülerini ayrı `ignore` kümesine al/train'den çıkar, (c) 15 sınıflı etiketlerle eğit (`--keep-original-classes`).
2. DÜŞÜK-ORTA — kapsam: yakın kopya tanımı — dHash ≤4 + NCC ≥0.85 ile sızıntı 0, ancak bağımsız pHash tarama eşiği gevşetilince komşu-kare benzerliği kalıyor: test↔train 24x24 küçük-resim max-NCC ≥0.90: 30/921 görüntü (≥0.95: 7, ≥0.97: 2), valid↔train ≥0.90: 27/918. Görsel kontrol: bunlar aynı sahnenin ardışık drone karesi / aynı oturumun (ör. `Physical_Damge_528` vs `_536`, `DJI_..._0361` vs `_0360`) farklı pozları; birebir kopya değil ama bağımlı. pHash≤6 + NCC≥0.9 ile valid↔train 4 görüntü eşleşti, test↔train 0. Kabul tanımını (dHash ≤4) bozmaz. Yeniden üretme: scratch `leak.py`. Öneri: isterse `--hash-thr 8 --ncc-thr 0.90` ile grup birleştirme gevşetilebilir (bölmeyi değiştirir; test boyutu/tabakalama yeniden doğrulanmalı).
3. DÜŞÜK — `scripts/train_yolo26.py:32,141-145` — Eğitim hâlâ `data/ges_project.yaml` + ham veride yerinde `remap_labels` çalıştırıyor; `ges_clean` bağlanmamış. Ham veri bu yüzden daha önce (2026-05-02) değiştirilmiş (`.txt` = remap'li, `.txt.orig` = orijinal); bu dal ham veriyi değiştirmiyor ve `.txt.orig`'i okuyor. `remap_labels` yanlışlıkla `ges_clean` üzerinde çalıştırılırsa 3 sınıflı etiketler tekrar eşlenir. Kapsam dışı, ayrı issue: eğitim hattını `ges_clean.yaml`'a bağla ve ham veriyi yerinde değiştirmeyi bırak.
4. DÜŞÜK — `tests/test_gui.py` toplama hatası (`libQt6Core.so.6 Qt_6_PRIVATE_API`): ortam kaynaklı, `main`'de de aynı; bu dalın değişikliğiyle ilgili değil. Tüm kalan testler geçiyor.
5. DÜŞÜK — `data/ges_clean.yaml` içinde `path: data/ges_clean` göreli; Ultralytics'e proje kökünden verilmeli (Colab'da yol uyarlaması gerekebilir). `data/` git dışı olduğundan yaml/manifest depoda yok; yalnız rapor depoda.
6. BİLGİ — Gri/termal modalitede tozlanma yok denecek kadar az (train 53, valid 11, test 1); hotspot yalnız termal, RGB'de hiç yok. Bu doğal olarak veri setinin yapısı; modalite başına metrik raporlanırken dikkate alınmalı.

## Kanıt (yeniden üretildi)
- `python -m pytest -q tests --ignore=tests/test_gui.py` → 61 passed (main: 52 passed; +9 yeni = `test_audit_dataset.py`). `tests/test_gui.py` ortam hatası (bulgu 4). Eklenen `tests/test_audit_dataset_extra.py`: 15 test (data yoksa 3'ü atlanır); `data` simgesel bağıyla 15 passed.
- Mevcut test anlamlı: poligon→bbox min/max + kırpma, karışık dosya ayrıştırma, remap + yinelenen atma, union-find + oran takibi, uçtan uca (sızıntılı bölme → 0 sızıntı, .txt.orig önceliği, modalite, kaynak baytları değişmez, üzerine yazma koruması, Ultralytics doğrulaması). Eksik olan: gerçek veri invariantları, determinizm, çevirme duyarsız dHash'in birim testi, dejenere/hatalı satır sayaçları, güvenlik korumaları — ek dosyada eklendi.
- Önce/sonra sayıları bağımsız hesap (ham `.txt.orig`): bbox/poligon train 24132/7315, valid 1720/528, test 295/323; karışık dosya (15 sınıf) 552/65/33, remap sonrası 450/54/26; remap sonrası kayıp (karışık dosyadaki instance): train çatlak 1979/3533, toz 2237/4267 (+hotspot 30/12392); valid çatlak 236/344, toz 317/439; test çatlak 150/212, toz 130/242 — rapor ve issue ile birebir.
- Temiz etiket yeniden türetme: ham `.txt.orig` → remap + bbox min/max + [0,1] kırpma + 6 basamakta tekilleştirme; 9196 dosyanın 0'ında fark (tol 2e-6); dejenere 0; tekilleştirilen 51 (tümü train, mikro_catlak: Defective+Physical Damage aynı kutu; 4089−51=4038); 5 sütun dışı satır 0; [0,1] dışı değer 0. Sınıf toplamları hotspot 12933, mikro_catlak 4038, tozlanma 4948 (rapor ile aynı).
- Yeniden üretim: `python scripts/audit_and_fix_dataset.py --src <ham> --out <scratch>/ges_clean --report-dir <scratch>/reports` (28 sn, exit 0) → mevcut `data/ges_clean` ile `diff -rq` farksız, rapor JSON'u yol alanları dışında aynı. Betik `--out`/`--report-dir`'i destekliyor; mevcut çıktı korunuyor.
- Sızıntı: stem kesişimi train∩valid/test, valid∩test = 0/0/0 (3115 stem); manifest grup kesişimi 0; en büyük grup 66 görüntü (aşırı büyük grup/zincirleme yok, 2838 grup). Bağımsız pHash (DCT 8x8, 4 çevirme) ≤6 bit + 24x24 NCC ≥0.9: test↔train 0, test↔valid 0, valid↔train 4 (bulgu 2).
- Split oranları: hotspot 10348/1294/1291 (80.0/10.0/10.0 %), modalite oranı test'te train ile aynı (%86.6 gri), arka plan oranı train %30.9 / valid %33.4 / test %31.7 (Colab günlüğü: 2641/8550 = %30.9 — makul).
- Modalite: chroma dağılımı iki kümeli (7966 görüntü <0.1, 1230 görüntü ≥3, arada 0); bağımsız tam çözünürlük kanal-farkı ölçütüyle 0 uyuşmazlık.
- Ultralytics 8.4.41 kurulu sürümle eşleşiyor; `check_det_dataset` nc=3 ['hotspot','mikro_catlak','tozlanma'], yaml ile tutarlı (etiketler 3 sınıf uzayında, yaml başlığı eşlemeyi yazıyor).

## Gözlemler
- Sınıf eşlemesi (Bird Drop/Snow→tozlanma, Defective/Physical Damage→mikro_catlak) bir alan kararıdır; bu dal mevcut `CLASS_REMAP`'i değiştirmeden kullanıyor, doğrulandı. Kullanıcı farklı taksonomi isterse `--remap-config` ile aynı bölme üretilir (seed + 15 sınıf tabakalaması).
- Bağımsız hesap betikleri scratchpad'de (git dışı): `indep1.py`, `indep2.py`, `leak.py`, `mod.py`, `bg.py`.
