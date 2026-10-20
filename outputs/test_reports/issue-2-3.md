# Test Raporu — Issue #2 ve #3 (dal `claude/sad-margulis-eb217f`, `b485ecb`)

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
1. ORTA (alan kararı) — `scripts/audit_and_fix_dataset.py:~661-668` (kaynak: 3 sınıfa remap) — Arka plan (etiketsiz) görüntülerin neredeyse tamamı gerçekte kapsam dışı etiketli: train'de 2271 arka planın 2271'i, toplamda 2870 arka planın 2819'u kaynakta etiketi olan görüntü. Bunların 2561'i termal ve Diode/ByPassed/StringOpenCircuit/ReversedPolarity gibi gerçek termal anomali içeriyor; yalnız "Non Defective" olanlar 250. Model bu görüntülerde hiçbir şey tespit etmemeyi öğrenecek (hotspot için zorlu negatif / etiket gürültüsü riski). Yeniden üretme: `/tmp/.../scratchpad/bg.py` (ham `.txt.orig` sınıf kümeleriyle manifest `n_rows_out==0` kesişimi). Öneri: kullanıcı karar versin — (a) mevcut hâli koru, (b) bu anomali görüntülerini ayrı `ignore` kümesine al/train'den çıkar, (c) 15 sınıflı etiketlerle eğit (`--keep-original-classes`).
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
