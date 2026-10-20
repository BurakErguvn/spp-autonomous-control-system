# Matematiksel çıkarımlar

Formüller, varsayımlar, parametreler ve sayısal sonuçlar kronolojik tutulur. Matematik yoksa madde eklenmez. Maddeler silinmez; yalnızca sona eklenir.

---

## 2026-08-13 14:21 — Model konumu, gereksiz ağırlıklar ve optimizasyon algoritmaları

Parametreler (`solver.py`): $p=2$ TL/kWh, $E=1.5$ kWh/gün, $H=30$ gün, $c_{\text{tech}}=200$ TL/saat.

Günlük kayıp ve 30 günlük fırsat maliyeti:

$$
L(h)=\begin{cases} E\cdot 0.20=0.30 & \text{hotspot}\\ E\cdot 0.05=0.075 & \text{mikro çatlak}\\ E\cdot 0.10/30=0.005 & \text{tozlanma} \end{cases}
\quad
O_i=L(h_i)\cdot H\cdot p
$$

$$O_{\text{hotspot}}=18,\quad O_{\text{çatlak}}=4.5,\quad O_{\text{toz}}=3 \text{ TL}$$

Bakım: $M_i=(s_i/60)c_{\text{tech}} + \mathbb{1}_{h\neq\text{toz}}(0.7\cdot 100+0.3\cdot 4500)$

$$M_{\text{hotspot}}\approx 1570,\quad M_{\text{çatlak}}\approx 1620,\quad M_{\text{toz}}\approx 23.3 \text{ TL}$$

Aşama 1 — MILP seçim (PuLP/CBC), $x_i\in\{0,1\}$:

$$\min\sum_i\bigl[x_i M_i+(1-x_i)O_i\bigr]=\min\sum_i x_i(M_i-O_i)+\text{sabit}$$

$$\sum_i x_i s_i\le K\cdot D=3\cdot 480=1440\text{ dk}$$

Kod must-fix'i sert kısıt değil, ceza ile zorlar: hotspot $M-O-10^6$, çatlak $M-O-5\cdot 10^5$. Mevcut sayılarla $M>O$ her sınıfta → tozlanma hiç seçilmez; hotspot/çatlak her zaman seçilir. MILP pratikte kapasite kısıtlı must-fix süzgeci.

Aşama 2 — CVRP (MTZ), $N\le 10$; $N>10$ en yakın komşu (NN):

$$\min\sum_{i\neq j}\sum_{k=1}^{K} d_{ij} c_f y_{ijk},\quad c_f=3\text{ TL/km}$$

$$u_{ik}-u_{jk}+N y_{ijk}\le N-1$$

Alternatiflerden beklenen (bu ölçek: $\sim$2–30 panel, 3 ekip):

- Seçim zaten 0-1 knapsack; CBC optimal. Greedy (fayda/süre) aynı sonucu verir.
- NN vs tam CVRP: mesafe genelde %+15–40 (klasik VRP). $N\le 10$ için CBC optimal; kod $N>10$'da NN'ye düşer — asıl kayıp burada.
- OR-Tools / 2-opt / Clarke–Wright: $N>10$'da NN'ye göre rota maliyetinde kabaca %10–30 iyileşme, tam çözüme %1–5 yakın.
- ALNS (Applied Energy 2024, büyük GES bakım rotalama): yüzlerce görevde MILP'nin çözemediği örneklerde yakın-optimal; bu tesiste aşırı.
- Ortak prize-collecting VRP: seçim+rota birlikte. Yakıt $3$ TL/km, bakım binlerce TL olduğu için bugünkü 30 panellik sahada fark küçük; uzak düşük değerli işler elenir.
- NSGA-II / çok amaçlı: maliyet–risk–enerji Pareto'su; tek skaler $Z$ yerine çözüm kümesi. Proje metninde geçiyor, kodda yok.
- Gurobi/HiGHS: aynı MILP, büyük $N$'de CBC'den hızlı; mevcut $N$ için fark saniye mertebesi.

## 2026-08-13 14:40 — YOLO26s resmi model, rota portföyü, Colab

Clarke–Wright tasarrufu ($0$ = depo):

$$s_{ij}=d_{0i}+d_{0j}-d_{ij}$$

2-opt: kenar $(i,i+1)$ ve $(j,j+1)$ yerine $(i,j)$ ve $(i+1,j+1)$; rota ters çevrilir. Kabul: $\Delta<0$.

ALNS: yok et (rastgele / worst / Shaw) + onar (greedy / regret-2). Regret:

$$r_v=c_v^{(2)}-c_v^{(1)}$$

SA kabul: $P=\exp(-(Z'-Z)/T)$, $T\leftarrow 0.995\,T$. Skor: en iyi kapsama, sonra $\min\sum_k \mathrm{tur}(k)$.

OR-Tools: PATH_CHEAPEST_ARC + Guided Local Search; maliyet $\lfloor 1000\,d_{ij}\rfloor$.

Colab free T4 $\approx 15$ GB VRAM, oturum $\le 12$ saat, boşta $\sim 90$ dk kopma. RTX 3060 Mobile $\approx 6$ GB.

| Boyut | Params | T4 batch=−1 | ~70 ep / 8550 img | Free tier |
|---|---|---|---|---|
| s | 9.5M | rahat | 2–4 sa | evet (şu an resmi) |
| m | 20.4M | ~8–16 | 4–7 sa | **hedef** |
| l | 24.8M | ~4–8 | 7–11 sa | sınırda, `save_period=5` |
| x | 55.7M | ~2–4 | 12+ sa | hayır |

COCO mAP50-95: n 40.9 → s 48.6 → m 53.1 → l 55.0 → x 57.5. Bu veri setinde s→m beklenen kazanç birkaç mAP puanı; l/x azalan getiri + kota riski.

## 2026-08-14 14:37 — Colab T4 3 GB VRAM kullanımı

PyTorch T4’ün 14 GB’ını doldurmaz; yalnızca model + aktivasyon için yer açar:

$$\mathrm{VRAM} \approx \underbrace{W}_{\text{ağırlık+opt}} + B\cdot \underbrace{A}_{\text{görüntü/aktivasyon}} \quad (\text{AMP} \approx 0.5\times \text{FP32})$$

Ekran: `GPU_mem=3.09G`, `502/1620` → epoch başına ~1620 adım ⇒ $B \approx N_{\text{train}}/1620$ (muhtemelen $B=4$ veya $8$). YOLO26s + AMP + küçük $B$ için ~3 GB beklenen. T4 boş kapasite ~11 GB; $B$ 16–32 (s) veya 16 (m) yapılabilir. AutoBatch `batch=-1` hedefi $\approx 0.6\times 14 \approx 8$ GB; 3 GB bu hedefin altında kalmış.

## 2026-08-14 14:54 — Rota algoritması seçimi ve ekip maliyeti

İki katman:

1. **MILP (PuLP/CBC)** — tamir et / ertele ve maliyet. $x_i\in\{0,1\}$, $M_i$ bakım, $O_i$ 30 günlük fırsat, $s_i$ servis (dk), $K=3$, $C=480$:

$$\min\sum_i\bigl(x_i M_i+(1-x_i)O_i\bigr)\quad\text{s.t.}\quad\sum_i x_i s_i\le KC$$

Hotspot/çatlak must-fix (büyük negatif $O_i$). Toz: $O=3$ TL $\ll M\approx 23$ TL → ertelenir. Ekip kimliği burada yok.

2. **ALNS CVRP** — seçilen panelleri 3 ekibe atar, tur mesafesini (yakıt $3$ TL/km) küçültür. Tohum: Clarke–Wright + 2-opt.

6 örnek, gerçek layout, $K=3$, $C=480$. Tümü tam kapsama + kapasite uygun.

| Örnek | $N$ | CW km | ALNS km | OR-Tools km | CW s | ALNS s | OT s |
|---|---|---|---|---|---|---|---|
| B hotspot | 2 | 0.374 | 0.374 | 0.374 | $<10^{-3}$ | 0.003 | 2.35 |
| C çatlak | 10 | 0.490 | 0.490 | 0.490 | $<10^{-3}$ | 0.022 | 2.00 |
| mixed | 15 | 0.814 | 0.794 | 0.794 | $<10^{-3}$ | 0.050 | 8.00 |
| hotspot | 20 | 0.750 | 0.691 | 0.691 | $<10^{-3}$ | 0.068 | 8.00 |
| çatlak sıkı | 24 | 1.044 | 0.941 | 0.941 | $<10^{-3}$ | 0.069 | 8.00 |
| tüm hotspot | 30 | 1.287 | 1.125 | 1.125 | $<10^{-3}$ | 0.064 | 8.00 |

ALNS, OR-Tools ile aynı $Z=\sum_k\mathrm{tur}(k)$; $N=30$'da CW'ye göre $\Delta\approx 12.6\%$. OR-Tools zaman limiti $2$–$8$ s. Seçim: ALNS.

## 2026-08-14 17:00 — QAOA QUBO deneyi ve klasik–kuantum raporu

Seçim QUBO (ölçekli bonus $B_h=5000$, $B_c=3000$; slack $y_k$; $\lambda=8\max|c_j|$):

$$
H_{\mathrm{sel}}=\sum_j\bigl((M_j-O_j)-B_j\bigr)x_j+\lambda\Bigl(\sum_j s'_j x_j+\sum_k 2^k y_k-C'\Bigr)^2+\sum_j O_j
$$

Ising: $x_i=(1-Z_i)/2$. QAOA $p$ katman: $\mathrm{RZ}(2\gamma h)$, $\mathrm{RZZ}(2\gamma J)$, $\mathrm{RX}(2\beta)$.

Aer (2026-08-14): tam sayım = CBC tüm seçim örneklerinde. QAOA $Z$ eşleşmesi:

| Örnek | kübit | CBC $Z$ | QAOA $Z$ | adet | Hamming |
|---|---|---|---|---|---|
| n4 çatlak | 6 | 4864.5 | 4864.5 | 3 | 0 |
| n6 mixed | 10 | 4723.5 | 4723.5 | 3 | 0 |
| n8 çatlak | 11 | 8113.5 | 8113.5 | 5 | 0 |
| n10 hotspot | 13 | 9492.0 | 9492.0 | 6 | 2 |
| n12 çatlak | 15 | 11362.5 | 11362.5 | 7 | 4 |
| n6 dust | 14 | 4760.9 | 3145.4 | 2 vs 3 | 1 |

CVRP $N=3,K=2$: ALNS $0.375$ km, QAOA $0.543$ km (fizibil). $N=4$ ($20$ kübit): QAOA fizibil değil. Üretim $NKT\approx 900$ kübit.

## 2026-10-20 20:15 — Proje sorun analizi (geriye dönük kayıt)

Başabaş süresi (bakım maliyeti = birikmiş fırsat maliyeti), mevcut `Parameters` ile:

$$T^{*}(h)=\frac{M(h)}{L(h)\cdot p},\qquad M(h)=\frac{s_h}{60}c_{\text{tech}}+\mathbb{1}[h\neq\text{toz}]\big(0.7\cdot 100+0.3\cdot 4500\big)$$

| Hasar | $M$ (TL) | $O_{30}$ (TL) | $T^{*}$ (gün) |
|---|---|---|---|
| hotspot | 1570.0 | 18.00 | ≈ 2617 |
| mikro çatlak | 1620.0 | 4.50 | ≈ 10800 |
| tozlanma | 23.3 | 0.30 | ≈ 2333 |

Sonuç: ekonomik terim hiçbir arızayı seçtirmiyor; seçim yalnızca amaçtaki $-10^6$ / $-5\cdot10^5$ katsayılarından geliyor (MILP fiilen öncelik sıralı açgözlü kural).

Senaryo C: toplam yol $0.424$ km → yakıt $0.424\times 3 \approx 1.27$ TL; toplam maliyet $14581$ TL'nin $\approx\%0.009$'u. Ekip yükleri 60 / 480 / 0 dk (makespan 480 dk; dengeli çözümde 180 dk).

Veri seti (yerel, remap sonrası): karma poligon/bbox dosyaları Ultralytics'te atılınca kayıp — train çatlak $1979/3533$ (%56), toz $2237/4267$ (%52); valid çatlak $236/344$ (%69), toz $317/439$ (%72). Train'de hotspot örneklerinin %100'ü gri (termal) görüntülerde, toz örneklerinin %95'i renkli.

YOLO26m (Colab T4, 70 epoch) doğrulama: mAP50 genel 0.501; hotspot 0.795, mikro çatlak 0.395, tozlanma 0.313 (valid: 499 görüntü, 762 örnek).

## 2026-10-20 20:40 — #2/#3 tester sonucu: PASS (koşullu)

- Poligon → eksen-hizalı bbox (normalize koordinat): $x_1=\min_i x_i,\ x_2=\max_i x_i$, $y_1=\min_i y_i,\ y_2=\max_i y_i$; $[0,1]$'e kırpma; $c_x=(x_1+x_2)/2,\ w=x_2-x_1$ (y için aynı); $w<10^{-4}$ veya $h<10^{-4}$ ise dejenere. Tester'ın bağımsız türetmesi 9196 dosyanın 0'ında fark verdi (tol $2\cdot10^{-6}$).
- Gruplama: kaynak stem ∪ çevirme-duyarsız dHash ($\le 4$ bit) ∧ küçük resim NCC $\ge 0.85$, union-find; 9196 görüntü → 2838 grup (en büyük 66). Bölme 80/10/10, seed 42.
- Sonuç: hotspot 10348 / 1294 / 1291 instance (%80.0/10.0/10.0); mikro_catlak 4038 (remap sonrası 51 yinelenen satır tekilleştirildi), tozlanma 4948. Arka plan oranı train %30.9, valid %33.4, test %31.7.

## 2026-10-20 21:10 — Arıza maliyetleri araştırması ve oturum devri

Kaynak: `docs/arastirma/ariza-maliyetleri.md` (dal `worktree-agent-ac97f9fac39b3d091`). Notasyon: $n_f$ etkilenen modül, $P$ modül gücü (kWp), $Y_d$ özgül verim (kWh/kWp/gün), $c_e$ enerji fiyatı (TL/kWh), $H$ ufuk (gün), $N_{sub}$ bypass diyot sayısı, $w$ ücret (TL/sa).

- Modül kayıp oranı: $L_f = 1/N_{sub}\approx 0.33$ (aktif bypass, IEA PVPS T13-01 §6.2.2); çatlak: $L_f=\max(0,\alpha(a_{in}-0.08))$, $\alpha$ [D]; modül/string devre dışı: $L_f=1$ (string açık devrede $n_f=S$).
- Fırsat maliyeti: $C_{opp}=n_f L_f P Y_d c_e H$.
- Tozlanma (doğrusal birikim, yağışla sıfırlanma): $C_{opp}^{toz}=nPY_dc_e\,\tfrac{rH^2}{2}$, ortalama kayıp $rH/2$. Konya $r=0.00296$/gün (Erbakan Üniv. tezi 2024) → $H=30$ gün için ort. ≈ %4.4; mevcut kod sabit %10/ay.
- Bakım: $C_{maint}=\tfrac{t_f}{60}n_{ekip}w+\sum_k p_{f,k}m_k+c_{yol}$; geri ödeme $T_{pay}=C_{maint}/(365\,n_fL_fPY_dc_e)$ yıl.
- Modül değişimi: 0.10 €/Wp (600 Wp → 60 €) + montaj ≈30 € (Köntges, IEA PVPS T13 çalıştayı, 2025-10-23). %100 kayıplı modül ≈1 yılda, %10 kayıplı ≈10 yılda öder.
- Tespit (Avrupa tipik, Tsanakas 2025): drone IR 450–650 €/MW, 0.4–0.8 sa/MW; drone RGB 250–400 €/MW; saha EL 1500–2500 €/MW, 2–4 sa/MW; I-V 900–1400 €/MW, >4 sa/MW. IEA T13-10:2018: el tipi IR 3.75–5 sa/MW, drone IR 1.25–2.5 sa/MW (fark büyük olasılıkla hazırlık süresi [T]).
- İşçilik tabanı: 2026 asgari ücret işveren maliyeti ≈39.2–40.9 bin TL/ay, 225 sa/ay ile ≈182 TL/sa (araştırmacı hesabı; koddaki 200 TL/sa yakın, teknisyen ücreti kaynaksız).
