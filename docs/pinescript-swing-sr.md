# Swing High/Low Support Resistance — PineScript (source)

Original TradingView indicator we are porting to Python + lightweight-charts.
We will use it on the **daily** chart to mark major swing highs (resistance,
red) and swing lows (support, green), with horizontal levels extended forward.

```pinescript
//@version=6
indicator("Swing High/Low Support Resistance", overlay=true, max_lines_count=100, max_labels_count=50)

// === User Inputs
swingLen = input.int(10, "Swing Detection Length", minval=1)
numLevels = input.int(5, "Number of S/R Levels to Display", minval=1)
lineLookahead = input.int(50, "Extend Lines Forward (Bars)", minval=5)

// === Arrays to store levels and lines
var float[] swingHighs = array.new_float()
var float[] swingLows = array.new_float()
var line[] highLines = array.new_line()
var line[] lowLines = array.new_line()

// === Detect Swings
ph = ta.pivothigh(high, swingLen, swingLen)   // Detect swing high
pl = ta.pivotlow(low, swingLen, swingLen)     // Detect swing low

if not na(ph)
    array.unshift(swingHighs, ph)
    if array.size(swingHighs) > numLevels
        array.pop(swingHighs)

if not na(pl)
    array.unshift(swingLows, pl)
    if array.size(swingLows) > numLevels
        array.pop(swingLows)

// === Clean up old lines
if bar_index > lineLookahead
    for i = 0 to array.size(highLines) - 1
        if array.size(highLines) > 0
            line.delete(array.get(highLines, i))
    array.clear(highLines)
    for i = 0 to array.size(lowLines) - 1
        if array.size(lowLines) > 0
            line.delete(array.get(lowLines, i))
    array.clear(lowLines)

// === Extend new lines forward for each detected level
if bar_index > lineLookahead
    for i = 0 to array.size(highLines) - 1
        if array.size(highLines) > 0
            line.delete(array.get(highLines, i))
    array.clear(highLines)
    for i = 0 to array.size(lowLines) - 1
        if array.size(lowLines) > 0
            line.delete(array.get(lowLines, i))
    array.clear(lowLines)

// Optional: Plot labels at swing points for reference
if not na(ph)
    label.new(bar_index - swingLen, ph, "Swing High", color=color.red, style=label.style_label_down, textcolor=color.white)
if not na(pl)
    label.new(bar_index - swingLen, pl, "Swing Low", color=color.green, style=label.style_label_up, textcolor=color.white)
```

## Behavior we must replicate

| PineScript | Our port |
|---|---|
| `ta.pivothigh(high, swingLen, swingLen)` | bar `i` is a swing high iff `high[i] > max(high[i-swingLen..i-1])` and `high[i] > max(high[i+1..i+swingLen])` |
| `ta.pivotlow(low, swingLen, swingLen)` | bar `i` is a swing low iff `low[i] < min(low[i-swingLen..i-1])` and `low[i] < min(low[i+1..i+swingLen])` |
| Keep last `numLevels` highs / lows | Select the most recent `numLevels` swings of each kind |
| Horizontal line extended `lineLookahead` bars forward | Red line (resistance) / green line (support) from the swing bar to bar+`lineLookahead` |
| "Swing High"/"Swing Low" labels | Small filled rectangle marker at the swing point (red above high, green below low) |

## Defaults used in the app

- `swingLen = 10`, `numLevels = 5`, `lineLookahead = 50`
- Applied on the **daily** chart (data: `data/nifty_daily.csv`)