# ENTRY THEORY — Kaise Entry Decide Hoti Hai

> Tumhari rules, sirf yahan likha hai jo tumne bola.

---

## Core Rule ( Tumhara Rule )

**Trade just after the first swing — no matter if it's 9:34 or 10:30**

```
For BUYING → wait for selling swing (first swing) → then BUY
For SELLING → wait for buying swing (first swing) → then SELL
```

---

## Trade Mode ( Aggressive vs Conservative )

| Mode                | Entry                                      |
| ------------------- | ------------------------------------------ |
| **aggressive** ⚡   | **First pivot break after FS**             |
| **conservative** 🐢 | **Second pivot break after FS (1st skip)** |
| **skip** ✕          | No trade                                   |

**Aggressive:** FS ke baad jo bhi pehla pivot break ho uspe entry (1st break)
**Conservative:** FS ke baad pehla break skip, dusre pivot break pe entry (2nd break)
**Skip:** Nahi mila → no trade that day

---

## Entry Process

```
For BUYING:
  → mark recent low pivot (selling swing ka low = swing end point)
  → entry must be ABOVE this low
  → pivot break = ENTRY (only if price above swing end line)

For SELLING:
  → mark recent high pivot (buying swing ka high = swing end point)
  → entry must be BELOW this high
  → pivot break = ENTRY (only if price below swing end line)
```

---

## Aggressive Day Entry ( First Pivot Break )

```
1. Desired swing aane tak wait karo
   (BUYING chahiye → selling swing aane tak wait)
   (SELLING chahiye → buying swing aane tak wait)

2. Swing complete hone ke baad
   → FIRST pivot break = ENTRY
   → entry price must be above/below swing end line

3. Aggressive = FIRST PIVOT BREAK
```

---

## Conservative Day Entry ( Second Break )

```
1. First swing complete hua → desired direction swing ka intezaar
   (BUYING chahiye → buying swing, SELLING chahiye → selling swing)
   Second swing hi desired de de to usi pe, nahi to third/fourth...

2. Desired swing complete hone ke baad
   → FS ke baad ke pivots dekho (FS ke andar wale nahi, FS end ke baad wale)
   → pehla pivot break = SKIP (1st break ignore)
   → dusra pivot break = ENTRY (2nd break pe trade)

3. Conservative = FS ke baad SECOND PIVOT BREAK (1st skip, 2nd entry)
   Example 27 Aug 2026 (bearish -> SHORT, FS2 buying 09:37->09:49 FS@09:50):
     - 09:51 L24206.5 pivot banta hai (FS2 ke baad)
     - 09:55 low 24200.85 <24206.5 -> 1st break -> SKIP
     - 09:58 low 24190.15 <24200.85 -> 2nd break -> SHORT ENTRY 09:58
   Aggressive hota to 09:55 pe hi entry ho jati.

4. Agar second bhi desired direction nahi deta
   → WAIT KARO — third, fourth ... 15th swing tak
   → desired direction ka swing aaye ga to trade (data khatam hone tak)
   → swing END price cross ho jaye to reference Naye swing pe shift ho jata hai
```

---

## Entry Price — Swing End Line

```
For BUYING:
  → Entry price must be ABOVE selling swing's LOW (swing end point)

For SELLING:
  → Entry price must be BELOW buying swing's HIGH (swing end point)
```

---

## Swing End Line Traversal (replaces old "First Swing Breach Rule")

```
OLD rule (REMOVED): swing end breach → no more trades that day. Not correct.

NEW behaviour:
  → Swing end cross hone ka matlab: swing abhi extend ho raha hai
  → Reference swing naye (same-direction) swing pe shift ho jata hai
    (selling swing ka low aur neeche gaya → naya selling swing end = reference)
  → Kabhi bhi day void nahi hota — engine desired swing ka intezaar karta hai

Safety sirf ENTRY ke waqt check hoti hai (Swing End Line, upar wala rule):
  For BUYING:  entry price must be ABOVE selling swing's LOW (current reference)
  For SELLING: entry price must be BELOW buying swing's HIGH (current reference)
```

---

## One Target Per Day Rule

```
If first trade hits TARGET (3R) → no second trade that day, regardless of setup
If first trade is SL / cost-to-cost / ft_fail → second trade allowed (max 2 entries)

Example: 25 Aug, first trade gave TARGET → second trade at next pivot break is SKIPPED
```

---

## SL ( Stop Loss )

> "SL toh bhai hum woh drop down se kuch bhi select kar sakte hain"

SL ke liye dropdown use karo — jo comfortable lage woh lo.

---

## 28 Aug 2026 — Example

- Tumne bola: "28 aug is aggressive day"
- Entry = **FIRST pivot break**
- BUYING → entry above selling swing low
- SELLING → entry below buying swing high
- Time: 9:34 bhi, 10:30 bhi — no cutoff
- SL: dropdown se jo comfortable ho

---

## Summary

|                | Aggressive ⚡                         | Conservative 🐢                        |
| -------------- | ------------------------------------- | -------------------------------------- |
| Entry on       | **1st pivot break after FS**          | **2nd pivot break after FS (1st skip)**|
| Entry position | Above/below swing end line            | Above/below swing end line             |
| Breach rule    | Low/high never breached after 1st FS  | Low/high never breached after 1st FS   |
| One target     | 1st hits TARGET → no 2nd trade        | 1st hits TARGET → no 2nd trade         |
| Skip if        | Breached → no trade                   | Breached or second doesn't give desired|
| Time           | Any (9:34 bhi, 10:30 bhi)             | Any                                    |
| SL             | Dropdown se select karo               | Dropdown se select karo                |
| Example 27Aug  | 09:55 entry (1st break)               | 09:58 entry (2nd break, 09:55 skip)    |
