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
