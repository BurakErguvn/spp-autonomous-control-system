# Veri Seti Denetim Raporu

Kaynak: `data/SOLAR PANEL DET.v1i.yolo26` → Çıktı: `data/ges_clean` (YAML: `data/ges_clean.yaml`)

Otomatik üretildi: `scripts/audit_and_fix_dataset.py`. Parametreler: `{"ratios": [0.8, 0.1, 0.1], "seed": 42, "hash_thr": 8, "ncc_thr": 0.9, "ncc_only_thr": null, "gray_thr": 1.0, "oos_mode": "separate", "oos_classes": ["MultiByPassed", "MultiDiode", "SingleByPassed", "SingleDiode", "StringOpenCircuit", "StringReversedPolarity"], "keep_original_classes": false}`

## 1. Etiket dönüşümü (poligon → bbox)

| Kaynak bölme | bbox satırı | poligon satırı (çevrildi) | dejenere | yinelenen | yinelenen (remap sonrası) | hatalı | karışık dosya (15 sınıf) | karışık dosya (remap sonrası) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 24132 | 7315 | 0 | 0 | 51 | 0 | 552 | 450 |
| valid | 1720 | 528 | 0 | 0 | 0 | 0 | 65 | 54 |
| test | 295 | 323 | 0 | 0 | 0 | 0 | 33 | 26 |

Karışık dosyalarda Ultralytics tüm satırları poligon sayar: 8.4.x'te 5 sütunlu bbox satırları iki nokta olarak okunup bozuk kutuya dönüşür, eski sürümlerde dosya düşürülür. Temiz veri setinde tüm satırlar 5 sütunludur.

## 2. Gruplama ve sızıntı

- 9196 görüntü, 3115 kaynak gövdesi, 2850 grup
- 753 yakın kopya çifti (dHash ≤ 8, çevirme duyarsız, NCC ≥ 0.9); 398 tanesi farklı gövdeler arasında
- En büyük grup: 24 görüntü

| Ölçüt | Önce (Roboflow bölmesi) | Sonra (yeni bölme) |
|---|---:|---:|
| Ortak gövde train-valid | 72 | 0 |
| Ortak gövde train-test | 17 | 0 |
| Ortak gövde valid-test | 8 | 0 |
| Ortak grup train-valid | 137 | 0 |
| Ortak grup train-test | 44 | 0 |
| Ortak grup valid-test | 20 | 0 |
| Bölmeler arası yakın kopya çifti | 195 | 0 |
| Train'de eşi olan test görüntüsü | 45 / 93 | 0 / 920 |

Bağımsız ölçüt: 24x24 küçük resim max-NCC (4 çevirme); ilk bölmedeki görüntülerden, ikincideki en benzeriyle NCC eşiğini aşanların sayısı (gruplama 32x32 kullandığı için bağımsızdır; yazılan görüntüler üzerinden).

| Bölme çifti | ≥0.90 önce | ≥0.90 sonra | ≥0.95 önce | ≥0.95 sonra | ≥0.97 önce | ≥0.97 sonra |
|---|---:|---:|---:|---:|---:|---:|
| test-train | 36/93 | 20/704 | 31/93 | 2/704 | 31/93 | 0/704 |
| valid-train | 118/553 | 27/663 | 89/553 | 2/663 | 84/553 | 1/663 |
| test-valid | 13/93 | 7/704 | 12/93 | 0/704 | 12/93 | 0/704 |

## 3. Bölme boyutları ve modalite

| Bölme | Önce gri | Önce RGB | Sonra gri | Sonra RGB | Sonra arka plan |
|---|---:|---:|---:|---:|---:|
| train | 7473 | 1077 | 4284 | 984 | 227 |
| valid | 453 | 100 | 541 | 122 | 37 |
| test | 40 | 53 | 580 | 124 | 45 |

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
| hotspot | 10345 | 1295 | 1293 | 0 | 0 | 0 | 12933 |
| mikro_catlak | 1401 | 136 | 123 | 1817 | 282 | 279 | 4038 |
| tozlanma | 41 | 13 | 11 | 4020 | 442 | 421 | 4948 |

**Orijinal 15 sınıf — yeni bölme**

| Sınıf | train gri | valid gri | test gri | train RGB | valid RGB | test RGB | Toplam |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bird Drop | 3 | 0 | 11 | 1623 | 171 | 134 | 1942 |
| Defective | 331 | 28 | 32 | 1294 | 192 | 165 | 2042 |
| Dusty | 33 | 13 | 0 | 1409 | 161 | 182 | 1798 |
| Electrical Damage | 23 | 0 | 0 | 361 | 48 | 50 | 482 |
| Non Defective | 26 | 3 | 0 | 2998 | 370 | 402 | 3799 |
| Physical Damage | 1117 | 110 | 91 | 525 | 90 | 114 | 2047 |
| Snow | 5 | 0 | 0 | 988 | 110 | 105 | 1208 |
| MultiByPassed | 93 | 8 | 17 | 0 | 0 | 0 | 118 |
| MultiDiode | 302 | 43 | 66 | 0 | 0 | 0 | 411 |
| MultiHotSpot | 4236 | 530 | 531 | 0 | 0 | 0 | 5297 |
| SingleByPassed | 904 | 101 | 138 | 0 | 0 | 0 | 1143 |
| SingleDiode | 833 | 122 | 82 | 0 | 0 | 0 | 1037 |
| SingleHotSpot | 6109 | 765 | 762 | 0 | 0 | 0 | 7636 |
| StringOpenCircuit | 169 | 29 | 3 | 0 | 0 | 0 | 201 |
| StringReversedPolarity | 28 | 5 | 4 | 0 | 0 | 0 | 37 |

## 4b. Kapsam dışı termal anomali arka planları (OOS)

- Mod: `separate` — bölme tüm görüntülerle yapıldı, filtre bölmeden SONRA uygulandı
- Çıkarma kümesi (kaynak sınıflar): MultiByPassed, MultiDiode, SingleByPassed, SingleDiode, StringOpenCircuit, StringReversedPolarity
- Kural: remap sonrası hedef kutusu kalmayan ve bu sınıflardan birini içeren görüntü. Etiketsiz / yalnız Non Defective / Electrical Damage arka planları ve hedef kutusu olan karma görüntüler korunur.
- Yazılan: oos=2561, atılan (yazılmayan)=0

| Atanmış bölme | gri | RGB | Toplam |
|---|---:|---:|---:|
| train | 2090 | 0 | 2090 |
| valid | 255 | 0 | 255 |
| test | 216 | 0 | 216 |

Kaynak sınıfa göre (bir görüntü içerdiği her sınıfta sayılır):

| Kaynak sınıf | train gri | train RGB | valid gri | valid RGB | test gri | test RGB |
|---|---:|---:|---:|---:|---:|---:|
| SingleByPassed | 1018 | 0 | 119 | 0 | 117 | 0 |
| SingleDiode | 451 | 0 | 61 | 0 | 60 | 0 |
| StringOpenCircuit | 421 | 0 | 66 | 0 | 12 | 0 |
| MultiByPassed | 182 | 0 | 27 | 0 | 16 | 0 |
| MultiDiode | 255 | 0 | 31 | 0 | 27 | 0 |
| StringReversedPolarity | 65 | 0 | 7 | 0 | 8 | 0 |

Çıkarılmayan, hedef kutusu olmayan arka planlar (kaynak sınıf kümesine göre; gri+RGB toplamı):

| Kaynak sınıf kümesi | train | valid | test |
|---|---:|---:|---:|
| (etiketsiz) | 4 | 0 | 3 |
| Electrical Damage | 24 | 3 | 4 |
| Electrical Damage+Non Defective | 15 | 3 | 3 |
| Non Defective | 184 | 31 | 35 |

Karma görüntüler (hedef kutusu + kapsam dışı kutu; remap sonrası anomali bölgesi etiketsiz kalır, bu işte DEĞİŞTİRİLMEDİ):

| Bölme | OOS-sınıf kutusu içeren | Herhangi eşlenmemiş kutu içeren |
|---|---:|---:|
| train | 1095 | 1419 |
| valid | 142 | 183 |
| test | 147 | 180 |

## 5. Kontroller

- Test `hotspot` ≥ 300: 1293 ✓
- Ultralytics 8.4.41 `verify_image_label`: toplam bozuk = **0**
  - train: 5268 görüntü, 0 bozuk, 227 boş, 0 segment içeren, 17624 instance
  - valid: 663 görüntü, 0 bozuk, 37 boş, 0 segment içeren, 2168 instance
  - test: 704 görüntü, 0 bozuk, 45 boş, 0 segment içeren, 2127 instance
- `check_det_dataset`: ✓
