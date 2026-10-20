# GES Otonom Denetim ve Bakım Optimizasyonu

Güneş enerjisi santrallerinde drone (DJI Matrice 350 RTK) görüntülerinden YOLO26 ile arıza tespiti, ardından bakım seçimi ve ekip rotalaması. Modüller: `modules/data_feeder` → `modules/ai_inference` → `modules/optimization` → `modules/gui`; aralarındaki sözleşme `outputs/ariza_verileri.json` ve `outputs/gorev_cizelgesi.json`.

Dil: Türkçe (issue, PR, commit açıklaması, rapor, agent mesajları). Kod tanımlayıcıları ve commit önekleri (`feat:`, `fix:` …) İngilizce kalır.

## Çalışma modeli: orkestratör + alt agentlar

Ana oturum **orkestratördür**: işi issue'lara böler, uygun alt agentı ve modeli seçer, sonucu doğrulatır, kullanıcı onayına sunar. Alt agent tanımları `.claude/agents/`, yazma izinleri `.claude/hooks/roles.json` (hook ile zorunlu).

| Rol | Model / efor | Alan |
|---|---|---|
| `veri-muhendisi` | Sonnet / high | Veri seti, etiketler, bölme, denetim |
| `gorsel-model` | Opus / high | YOLO eğitimi, Colab, değerlendirme, çıkarım hattı |
| `yoneylem` | Opus / xhigh | Maliyet modeli, seçim + rotalama, benchmark, karşılaştırma raporu |
| `ucus-planlayici` | Opus / high | Drone kapsama rotası, GSD, batarya, IEC 62446-3 koşulları |
| `arastirmaci` | Sonnet / medium | Kaynaklı literatür/parametre araştırması (`docs/arastirma/`) |
| `tester` | Sonnet / high (matematik/model değişikliğinde Opus) | Bağımsız doğrulama, PASS/FAIL |
| `katip` | Haiku / low | GitHub issue/PR/pano, kayıt dosyaları |

Model seçimi işin zorluğuna göre yapılır: orkestratör gerekirse çağrı başına bir üst/alt modele geçer ve bunu issue'ya not eder.

### İş akışı

1. Her iş bir GitHub issue'sudur (`BurakErguvn/spp-autonomous-control-system`; etiketler `alan:*`, `öncelik:P0-P2`, `agent:*`; milestone = faz).
2. Yazan agent kendi worktree'sinde/dalında çalışır, ortak rapor formatıyla döner. Worktree'yi orkestratör açar (`git worktree add .claude/worktrees/<ad> -b <dal> main`) veya mevcut dalın worktree yolunu verir; agent tanımlarında `isolation: worktree` yoktur (her çağrıda main'den boş worktree açıp mevcut dalda çalışmayı engelliyordu). Agent verilen yola `cd` eder, dal değiştirmez.
3. `tester` aynı dalda bağımsız doğrular. FAIL → bulgular yazan agenta geri gider (aynı agent `SendMessage` ile sürdürülür). PASS → orkestratör PR açar (`Closes #N`).
4. **Kullanıcı onayı gereken adımlar:** main'e merge; alan kararları (sınıf taksonomisi, maliyet parametreleri, problem formülasyonu, kabul eşikleri). Agentlar bu konularda seçenek + öneri hazırlar, karar vermez.
5. Agentlar birbirine `SendMessage` ile danışabilir, iş devredemez. Karar doğuran istişareler issue'ya yorum olarak işlenir.

### Sabit kısıtlar

- Push, merge, rebase, dal silme yalnızca orkestratörde (kullanıcı onayıyla merge).
- Paket kurulumu yok (gerekirse kullanıcıya sorulur). `.env` okunmaz.
- Yerelde en fazla ~15 dk'lık hesaplama; uzun eğitim Colab'da (T4), kullanıcı çalıştırır. Drive `GES/` klasörü yalnızca okunur.
- Ham veri (`data/SOLAR PANEL DET.v1i.yolo26`) yerinde değiştirilmez; türetilmiş veri yeni klasöre üretilir. `data/`, `models/`, `runs/` git dışıdır.
- Repo herkese açıktır: GitHub'a yazılan her şey herkese görünür; gizli bilgi yazılmaz.

## Proje kayıt defteri (`docs/kayit/`)

Her kullanıcı mesajından sonra, iş bitmeden kayıt düşülür. Eski maddeler silinmez/kısaltılmaz; yalnızca sona eklenir. Kullanıcı "kayıt tutma" / "bu inputumu yok say" derse o tur hiçbir dosyaya yazılmaz.

| Dosya | İçerik | Kim yazar |
|---|---|---|
| `inputlar.md` | Kullanıcı mesajı (500+ karakterse kısaltılmış) | `UserPromptSubmit` hook'u otomatik; orkestratör başlığı düzeltebilir |
| `degisiklikler.md` | Değişen yol + ne değişti, karar ve gerekçe | Orkestratör (agent raporlarından) |
| `matematik.md` | Varsayım, parametre, formül (LaTeX), sayısal sonuç + birim | Orkestratör (agent raporlarından) |

Üç dosyada aynı başlık: `## YYYY-MM-DD HH:MM — kısa başlık` (Europe/Istanbul). Alt agentlar kayıt dosyalarına doğrudan yazmaz (`katip` hariç, orkestratörün verdiği içerikle).

## Komutlar

```bash
python -m pytest -q tests                 # testler
python main.py --scenario B               # tek senaryo (GUI)
python scripts/run_scenarios.py && python scripts/comparison_report.py
```
