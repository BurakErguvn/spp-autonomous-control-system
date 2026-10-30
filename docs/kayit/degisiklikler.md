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

## 2026-10-20 20:28 — #2/#3 dalının tester doğrulaması

- Kod değişmedi (orkestratör). `tester` (Sonnet/high) dal `claude/sad-margulis-eb217f` (`b485ecb`) üzerinde başlatıldı: testler, 0-corrupt taraması, poligon→bbox doğruluğu, determinizm, bölmeler arası stem/hash sızıntısı, sınıf × modalite × bölme tablosunun bağımsız yeniden hesabı.
- Gerekçe: veri hattı doğrulaması (matematik/model değişikliği değil) → Sonnet yeterli. Mevcut `data/ges_clean` üzerine yazılmaması, yeniden üretimin geçici klasöre yapılması istendi.

## 2026-10-20 20:40 — #2/#3 tester sonucu: PASS (koşullu)

- Dal `claude/sad-margulis-eb217f`: `96611d3` test: `tests/test_audit_dataset_extra.py` (15 test: determinizm, çevirme-duyarsız dHash, dejenere/hatalı satır, gerçek veri invariantları); `b966ae7` + `9718a95` docs: `outputs/test_reports/issue-2-3.md`. Üretim koduna dokunulmadı.
- Kabul kriterleri (#2, #3) bağımsız yeniden üretildi: 0 corrupt (Ultralytics 8.4.41), ham veri md5 farkı 0/9196, scratch'e yeniden üretim `diff -rq` farksız (deterministik), bölmeler arası stem/grup kesişimi 0, test hotspot 1291.
- Orkestratör teyidi: `pytest -q tests --ignore=tests/test_gui.py` → 73 passed, 3 skipped (`test_gui.py` Qt ortam hatası, main'de de var).
- Açık alan kararları (kullanıcıya): (1) train'deki 2271 arka plan görüntüsünün tamamı kaynakta kapsam dışı sınıfla etiketli (2561'i termal anomali: Diode/ByPassed/StringOpenCircuit…) → olduğu gibi / çıkar-ayır / 15 sınıflı eğit; (2) yakın-kopya eşiği (dHash ≤4, NCC ≥0.85) komşu drone karelerini ayırmıyor (test↔train NCC ≥0.90: 30/921) → koru / gevşet (`--hash-thr 8 --ncc-thr 0.90`).
- Kapsam dışı: `scripts/train_yolo26.py` hâlâ `ges_project.yaml` + ham veride yerinde `remap_labels` kullanıyor; `ges_clean`'e bağlanması ayrı issue.

## 2026-10-20 20:45 — #2/#3 alan kararları ve iş bölümü

- Karar (kullanıcı): yakın-kopya eşiği gevşetilecek (`--hash-thr 8 --ncc-thr 0.90`); gerekçe: ardışık drone kareleri bölmeler arasında kalıyor (test↔train NCC ≥0.90: 30/921), test skoru iyimser.
- Karar (kullanıcı): kapsam dışı termal arızalar (Diode, ByPassed, StringOpenCircuit, ReversedPolarity …) eğitime katılmak isteniyor, ancak mevcut örnek sayısı yetersiz → önce güvenilir/uyumlu veri seti genişletme kaynakları ve bu arıza tiplerinin onarım + geleneksel tespit (zaman, para) maliyetleri araştırılacak. Taksonomi kararı (#6) araştırma sonrasına ertelendi.
- Karar (kullanıcı): #2/#3 PR'ı eşik değişikliği uygulanıp tester yeniden doğruladıktan sonra açılacak.
- İş bölümü: veri-muhendisi (Sonnet/high) aynı dalda eşik + yeniden üretim; arastirmaci ×2 (Sonnet/medium, ayrı worktree'ler) veri seti genişletme ve arıza maliyetleri; katip (Haiku/low) kararları #3/#6'ya işler.

## 2026-10-20 20:55 — Yazan agentlarda worktree izolasyonu kaldırıldı

- Sorun: veri-muhendisi, tanımındaki `isolation: worktree` yüzünden main'den yeni boş worktree'de başladı; mevcut `claude/sad-margulis-eb217f` dalına erişemedi (izolasyon kuralı + guard). Hiçbir değişiklik yapılmadı.
- `.claude/agents/{veri-muhendisi,gorsel-model,ucus-planlayici,yoneylem}.md`: `isolation: worktree` satırı silindi.
- `CLAUDE.md` iş akışı md. 2: worktree'yi orkestratör açar (`git worktree add`) veya mevcut dalın yolunu verir; agent o yola `cd` eder.
- Karar (kullanıcı): "worktree'yi orkestratör açsın" seçeneği; gerekçe: FAIL → aynı dalda düzeltme döngüsü ancak böyle çalışır (tester zaten bu modelde çalışıyordu). Agentın önerdiği hook/sınıflandırıcı izinlerini açma seçeneği uygulanmadı.
- Veri seti genişletme araştırması tamamlandı: `docs/arastirma/veri-seti-genisletme.md`, dal `worktree-agent-a50dd5221d0f267d1` (`026b840`).

## 2026-10-20 21:00 — Izolasyon kaldırma bu oturumda etkisiz

- veri-muhendisi ikinci denemede de izole worktree'de (`38f5e1d` tabanlı) başladı ve talimat gereği durdu; değişiklik yok. Neden: agent tanımları oturum başında yükleniyor, `.claude/agents/*.md` düzenlemesi yeni oturumda etkin olur.

## 2026-10-20 21:10 — Arıza maliyetleri araştırması ve oturum devri

- Arıza maliyetleri araştırması tamamlandı: `docs/arastirma/ariza-maliyetleri.md`, dal `worktree-agent-ac97f9fac39b3d091` (`62c7c26`, Refs #6 #10). 9 arıza tipi × {onarım, maliyet, süre, kayıp, aciliyet, geleneksel tespit}; 22 kaynak; doğrulanamayanlar [D], tahminler [T] işaretli. Türkiye TL birim fiyatları ve adam-saat süreleri kaynaksız (yerel teklif gerekir).
- Öne çıkan bulgu: açık devre bypass diyot normal koşulda IR'de görünmüyor; termalde sıcak görünen aktif bypass alt dizisi (Köntges, IEA PVPS T13 2025) → #6'da Diode/ByPassed birleştirme seçeneğini destekliyor.
- Kapsam dışı gözlem: `modules/optimization/solver.py` `HASAR_PRIORITY`/`MUST_FIX_CLASSES` yalnız 3 sınıf; yeni sınıflarda `service_minutes`=30, `daily_loss_kwh`=0 varsayılanı sessizce devreye girer; toz kaybı sabit %10/30·H (birikimli değil).
- Karar (kullanıcı): eşik işi (#3) yeni oturumda sürdürülecek (agent tanımı değişikliği oturum başında yükleniyor).
- Açık işler (yeni oturum için):
  1. veri-muhendisi → `claude/sad-margulis-eb217f` worktree'sinde eşik gevşetme (`--hash-thr 8 --ncc-thr 0.90` başlangıç), yeniden üretim, `--keep-original-classes` ile bölme bağımsızlığı; sonra tester → PR (Closes #2, #3).
  2. #6 taksonomi kararı kullanıcıda: veri seti genişletme seçenekleri (S1 sınıf birleştirme / S2 +ikinci aşama sınıflandırıcı / S3 +kendi verisiyle yarı-otomatik etiketleme) ve maliyet bulguları birlikte sunulacak.
  3. İki araştırma dalı (`worktree-agent-a50dd5221d0f267d1`, `worktree-agent-ac97f9fac39b3d091`) main'e alınmadı (`origin/main` = `38f5e1d` tabanlı); merge kullanıcı onayıyla.
  4. Eğitim hattının `ges_clean.yaml`'a bağlanması (tester bulgu 3) — #8'e not mu, yeni issue mu, kullanıcıya soruldu.
  5. Veri lisansı çelişkisi: Roboflow `data.yaml` `license: Private`, README "CC BY 4.0" — netleşmeli.

## 2026-10-20 21:11 — 15 sınıf genişletme iptal, lisans CC BY 4.0, #8 notu, oturum devri

- Karar (kullanıcı): 15 sınıfa genişletme yapılmıyor; 3 hedef sınıf korunuyor. Gerekçe: araştırılan açık termal PV veri setlerinin hiçbiri bbox sunmuyor (sınıflandırma kırpmaları), tespit görevine eklenemiyor. #6'ya yorum: issuecomment-6297823185.
- Karar (kullanıcı): Roboflow "SOLAR PANEL DET" lisansı **CC BY 4.0** (`data.yaml`'daki `license: Private` geçersiz); atıf gerekli.
- Karar (kullanıcı): eğitim hattının `ges_clean.yaml`'a bağlanması #8'e not edildi (issuecomment-6297823572).
- Açık: #6'da kapsam dışı termal anomali içeren arka plan görüntüleri (train 2271) bırakılacak mı, çıkarılacak mı.
- Sorun: `.claude/hooks/log_input.py` kullanıcı turu olarak gelen alt agent raporlarını/görev bildirimlerini (`<agent-message`, `<task-notification`) de `inputlar.md`'ye yazıyor (bu oturumda 7 hatalı girdi, 20:35–21:11); ayrıca kayıt yolunu `cwd`'den alıyor. Düzeltme + hatalı girdilerin çıkarılması izin sınıflandırıcısınca reddedildi; kullanıcı kararı bekliyor.
- Güncel açık işler (yeni oturum): (1) #3 eşik gevşetme → tester → PR (Closes #2, #3); (2) #6 arka plan kararı; (3) araştırma dallarının (`worktree-agent-a50dd5221d0f267d1`, `worktree-agent-ac97f9fac39b3d091`) main'e merge onayı; (4) log_input hook düzeltmesi; (5) main push.

## 2026-10-20 21:14 — Arka plan anomalileri çıkarılsın, hook izni, merge, push

- Karar (kullanıcı, #6): kapsam dışı termal anomali içeren arka plan görüntüleri (kaynakta etiketli ama 3 sınıflı eşlemede boş kalan; train'de 2271) **eğitim verisinden çıkarılacak**. Uygulama veri-muhendisinde, #3 eşik işiyle aynı dalda (`claude/sad-margulis-eb217f`); gerçek "Non Defective" arka planlar kalır. valid/test'te aynı görüntülerin ele alınışı (çıkar / ayrı raporla) için veri-muhendisi seçenek + öneri sunacak.
- `.claude/hooks/log_input.py` (kullanıcı izniyle): `<agent-message`, `<task-notification`, `<system-reminder`, `<side-sessions-event`, `<ci-monitor-event` ile başlayan turlar kaydedilmez; kayıt yolu `CLAUDE_PROJECT_DIR`'den alınır (yoksa `cwd`). Test: agent mesajı → kayıt yok; normal mesaj → kayıt var.
- `docs/kayit/inputlar.md` (kullanıcı izniyle): hook hatasıyla eklenen 7 kullanıcı-dışı girdi (20:35–21:11, alt agent raporları ve görev bildirimleri) çıkarıldı; iki başlık düzeltildi.
- Karar (kullanıcı): araştırma dalları main'e merge edildi (`docs/arastirma/veri-seti-genisletme.md`, `docs/arastirma/ariza-maliyetleri.md`); main push edildi.

## 2026-10-30 14:25 — #3 eşik + #6 arka plan çıkarma, tester, PR

- Kod değişmedi (orkestratör). `veri-muhendisi` (Sonnet/high) `claude/sad-margulis-eb217f` worktree'sinde başlatıldı: (1) #3 yakın-kopya varsayılanları `--hash-thr 8 --ncc-thr 0.90`, başarı ölçütü tester metriği (bölmeler arası 24×24 max-NCC ≥0.90; önce test↔train 30/921, valid↔train 27/918); yetersizse seçenek sunacak; (2) #6 kapsam dışı termal anomali içeren arka planların çıkarılması (gruplama/bölme tüm görüntülerle, çıkarma bölme sonrası filtre önerildi).
- Karar (kullanıcı, #6): valid/test'teki aynı tür görüntüler de çıkarılır ve ayrı `oos` değerlendirme kümesine yazılır (yanlış pozitif oranı ayrıca raporlanacak). Gerekçe: ana valid/test yalnız 3 hedef sınıf + gerçek arka planı ölçer, sahadaki anomalilere verilen yanlış alarm yine ölçülebilir.
- Not: worktree'de eski hook'un yazdığı commit'lenmemiş `docs/kayit/inputlar.md` değişikliği (2 agent-message girdisi) duruyor; geri alma izin sınıflandırıcısınca reddedildi, agenta commit'e katmaması söylendi.
- `docs/kayit/inputlar.md`: bu turun başlığı düzeltildi.
- Kullanıcı worktree'deki eski `docs/kayit/inputlar.md` değişikliğini `git checkout` ile geri aldı; dosya artık temiz.

## 2026-10-30 14:44 — #3/#6 veri-muhendisi sonucu

- Dal `claude/sad-margulis-eb217f`: `2e505fa` feat: `scripts/audit_and_fix_dataset.py` — varsayılan `--hash-thr 8 --ncc-thr 0.90`; yeni `--ncc-only-thr` (dHash'siz NCC adayı, varsayılan kapalı); `ncc_leakage()` bağımsız sızıntı ölçütü; OOS filtresi (`OOS_DEFAULT_CLASSES`, `--oos-classes`, `--oos-mode {separate,keep,drop}`), manifest'e `placed_in`/`oos`/`oos_source_classes`. `2127401` test: +13 test. `d8cbbae` docs: `outputs/reports/dataset_audit.{json,md}`.
- `data/ges_clean` yeniden üretildi (git dışı): train 5268 / valid 663 / test 704 görüntü, `oos/` 2561 (atanmış bölme 2090/255/216); Ultralytics 0 bozuk. pytest 84 passed, 4 skipped (veri bağıyla 88 passed).
- OOS kümesi: MultiByPassed, MultiDiode, SingleByPassed, SingleDiode, StringOpenCircuit, StringReversedPolarity; hepsi termal. Gruplama/bölme tüm görüntülerle, filtre bölme sonrası (grup kesişimi 0). `--keep-original-classes` ile 9196 dosyada grup/bölme aynı.
- Bulgu: 8/0.90 bağımsız ≥0.90 sızıntıyı düşürmüyor (test↔train 31→33, valid↔train 36→42; gürültü ±10). Ardışık kareler çoğunlukla dHash>8. Seçenek: `--ncc-only-thr 0.93` → test↔train 23/0/0, valid↔train 28/0/0 (≥.90/.95/.97), en büyük grup 45; 0.90 → 11/9 ama en büyük grup 223.
- Bulgu: filtre sonrası arka plan oranı train %30.9 → %4.3 (227/5268); termal negatif neredeyse kalmadı.
- Açık alan kararları (kullanıcıda): eşik seçimi; Electrical Damage (yalnız RGB, train 24) arka plan kalsın mı; termal negatif azlığı.

## 2026-10-30 14:46 — #3/#6 alan kararları (eşik, negatifler, Electrical Damage)

- Karar (kullanıcı, #3): yakın-kopya varsayılanı `--hash-thr 8 --ncc-thr 0.90 --ncc-only-thr 0.93`. Gerekçe: ≥0.95/0.97 sızıntı 0'a iner, en büyük grup 45'te kalır (0.90'daki 223'lük zincirleme yok).
- Karar (kullanıcı, #6): termal negatif azlığı (train arka plan %4.3) şimdilik kabul; FP `oos` kümesinde ölçülecek, eğitimde sorun çıkarsa (#8) yeniden ele alınır, issue'ya not edilecek.
- Karar (kullanıcı, #6): "Electrical Damage" OOS kümesine eklenir (gerçek arıza, "arıza yok" diye öğretilmemeli).
- veri-muhendisi aynı oturumla sürdürülüyor: varsayılan değişikliği, yeniden üretim, rapor/test güncellemesi.
- GitHub (katip, Haiku/low): kararlar #3 (issuecomment-6521900346) ve #6'ya (issuecomment-6521900820) yorum olarak işlendi.

## 2026-10-30 14:49 — #3/#6 kararları uygulandı; tester başlatıldı

- Dal `claude/sad-margulis-eb217f`: `f7a4230` feat: `--ncc-only-thr` varsayılanı 0.93, Electrical Damage `OOS_DEFAULT_CLASSES`'ta; `b734990` test; `08ef0c4` docs: `outputs/reports/dataset_audit.{json,md}`. pytest 84 passed, 4 skipped (veri bağıyla 88).
- `data/ges_clean` yeniden üretildi: train 5337 / valid 640 / test 606 / oos 2613 (toplam 9196); 2799 grup, en büyük 45; Ultralytics 0 bozuk. Arka plan: train %3.6, valid %3.6, test %6.8.
- `tester` (Sonnet/high) aynı dalda başlatıldı. Gerekçe: veri hattı doğrulaması; matematik/model değişikliği değil.

## 2026-10-30 15:01 — #2/#3/#6 tester PASS, PR #16

- Tester sonucu (Sonnet/high): PASS (koşullu). Dalda `ecfc9db`, `tests/test_audit_dataset_oos_independent.py` eklendi (6 test: OOS üyeliğinin ham etiketlerden bağımsız hesabı, korunan arka planlar, `placed_in`/`split` grup kesişimi, oranlar ve hotspot tabanı, NCC-only eşik altı ve çevirme ikizi). `3dec995`, `outputs/test_reports/issue-2-3.md` 2. tur. Tüm iddialar birebir yeniden üretildi. Yeniden üretim deterministik; `--oos-mode` ve `--keep-original-classes` modlarında 9196/9196 atama aynı. Zincirlemede ilgisiz sahne birleşmesi görülmedi.
- Bulgular (düşük): (1) 0.90–0.95 NCC aralığında artık sızıntı 15/15/4 (ardışık kareler); (2) `scripts/audit_and_fix_dataset.py:808` `--ncc-only-thr` ≤0 değerleri doğrulanmıyor (`-1` tüm çiftleri birleştirir); (3) gri tozlanma test n=23; (6) `tests/test_audit_dataset_extra.py` içinde Electrical Damage hakkında eski yorum; (7) `.claude/hooks/guard.py:98` worktree yollarını ana köke göre değerlendirip `.claude/` öneki nedeniyle Edit/Write'ı reddediyor.
- Orkestratör teyidi: `pytest -q tests --ignore=tests/test_gui.py` 86 passed, 8 skipped; main ile çakışma yok (`git merge-tree`).
- Dal origin'e pushlandı. PR açıldı: https://github.com/BurakErguvn/spp-autonomous-control-system/pull/16 (Closes #2, #3; Refs #6). CI kontrolü yok. Merge kullanıcı onayı bekliyor.

## 2026-10-30 15:05 — guard.py: worktree yolları worktree köküne göre değerlendirilsin

- Sorun (PR #16 doğrulamasında tester bildirdi): `.claude/hooks/guard.py` yazma yolunu ana repo köküne göre hesaplıyordu; `.claude/worktrees/<ad>/...` altındaki her dosya `.claude/` önekiyle eşleşip Edit/Write'ta reddediliyordu, alt agentlar kendi worktree'lerinde izinli yollara (`tests/**`, `outputs/test_reports/**` …) yazamıyordu.
- Değişiklik (`.claude/hooks/guard.py`, kullanıcı izniyle): göreli yol `.claude/worktrees/<ad>/` önekiyle başlıyorsa önek soyulur, `roles.json` kuralları worktree köküne göre uygulanır. Worktree içindeki `.claude/` ve `CLAUDE.md` yine korunur; worktree dizininin kendisi ve `..` ile kaçış reddedilir.
- Sınama (stdin'e örnek JSON): ana kökte izinli yol → izin; worktree'de izinli yol (cwd ana kök ve worktree) → izin; worktree'de `.claude/hooks/x` ve `CLAUDE.md` → red; tester için `modules/optimization/**` → red, yoneylem için izin.
