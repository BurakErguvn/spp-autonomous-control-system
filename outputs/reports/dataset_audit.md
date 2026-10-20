# Veri Seti Denetim Raporu

Kaynak: `data/SOLAR PANEL DET.v1i.yolo26` → Çıktı: `data/ges_clean` (YAML: `data/ges_clean.yaml`)

Otomatik üretildi: `scripts/audit_and_fix_dataset.py`. Parametreler: `{"ratios": [0.8, 0.1, 0.1], "seed": 42, "hash_thr": 4, "ncc_thr": 0.85, "gray_thr": 1.0}`

## 1. Etiket dönüşümü (poligon → bbox)

| Kaynak bölme | bbox satırı | poligon satırı (çevrildi) | dejenere | yinelenen | yinelenen (remap sonrası) | hatalı | karışık dosya (15 sınıf) | karışık dosya (remap sonrası) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 24132 | 7315 | 0 | 0 | 51 | 0 | 552 | 450 |
| valid | 1720 | 528 | 0 | 0 | 0 | 0 | 65 | 54 |
| test | 295 | 323 | 0 | 0 | 0 | 0 | 33 | 26 |

Karışık dosyalarda Ultralytics tüm satırları poligon sayar: 8.4.x'te 5 sütunlu bbox satırları iki nokta olarak okunup bozuk kutuya dönüşür, eski sürümlerde dosya düşürülür. Temiz veri setinde tüm satırlar 5 sütunludur.

## 2. Gruplama ve sızıntı

- 9196 görüntü, 3115 kaynak gövdesi, 2838 grup
- 645 yakın kopya çifti (dHash ≤ 4, çevirme duyarsız, NCC ≥ 0.85); 401 tanesi farklı gövdeler arasında
- En büyük grup: 66 görüntü

| Ölçüt | Önce (Roboflow bölmesi) | Sonra (yeni bölme) |
|---|---:|---:|
| Ortak gövde train-valid | 72 | 0 |
| Ortak gövde train-test | 17 | 0 |
| Ortak gövde valid-test | 8 | 0 |
| Ortak grup train-valid | 137 | 0 |
| Ortak grup train-test | 44 | 0 |
| Ortak grup valid-test | 20 | 0 |
| Bölmeler arası yakın kopya çifti | 185 | 0 |
| Train'de eşi olan test görüntüsü | 45 / 93 | 0 / 921 |

## 3. Bölme boyutları ve modalite

| Bölme | Önce gri | Önce RGB | Sonra gri | Sonra RGB | Sonra arka plan |
|---|---:|---:|---:|---:|---:|
| train | 7473 | 1077 | 6372 | 985 | 2271 |
| valid | 453 | 100 | 796 | 122 | 307 |
| test | 40 | 53 | 798 | 123 | 292 |

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
| hotspot | 10348 | 1294 | 1291 | 0 | 0 | 0 | 12933 |
| mikro_catlak | 1325 | 190 | 145 | 1898 | 215 | 265 | 4038 |
| tozlanma | 53 | 11 | 1 | 3978 | 441 | 464 | 4948 |

**Orijinal 15 sınıf — yeni bölme**

| Sınıf | train gri | valid gri | test gri | train RGB | valid RGB | test RGB | Toplam |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bird Drop | 3 | 11 | 0 | 1638 | 150 | 140 | 1942 |
| Defective | 309 | 49 | 33 | 1323 | 156 | 172 | 2042 |
| Dusty | 45 | 0 | 1 | 1393 | 180 | 179 | 1798 |
| Electrical Damage | 23 | 0 | 0 | 361 | 47 | 51 | 482 |
| Non Defective | 19 | 7 | 3 | 3037 | 361 | 372 | 3799 |
| Physical Damage | 1061 | 145 | 112 | 577 | 59 | 93 | 2047 |
| Snow | 5 | 0 | 0 | 947 | 111 | 145 | 1208 |
| MultiByPassed | 313 | 39 | 39 | 0 | 0 | 0 | 391 |
| MultiDiode | 836 | 104 | 107 | 0 | 0 | 0 | 1047 |
| MultiHotSpot | 4239 | 528 | 530 | 0 | 0 | 0 | 5297 |
| SingleByPassed | 2601 | 325 | 326 | 0 | 0 | 0 | 3252 |
| SingleDiode | 1587 | 197 | 198 | 0 | 0 | 0 | 1982 |
| SingleHotSpot | 6109 | 766 | 761 | 0 | 0 | 0 | 7636 |
| StringOpenCircuit | 1028 | 118 | 120 | 0 | 0 | 0 | 1266 |
| StringReversedPolarity | 99 | 12 | 13 | 0 | 0 | 0 | 124 |

## 5. Kontroller

- Test `hotspot` ≥ 300: 1291 ✓
- Ultralytics 8.4.41 `verify_image_label`: toplam bozuk = **0**
  - train: 7357 görüntü, 0 bozuk, 2271 boş, 0 segment içeren, 17602 instance
  - valid: 918 görüntü, 0 bozuk, 307 boş, 0 segment içeren, 2151 instance
  - test: 921 görüntü, 0 bozuk, 292 boş, 0 segment içeren, 2166 instance
- `check_det_dataset`: ✓
