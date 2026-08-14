# Proje değişiklikleri

Kod, doküman ve yapılandırma değişiklikleri kronolojik tutulur. Maddeler silinmez; yalnızca sona eklenir.

---

## 2026-08-13 14:09 — Proje kayıt kuralı oluşturuldu

- `.cursor/rules/proje-kayit.mdc`: her mesajda kayıt düşmeyi zorunlu kılan, her oturumda uygulanan Cursor kuralı eklendi
- `docs/proje_kayit.md`: ilk birleşik kayıt defteri oluşturuldu
- Karar: kayıt her kullanıcı mesajından sonra, iş bitmeden tutulur; formüller LaTeX ile yazılır; eski maddeler silinmez

## 2026-08-13 14:21 — Model konumu, gereksiz ağırlıklar ve optimizasyon algoritmaları

- `yolo26n.pt`: silindi (COCO ön-eğitim, kodda referans yok)
- `runs/detect/models/ges_yolo26/weights/last.pt`: silindi (son epoch yedek; pipeline kullanmıyor)
- `runs/detect/models/ges_yolo26/weights/yolo26nano.pt`: silindi (epoch 7 yarım eğitim, mAP50=0.336)
- Korunan: `models/best.pt` (aktif inference), `yolo26s.pt` (yeniden eğitim tabanı), `runs/.../weights/best.pt` (YOLO26s ince ayar, pipeline'a bağlı değil)
- Karar: üretim modelini değiştirmedik; `models/best.pt` aslında `yolov8n` ince ayarı, dokümandaki YOLO26s değil

## 2026-08-13 14:40 — YOLO26s resmi model, rota portföyü, Colab

- `models/best.pt`: YOLO26s ince ayar kopyalandı (eski yolov8n üzerine yazıldı; ~20 MB, 3 sınıf)
- `runs/.../weights/best.pt`: kopya sonrası silindi (artık `models/best.pt` ile aynıydı)
- `outputs/reports/train_metrics.json`: yolo26s metrikleri + `architecture` alanı
- `modules/optimization/routing.py`: Clarke–Wright + 2-opt, ALNS, OR-Tools portföyü eklendi
- `modules/optimization/solver.py`: PuLP MTZ CVRP kaldırıldı; portföy + NN fallback
- `requirements.txt`: `ortools>=9.8.0`
- `scripts/train_yolo26.py`: `--size n|s|m|l|x` (varsayılan s)
- `scripts/train_yolo26_colab.ipynb`: free T4 Colab eğitim defteri
- `tests/test_optimization.py`: rota portföyü testleri (17 passed)
- Karar: Cursor Colab GPU’suna bağlanamaz; eğitim notebook ile Drive üzerinden. Free tier hedefi YOLO26m.

## 2026-08-14 14:16 — Commit ve push

- `main` dalına yalnızca bu oturumun dosyaları eklendi; dokumanlar silmeleri, pycache ve senaryo JSON’ları commit dışı bırakıldı
