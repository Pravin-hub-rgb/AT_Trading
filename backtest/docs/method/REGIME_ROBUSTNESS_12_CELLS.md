# regime robustness — 12 half-years, every candidate, side by side

Date: 2026-10-09. The question this file answers, in the owner's words:

> "still that IS stands out because of the regime it holds not — and we are
> looking for something joh each regime mai tike… covid ka area tha panic and
> other stuff crash wagera"

---

## first, what HTF means, because it came up unclear

**HTF = Higher Time Frame.** In this system there are two clocks:

| | kya hai | is book me kaam |
|---|---|---|
| **LTF** | 15-minute bars | **signals yahin bante hain** — har trade 15m pe decide hota hai |
| **HTF** | 1-hour bars | **context yahin se aata hai** — 1h dekh kar book decide karti hai market ka regime kya hai, phir 15m pe trade karti hai |

`exp_persist=7` usi 1h context ka memory hai — "agar regime strong hai to usko
mat badlo jaldi." `htf_regime` field jo har trade pe lagta hai (`flip` ya
`decisive`) **1h wala hissa** hai. LTF pe koi alag clock nahi hai.

**Ye sweep isliye interesting hai** kyunki agar 15m pe koi filter kaam karta hai
to wo **1h regime ke andar** kuch alag karta hai — matlab 15m ka signal
1h ke context me meaningfully different hota hai.

---

## the 12 half-years, both eras, every candidate

**IS = 2023-01 → 2026-09. OOS = 2021-01 → 2022-12. Dono milaye ja rahe hain
kyunki dono abhi tak dekh chuke hain (2021-22 holdout nahi hai — see
`OOS_IS_NOT_A_HOLDOUT.md`).**

| half-year | champ_long **(aapki)** | **sig_multi** | sig_full | union | atr_low |
|---|---:|---:|---:|---:|---:|
| 2021-H1 | +43.7 (84t) | +39.9 (47t) | +39.6 (38t) | +46.2 (108t) | +47.5 (71t) |
| 2021-H2 | +34.7 (78t) | **+40.5** (43t) | +35.8 (37t) | +48.8 (114t) | +50.9 (85t) |
| **2022-H1** ← COVID crash | **+92.4** (79t) | +80.2 (52t) | +60.4 (37t) | **+154.7** (119t) | +126.1 (85t) |
| 2022-H2 | **+68.8** (70t) | +59.3 (52t) | +58.7 (39t) | +54.1 (101t) | +56.3 (74t) |
| 2023-H1 | +29.0 (64t) | **+91.1** (50t) | +59.3 (33t) | +22.0 (97t) | +12.4 (71t) |
| **2023-H2** ← the big rally | **+143.5** (60t) | +48.5 (38t) | +32.2 (28t) | +161.9 (108t) | **+222.6** (95t) |
| 2024-H1 | +58.8 (75t) | **+67.6** (48t) | +66.6 (36t) | +81.2 (116t) | +66.6 (82t) |
| 2024-H2 | +55.3 (90t) | **+73.2** (39t) | +47.7 (32t) | +81.2 (127t) | +137.8 (111t) |
| **2025-H1** | **−0.7** ⚠️ (60t) | +40.5 (33t) | +20.4 (25t) | +27.2 (104t) | +16.5 (81t) |
| 2025-H2 | **+138.2** (80t) | +65.6 (48t) | +35.0 (34t) | +116.4 (107t) | +74.3 (81t) |
| 2026-H1 | **+56.2** (72t) | +28.1 (55t) | +18.8 (33t) | +50.9 (110t) | +92.5 (93t) |
| 2026-H2 | +53.0 (27t) | **+70.0** (18t) | +15.7 (13t) | +39.1 (44t) | +98.7 (27t) |

---

## the answer to "something joh har regime me tike"

### Negative half-years, out of 12

| book | negative cells | verdict |
|---|---:|---|
| **`champ_long`** (aapki shipping) | **1** | fails **2025-H1 at −0.7R** |
| **`sig_multi`** | **0** | **12/12 positive** |
| `sig_full` | 0 | 12/12 positive |
| `union` | 0 | 12/12 positive |
| `atr_low` | 0 | 12/12 positive |

**`sig_multi` kabhi negative half-year nahi hua. Aapki shipping book hui hai — 2025-H1 me −0.7R.**

**Ye aapke sawaal ka seedha jawab hai:** "har regime me tika hua" — `sig_multi` woh
book hai jo 12 me se 12 cells me positive hai.

### Par — aur ye bhi sach hai

**`sig_multi` aapki book se 12 me se 6 cells me kam kamata hai:**
2021-H1, 2022-H1, 2022-H2, 2023-H2, 2025-H2, 2026-H1.

**Aur COVID wale saal me aapki book jeetti hai:** 2022 me `champ_long` +161.3R,
`sig_multi` +139.4R. **2022-H1 me +92.4 vs +80.2.**

---

## the trade-off, stated as plainly as it can be

| | `champ_long` (aapki) | `sig_multi` |
|---|---|---|
| **negative half-year** | 1 (2025-H1) | **0** |
| cells where it's negative | fails | **never** |
| **COVID year (2022)** | **+161.3R** 🏆 | +139.4R |
| 2023 (rally year) | **+172.4R** 🏆 | +139.6R |
| total, both eras | **+773.0R** | **+704.9R** |
| out-of-sample max DD | 11.88R | **7.64R** |
| out-of-sample win rate | 37% | **47%** |

**Aapki book zyada kamati hai. `sig_multi` kabhi haar nahi jaati.**

**Ye "consistent vs profitable" ka trade-off hai — dono ek saath nahi.** Aur ye
2022 ke data se aata hai, jo aap sahi keh rahe ho ek **alag regime** tha (COVID
panic + bear market). Us saal aapki book ne +161.3R diye, `sig_multi` ne +139.4R.

---

## iska matlab kya hai — teeno options honestly

**1. `sig_multi` "har regime me tika" hai — par usse zyada paisa kamane ki**
himmat nahi hai. Ye aapke framework ke "stability > peak return" wale hisse se
sahi fit hota hai, jo aapke doc me likha hai: *"Smoothness is nice. **Stability is
more important.**"*

**2. Par 2022 ka data aapke sawaal ka seedha jawab bhi de raha hai** — wo
**crash regime** tha, aur wahan aapki book **+26R zyada** kamayi. Agar crash me
zyada kamana hai toh `sig_multi` galat choice hai. Agar crash me **garna nahi** hai
toh sahi choice hai. **Ye aapka decision hai, data ka nahi.**

**3. Teeno books me ek hi cheez common hai:** `champ_long` bhi, `sig_full` bhi,
`union` bhi, `atr_low` bhi — **koi bhi har half-year negative nahi hai** (shayad
`champ_long` hi ek exception). Toh **"har regime me tika" koi bhi book ke liye
bhaari criterion nahi hai** — ye zyada tar ban jata hai. Asal sawal ye hai ki
**aapko crash me zyada paisa chahiye, ya kam nuksan.**

---

## `union` — jo maine pehle reject kiya tha, wo is table me strong hai

Main `union` ko drawdown aur tail ke karan reject kiya tha. **Regime table me wo
kafi strong dikhta hai** — har cell positive, aur 2022-H1 me **+154.7R**, sabse
zyada:

| book | negative cells | 2022 (COVID year) | both eras total |
|---|---:|---:|---:|
| `champ_long` | 1 | +161.3R | **+773.0R** |
| `union` | **0** | **+208.8R** 🏆 | **+884.0R** 🏆 |
| `atr_low` | 0 | +182.4R | +812.0R |
| `sig_multi` | 0 | +139.4R | +704.9R |
| `sig_full` | 0 | +119.1R | +490.6R |

**`union` aur `atr_low` 2022 me aapki book se bhi zyada kamate hain.** Wo meri
pehli wali "drawdown veto" se marte the — jo maine khud withdraw kar chuka hoon.

**Iska matlab ye nahi ki wo ab adopt ho jayein.** Drawdown abhi bhi 23.8R
(`union`) aur 28.9R (`atr_low`) in-sample hai, aur aapka budget 20R hai. **Par ye
unka dismissal nahi hai — ye unka proper characterization hai.**

---

## verification

| check | result |
|---|---|
| half-year split | 12 cells, both eras accumulated — first script overwrote OOS with IS and was fixed |
| books covered | all 5, from engine, no hand-entered numbers |
| registry | untouched in this file |
| shipping book | unchanged |

One script bug caught and fixed while producing this: the first version keyed its
accumulator by book and let the IS era overwrite the OOS era, so it silently
printed **4 half-years instead of 12** and made `union` look weak for no reason.
Both eras are now accumulated into the same cells.