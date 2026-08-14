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
