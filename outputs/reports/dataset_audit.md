# Veri Seti Denetim Raporu

Kaynak: `data/SOLAR PANEL DET.v1i.yolo26` → Çıktı: `data/ges_clean` (YAML: `data/ges_clean.yaml`)

Otomatik üretildi: `scripts/audit_and_fix_dataset.py`. Parametreler: `{"ratios": [0.8, 0.1, 0.1], "seed": 42, "hash_thr": 8, "ncc_thr": 0.9, "ncc_only_thr": 0.93, "gray_thr": 1.0, "oos_mode": "separate", "oos_classes": ["MultiByPassed", "MultiDiode", "SingleByPassed", "SingleDiode", "StringOpenCircuit", "StringReversedPolarity", "Electrical Damage"], "keep_original_classes": false}`

## 1. Etiket dönüşümü (poligon → bbox)

| Kaynak bölme | bbox satırı | poligon satırı (çevrildi) | dejenere | yinelenen | yinelenen (remap sonrası) | hatalı | karışık dosya (15 sınıf) | karışık dosya (remap sonrası) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 24132 | 7315 | 0 | 0 | 51 | 0 | 552 | 450 |
| valid | 1720 | 528 | 0 | 0 | 0 | 0 | 65 | 54 |
| test | 295 | 323 | 0 | 0 | 0 | 0 | 33 | 26 |

Karışık dosyalarda Ultralytics tüm satırları poligon sayar: 8.4.x'te 5 sütunlu bbox satırları iki nokta olarak okunup bozuk kutuya dönüşür, eski sürümlerde dosya düşürülür. Temiz veri setinde tüm satırlar 5 sütunludur.

## 2. Gruplama ve sızıntı

- 9196 görüntü, 3115 kaynak gövdesi, 2799 grup
- 901 yakın kopya çifti (dHash ≤ 8, çevirme duyarsız, NCC ≥ 0.9; ek NCC-tabanlı aday ≥ 0.93); 489 tanesi farklı gövdeler arasında
- En büyük grup: 45 görüntü

| Ölçüt | Önce (Roboflow bölmesi) | Sonra (yeni bölme) |
|---|---:|---:|
| Ortak gövde train-valid | 72 | 0 |
| Ortak gövde train-test | 17 | 0 |
| Ortak gövde valid-test | 8 | 0 |
| Ortak grup train-valid | 140 | 0 |
| Ortak grup train-test | 45 | 0 |
| Ortak grup valid-test | 20 | 0 |
| Bölmeler arası yakın kopya çifti | 212 | 0 |
| Train'de eşi olan test görüntüsü | 46 / 93 | 0 / 920 |

Bağımsız ölçüt: 24x24 küçük resim max-NCC (4 çevirme); ilk bölmedeki görüntülerden, ikincideki en benzeriyle NCC eşiğini aşanların sayısı (gruplama 32x32 kullandığı için bağımsızdır; yazılan görüntüler üzerinden).

| Bölme çifti | ≥0.90 önce | ≥0.90 sonra | ≥0.95 önce | ≥0.95 sonra | ≥0.97 önce | ≥0.97 sonra |
|---|---:|---:|---:|---:|---:|---:|
| test-train | 36/93 | 15/606 | 31/93 | 0/606 | 31/93 | 0/606 |
| valid-train | 118/553 | 15/640 | 89/553 | 0/640 | 84/553 | 0/640 |
| test-valid | 13/93 | 4/606 | 12/93 | 0/606 | 12/93 | 0/606 |

## 3. Bölme boyutları ve modalite

| Bölme | Önce gri | Önce RGB | Sonra gri | Sonra RGB | Sonra arka plan |
|---|---:|---:|---:|---:|---:|
| train | 7473 | 1077 | 4393 | 944 | 193 |
| valid | 453 | 100 | 514 | 126 | 23 |
| test | 40 | 53 | 492 | 114 | 41 |

## 4. Sınıf × modalite × bölme (instance)

**Hedef sınıflar — önce (Roboflow bölmesi)**

| Sınıf | train gri | valid gri | test gri | train RGB | valid RGB | test RGB | Toplam |
|---|---:|---:|---:|---:|---:|---:|---:|
| hotspot | 12392 | 532 | 9 | 0 | 0 | 0 | 12933 |
| mikro_catlak | 1398 | 174 | 88 | 2084 | 170 | 124 | 4038 |
| tozlanma | 53 | 9 | 3 | 4214 | 430 | 239 | 4948 |

**Hedef sınıflar — sonra (yeni bölme)**

| Sınıf | train gri | valid gri | test gri | train RGB | valid RGB | test RGB | Toplam |
|---|---:|---:|---:|---:|---:|---:|---:|
| hotspot | 10349 | 1294 | 1290 | 0 | 0 | 0 | 12933 |
| mikro_catlak | 1289 | 211 | 160 | 1947 | 188 | 243 | 4038 |
| tozlanma | 39 | 3 | 23 | 4028 | 406 | 449 | 4948 |

**Orijinal 15 sınıf — yeni bölme**

| Sınıf | train gri | valid gri | test gri | train RGB | valid RGB | test RGB | Toplam |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bird Drop | 3 | 0 | 11 | 1667 | 118 | 143 | 1942 |
| Defective | 301 | 58 | 32 | 1356 | 133 | 162 | 2042 |
| Dusty | 31 | 3 | 12 | 1406 | 170 | 176 | 1798 |
| Electrical Damage | 9 | 0 | 0 | 273 | 49 | 39 | 370 |
| Non Defective | 19 | 10 | 0 | 2939 | 367 | 360 | 3695 |
| Physical Damage | 1037 | 153 | 128 | 593 | 55 | 81 | 2047 |
| Snow | 5 | 0 | 0 | 955 | 118 | 130 | 1208 |
| MultiByPassed | 95 | 17 | 6 | 0 | 0 | 0 | 118 |
| MultiDiode | 301 | 73 | 37 | 0 | 0 | 0 | 411 |
| MultiHotSpot | 4240 | 531 | 526 | 0 | 0 | 0 | 5297 |
| SingleByPassed | 941 | 98 | 104 | 0 | 0 | 0 | 1143 |
| SingleDiode | 878 | 91 | 68 | 0 | 0 | 0 | 1037 |
| SingleHotSpot | 6109 | 763 | 764 | 0 | 0 | 0 | 7636 |
| StringOpenCircuit | 165 | 16 | 20 | 0 | 0 | 0 | 201 |
| StringReversedPolarity | 27 | 4 | 6 | 0 | 0 | 0 | 37 |

## 4b. Kapsam dışı termal anomali arka planları (OOS)

- Mod: `separate` — bölme tüm görüntülerle yapıldı, filtre bölmeden SONRA uygulandı
- Çıkarma kümesi (kaynak sınıflar): Electrical Damage, MultiByPassed, MultiDiode, SingleByPassed, SingleDiode, StringOpenCircuit, StringReversedPolarity
- Kural: remap sonrası hedef kutusu kalmayan ve bu sınıflardan birini içeren görüntü. Etiketsiz / yalnız Non Defective arka planları ve hedef kutusu olan karma görüntüler korunur; Electrical Damage (+ Non Defective) görüntüleri OOS'a gider.
- Yazılan: oos=2613, atılan (yazılmayan)=0

| Atanmış bölme | gri | RGB | Toplam |
|---|---:|---:|---:|
| train | 1983 | 36 | 2019 |
| valid | 280 | 0 | 280 |
| test | 304 | 10 | 314 |

Kaynak sınıfa göre (bir görüntü içerdiği her sınıfta sayılır):

| Kaynak sınıf | train gri | train RGB | valid gri | valid RGB | test gri | test RGB |
|---|---:|---:|---:|---:|---:|---:|
| SingleByPassed | 965 | 0 | 143 | 0 | 146 | 0 |
| SingleDiode | 432 | 0 | 59 | 0 | 81 | 0 |
| StringOpenCircuit | 369 | 0 | 73 | 0 | 57 | 0 |
| MultiByPassed | 176 | 0 | 19 | 0 | 30 | 0 |
| MultiDiode | 252 | 0 | 26 | 0 | 35 | 0 |
| StringReversedPolarity | 66 | 0 | 8 | 0 | 6 | 0 |
| Electrical Damage | 6 | 36 | 0 | 0 | 0 | 10 |

Çıkarılmayan, hedef kutusu olmayan arka planlar (kaynak sınıf kümesine göre; gri+RGB toplamı):

| Kaynak sınıf kümesi | train | valid | test |
|---|---:|---:|---:|
| (etiketsiz) | 7 | 0 | 0 |
| Non Defective | 186 | 23 | 41 |

Karma görüntüler (hedef kutusu + kapsam dışı kutu; remap sonrası anomali bölgesi etiketsiz kalır, bu işte DEĞİŞTİRİLMEDİ):

| Bölme | OOS-sınıf kutusu içeren | Herhangi eşlenmemiş kutu içeren |
|---|---:|---:|
| train | 1263 | 1472 |
| valid | 133 | 166 |
| test | 130 | 144 |

## 5. Kontroller

- Test `hotspot` ≥ 300: 1290 ✓
- Ultralytics 8.4.41 `verify_image_label`: toplam bozuk = **0**
  - train: 5337 görüntü, 0 bozuk, 193 boş, 0 segment içeren, 17652 instance
  - valid: 640 görüntü, 0 bozuk, 23 boş, 0 segment içeren, 2102 instance
  - test: 606 görüntü, 0 bozuk, 41 boş, 0 segment içeren, 2165 instance
- `check_det_dataset`: ✓
