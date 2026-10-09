# `fsent_sig_multi` — registered. What it is, why it works, and what is still unknown

Date: 2026-10-08. Harness: `exp_sig_multi.py`, registration pins from
`exp_register_sig_multi.py`. Registry: 152 books (was 151).
**Registered as a candidate. NOT adopted. NOT promoted.**

---

## PART 1 — plain explanation first, numbers later

### Aapki book kya karti hai

`sig_full` **ek hi position** leti hai. Ek trade khula hai to agla signal aaye tab bhi wo **wait karti hai**, jab tak pehla band na ho.

### Ye book kya karti hai

**Wahi signals. Bus ek position hone ki kami nahi hai.**

Ye lagbhag aise hai jaise aap shop pe line me khade ho:
- **Aapki book (serial):** ek customer aaya, serve karo, agra intezaar karo
- **Ye book (multi):** ek customer aaya aur dusra bhi aa gaya — **dono ko saath serve karo**

**Signals bilkul same hain.** Sirf itna hai ki ek ke chalte chalte doosra bhi le liya jaata hai.

### Ye kaam kyun karta hai

Maine naye data (OOS) me count kiya:

| | kitne |
|---|---:|
| Total naye trades | **50** |
| Jinme pehle se ek position khuli thi | **48** |
| Jinme pehli position **band** ho chuki thi | **2** |

**Yaani 50 me se 48 trades aise lage jahan serial book bas khali baithi rehti.**

Aur in 50 me se:
- **47** usi direction me lage jo position pehle se khuli thi (same bet me aur add)
- **3** opposite direction me (1 real hedge)

**Ye naye trades +25.1R kamaye** (46% win rate). **Jo 7 trades serial book ne liye the jo multi ne nahi liye — wo −0.3R.**

**Net +25.4R. Bas.**

Purane data (IS) me bhi wahi:
- 108 naye trades, **104** khuli position ke dauraan lage
- **+186.2R** kamaye, 53% win rate
- Net **+188.8R**

### Ek zaroori baat

**Ye "signal behtar" nahi hai.** Signal to bilkul wahi hai. **Ye sirf itna bolta hai ki ek position chalte chalte doosri bhi leni chahiye.**

---

## PART 2 — numbers

### Aapki shipping book ke against

| era | book | trades | net | **DD** | **WR** |
|---|---|---:|---:|---:|---:|
| IS | aapki `champ_long` | 528 | +533.4 | 13.4 | 40% |
| IS | **`sig_multi`** | 329 | **+484.6** | 13.4 | **46%** |
| OOS | aapki `champ_long` | 311 | **+239.6** | 11.9 | 37% |
| OOS | **`sig_multi`** | 195 | **+219.8** | **7.6** | **47%** |

**Naye data me:** aapke book ka **92% paisa**, **63% trades** par, **64% drawdown** par, aur **10% zyada win rate.**

### Apni parent book ke against

| era | parent (serial) | `sig_multi` | badlav |
|---|---|---|---|
| IS net | +295.8 | **+484.6** | **+188.8** |
| IS DD | 10.8 | 13.4 | +2.6 |
| IS WR | 41% | **46%** | +5pp |
| OOS net | +194.4 | **+219.8** | **+25.4** |
| OOS DD | 6.96 | 7.64 | +0.68 |
| OOS WR | 46% | **47%** | +1pp |

---

## PART 3 — teeno gates

### Gate 1: Period control — **99% bacha** ✅

Ye test poochta hai: *"ye naya faayada asli hai, ya sirf us samay ka hai jab market acha tha?"*

Iske liye half-year ka hisaab (har 6 mahine) adjust karte hain, phir dekhte hain bacha ya nahi.

| era | raw gap | **period control ke baad** | MDE | |
|---|---:|---:|---:|---|
| IS | +1.5600 | **+2.1619** | 1.8920 | ✅ **powered** |
| OOS | +0.4452 | **+0.3303** | 2.1999 | ⚠️ **underpowered** |

**MDE = "test kitna chhota effect pakad sakta hai."**

- **IS me:** effect 2.16, test 1.89 tak pakad sakta hai → **result real hai** (t = 2.24, bootstrap +1.85)
- **OOS me:** effect sirf 0.33, par test 2.20 tak pakad sakta hai → **direction pata hai, size pata nahi**

**Do eras me 99% bacha — ye regime-proxy NAHI hai.** Repo me jo ATR% ceiling tha wo yahan nahi hua.

### Gate 2: Half-year partition — **12/12** ✅

Har 6 mahine ka hisaab, dono taraf ka:

| era | serial | sig_multi | kaun aage |
|---|---:|---:|---|
| IS 2023-H1 | 59.3 | 91.1 | ✅ |
| IS 2023-H2 | 32.2 | 48.5 | ✅ |
| IS 2024-H1 | 66.6 | 67.6 | ✅ |
| IS 2024-H2 | 47.7 | 73.2 | ✅ |
| IS 2025-H1 | 20.4 | 40.5 | ✅ |
| IS 2025-H2 | 35.0 | 65.6 | ✅ |
| IS 2026-H1 | 18.8 | 28.1 | ✅ |
| IS 2026-H2 | 15.7 | 70.0 | ✅ |
| OOS 2021-H1 | 39.6 | 39.9 | ✅ |
| OOS 2021-H2 | 35.8 | 40.5 | ✅ |
| OOS 2022-H1 | 60.4 | 80.2 | ✅ |
| OOS 2022-H2 | 58.7 | 59.3 | ✅ |

**12 me se 12. Ek bhi cell ulta nahi.**

**Par sach:** pehle do OOS cells almost barabar hain (+39.6 vs +39.9, +35.8 vs +40.5). **Poora faayada 2022 ke do half-years me aata hai.**

### Gate 3: Tail — **har jagah behtar** ✅

Top winners hatao, dekho kitna paisa bacha:

| | serial | **sig_multi** |
|---|---:|---:|
| IS — top 10 hataye | 22.0% | **40.1%** |
| OOS — top 10 hataye | 22.4% | **30.7%** |

**Isse accha hua.** Zyada trades ne tail dilute kiya, concentrate nahi — jo usually ulta hota hai.

---

## PART 4 — do galtiyan jo is dauraan mili

### 1. Sibling test null aaya — **wo bug tha, result nahi**

Maine ye arm multi books pe lagane ki koshish ki. **Byte-identical** result aaya — jo impossible hai.

**Wajah:** multi books me `exp_mltf=True` hota hai, jo harness me `max_positions` gate ko bypass kar deta hai. **Unke liye ye knob dead hai.**

`sig_full` me `exp_mltf` **absent** hai → gate asli me kaam karta hai → **ye arm real hai.** ✅

**Ye doosri baar hai jab null result ne bug bataya.**

### 2. Registration ke pins — convention sahi honi chahiye

`n = raw len(trades)`, `net` alag function se, `dd` open trades skip karke. **Ye teenon alag hain.** Is hafte teen harnesses galat convention use karke **false mismatch** diye (net bilkul same tha).

`exp_fastcheck` PASS — **har pinned field reproduce hua.**

---

## PART 5 — kya BAKI hai (ye important hai)

### Ek knob, free option

Concurrency cap — kitni positions ek saath khul sakti hain:

| cap | IS net | IS DD | OOS net | OOS DD |
|---|---:|---:|---:|---:|
| none | +484.6 | 13.4 | +219.8 | 7.6 |
| 2 | +451.1 | **12.3** | **+229.7** | **7.0** |
| **3** | +483.1 | **12.3** | +219.8 | 7.6 |

**Cap 3: purane data me sirf 1.5R kam, naye data me zero kam, drawdown dono me kam.**

### Concentration kahan hai

**69% trades aise lage jahan koi aur position open nahi thi.** Ye crowded book nahi hai — **kabhi kabhi do position leti hai.**

Max depth: IS me 5, OOS me 4.

---

## Faisla

### ✅ Register ho gaya — `fsent_sig_multi`

| | |
|---|---|
| registry books | 151 → **152** |
| parent (`sig_full`) | **unchanged** |
| aapki shipping book | **unchanged** (528 / +533.37 / 13.42, 311 / +239.59 / 11.88) |
| retired books | **85, unchanged** |
| fastcheck | **PASS** |

### Kyu adopt nahi

1. **OOS me size establish nahi hui** — b = +0.33, MDE = 2.20
2. **Effect 6 guna kam** naye data me (+2.16 → +0.33)
3. **Pehla OOS half-year almost zero** (+39.6 vs +39.9)
4. **Siblings test nahi hua** — multi books pe ye knob kaam hi nahi karta
5. **Doosre serial variants** ke saath compare nahi kiya

### Asli number jo aage carry karna hai

**IS ka +2.16R/trade mat lijiye.** Wo powered hai par forward expectation nahi.

**OOS ka +0.33R/trade** — direction pakki hai (99% bacha, 12/12 cells), par size abhi tak prove nahi hui.

**Aage ka kaam:** forward time. Ye dono eras ka 6× ka farak in-sample research se nahi, sirf naye data se band hoga.

---

## verification

| check | result |
|---|---|
| `exp_fastcheck fsent_sig_multi` | **PASS** — har pinned field reproduce |
| differs from parent | **exactly one value: `max_positions`** |
| parent + shipping book pins | unchanged |
| registry count | 151 → 152 |
| retired count | 85, unchanged |
| decomposition assert | exact in both eras |