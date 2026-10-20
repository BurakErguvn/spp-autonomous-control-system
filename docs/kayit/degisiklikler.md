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

## 2026-08-14 14:54 — Rota algoritması seçimi ve ekip maliyeti

- `scripts/benchmark_routing.py`: CW+2-opt, ALNS, OR-Tools aynı 6 örnekte (B/C/mixed/20/24/30) izole ölçüldü
- `tests/test_routing_solvers.py`: her çözücü için izole pytest; ALNS ≤ CW mesafe regresyonu
- `modules/optimization/routing.py`: üretim `solve_cvrp` = ALNS; OR-Tools ve portföy kaldırıldı; CW yalnızca tohum
- `modules/optimization/solver.py`: tek ALNS çağrısı; `CVRP_TIME_LIMIT_S` silindi
- `requirements.txt`: `ortools` bağımlılığı kaldırıldı
- `tests/test_optimization.py`: portföy iddiaları ALNS’e çekildi (23 passed)
- Karar: ALNS = OR-Tools mesafe, ~100× hızlı; CW büyük örneklerde %2–13 daha uzun. Maliyet seçimi MILP, ekip ataması ALNS.

## 2026-08-14 17:00 — QAOA QUBO deneyi ve klasik–kuantum raporu

- `modules/optimization/qubo.py`: seçim ve oyuncak CVRP QUBO (ölçekli must-fix, slack)
- `modules/optimization/qaoa_runner.py`: RZZ/RX QAOA, Aer statevector/shot, IBM SamplerV2 (token env)
- `modules/optimization/qaoa_instances.py`, `scripts/run_qaoa_benchmark.py`, figürler `outputs/reports/qaoa/`
- `tests/test_qubo.py`, `tests/test_qaoa.py` (33 passed birlikte)
- `requirements-qaoa.txt`, `.gitignore`: `.env`, `.qiskit/`
- `docs/qaoa_karsilastirma_raporu.md`
- Karar: üretim CBC+ALNS değişmedi. QAOA $N\le 8$ seçimde CBC ile örtüşür; CVRP ve saha ölçeği NISQ dışı. IBM bu koşuda tokensız atlandı.

## 2026-10-20 20:15 — Proje sorun analizi (geriye dönük kayıt)

- Kod değişmedi; analiz yapıldı. Bulgular GitHub Issues'a taşındı (Faz 0–4).
- Ayrı oturum: `scripts/audit_and_fix_dataset.py` (poligon→bbox, grup bazlı sızıntısız bölme, denetim raporu) — dal `claude/sad-margulis-eb217f`, commit `b485ecb`; henüz main'e alınmadı, tester doğrulamasını bekliyor.
- Karar: modeller zaten COCO ön-eğitimliydi (Colab günlüğü: "Transferred 768/768 items from pretrained weights"); düşük skorun ana nedeni veri ve sınıf tanımı.

## 2026-10-20 20:15 — Çok-agentlı çalışma ortamı

- `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.claude/worktrees/` eklendi
- QAOA deneyi `deney/qaoa` dalına alındı (`7540dad`); main'e girmedi
- `CLAUDE.md`: orkestratör modeli, roller, iş akışı, sabit kısıtlar ve kayıt kuralı (Cursor kuralının Claude Code karşılığı)
- `.claude/agents/*.md`: 7 rol — veri-muhendisi (Sonnet/high), gorsel-model (Opus/high), yoneylem (Opus/xhigh), ucus-planlayici (Opus/high), arastirmaci (Sonnet/medium), tester (Sonnet/high, kritikte Opus), katip (Haiku/low)
- `.claude/hooks/guard.py` + `roles.json`: rol bazlı yazma izinleri; git push/merge/rebase/reset --hard/dal silme, paket kurulumu, rm -rf, `.env` ve (katip dışı) GitHub'a yazma engeli
- `.claude/hooks/log_input.py` + `.claude/settings.json`: kullanıcı mesajları `inputlar.md`'ye otomatik eklenir (alt agent turları ve gizli bilgiler hariç)
- Kararlar (kullanıcı): sorun kaydı = GitHub Issues + Projects panosu (repo herkese açık, yayımlanması onaylandı); mekanizma = subagent + SendMessage (Agent Teams deneysel olduğu için değil); her yazan agent kendi worktree'sinde; serbest danışma ama iş devri yok, kararlar issue'ya; kullanıcı onayı = main'e merge + alan kararları; hesaplama yerelde ≤15 dk, uzun eğitim Colab; dil Türkçe; model seçimi işin zorluğuna göre karma

## 2026-10-20 20:30 — GitHub Issues kurulumu

- GitHub (`BurakErguvn/spp-autonomous-control-system`): 17 etiket (`alan:*`, `öncelik:P0-P2`, `karar-gerekli`, `agent:*`), 5 milestone (Faz 0–4), 15 issue (#1–#15) açıldı
- Projects panosu bekliyor: gh token'ında `project` izni yok (kullanıcı `gh auth refresh -s project,read:project` çalıştıracak)
