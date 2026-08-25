you really have to know the orange line + the ohlc data man and try do know the relation
if i were to code 
it would be like this
looping on candles okay 
selling flow
i.low < i-1.low - and also  i.high < i-1 high then  marker point shifts to i.low (the normal selling where the next cnadle just broke the low not the high) 
now two case on above
1: it broke both high + low
now we check if candle = green
if green mark low then high of the same candle cuse flow is from bottom to up
if red so first we mark the first candle low then next candle high then low cuse red flow is top to bottom
this was the volatile candle 

now comes the case of insider candle like we have at 21 aug 2026 9:25 case
if flow is selling 
so first candle is red
red candles high mark then same candles low
as the first cnadle is red 
so next candle to be insider that means that is definately green
so we go like
first candle high marked then low marked
then we mark high of the insider candle 
then if the third candle broke the low so we mark the low of it
if not then it means it broke the high of the insider candle so we skip the insider candle 
and from first candle's low we mark high of third candle ... 

you getting the flow and logic here??

vice versa for buying flow
buying flow means
first candle is green and next candle broke the high of that's it not low

now the insider candle for green case will be definately red that's 100%
so as the first candle is green that mean we go from low mark then high cuse only that way it will be green

now second candle is insider now it depends on the next + 1 candle what it did but whatever for insider till we can handle it like
from first cnadle high we mark low of the insider candle's low
now if the 3rd candle broke high 
so then we go insider candle's low to high of 3rd candle
but if the tthird candle broke low of the insider then we skip the insider 

so its about skipping too

think about it

and also we have to make the hardcoded line orange

the another controversial case is
after insider candle there is volatile candle meaning breaking high and low of insider candle
we are missing this case
two cases can be here
insider = green
insider = red

order will be like
1st candle = green and marker is at green low
2nd = insider red
3rd = volatile green
in this case

1st low to 2nd high then 3rd low


another case

1st candle = green and marker is at green low
2nd = insider red
3rd = volatile red

1st low  then 2ns high then 2nd low then 3rd high....  (yup same candle high and low insider)

vice versa for first candle being red .. then insider will be definately green now we have 2 cases volatile being 1: green 2: red



another extreme case is 
after insider we have volatile..

two patterns i'm noticing
1: if  volatile is in range of the prev high low mark (from back marking we will be having high and low marker nah )
yeah so if we are inside it then we have to skip the insider we directly mark the volatile which we are are currently doing
for 11:00 case see 
11:00 insider candle and volatile candle both are inside the high low range of prev markers
high being at 10:55 candle high and low being at same 10:55 candle and bothh insider and volatile are inside it now in this case we have to skip the insider 
so orange line will follow like - 10:55 low to direct volatile candle's high which is correct

2: now if other case here is the volatile candle is out of the range of the prev markers
now we have to mark the insider
example 20 aug 2026 
12:25 prev low is here 
12:15 prev high is here
12:30 is the insider
12:35 is the volatile candle and it broke the prev low means low of 12:25 
now we can't skip insider
now we mark like from 12:25 low (green candle) then 12:30 high (red candle which is insider)
then low of 12:35 (green candle which is volatile)

vice versa 


nahh still misses the range break case insider then volatile case

let me mark orange for 20 aug 2026 okay
make this hardcoded to see the difference
first 10:35 low will be marked but currently 10:40 is marked
as 10:40 is insider and the 10:45 broke its high so this is general case this is not insider and volatile case although low of both 10:40 and 10:45 is same but it didn't broke so can't consider it 
then 10:45 broke high of the 10:40 insider candle so we skip the 10:40 candle entirely
so we go directly from 10:35 low to10:45 high
then mark goes to 10:55 low
then all good till 12:20
now from here
12:25 low will be marked
12:30 is insider and 12:35 is volatile and it broke the low of 12:25 candle so
12:25's low we go insider candle 12:30's high then 12:35's low 

then all good till 13:00
13:05 is insider and 13:10 is volatile and it broke the range too so we can't skip insider that's the rule so we mark the insider like
from 13:00 high to 13:05 insider's candle's low
to 13:10 volatile candle's high to 13:15 low

umm if we fix till here and algo adapts then ahead cases will also fix 

now mark orange harcoded like this for 20 aug too 
we already have it for 21 don't touch that 


umm now i think need to hardcode orange line on 24 aug 2026 too
here where i would change 
9:55 low to 10:00 high to 10:05 low to 10:20
can you find the reason???
which case is this..???

cuse this seems odd because this breaks the basic fundamental of zig zag
we can't go zig zig or zag zag haha 
you know what i means
like we can't mark two things in a row...
like high then high and vice versa
so what i'm noticing is it goes to 10:10 high to 10:20 high 
so high to high 


and vice versa can't happen too

umm
there are some cases wehere the marking is not correct man

starting from 19 aug 2026
see
it should go like (9:50 high to  10:00 low to 10:00 high to 10:20 low..... yup same candle low then high

why i say see 
9:55 is insider 10:00 is volatile now 10:05 is again an insider ... damn this is the case for alteration
insider then volatility then again insider...

that's new right??

now so getting back
10:00 low than high will be marked 

see how i'm noticing in the chart is when ever there is a high and it is not marked that seems odd in this case

high is marked at 10:05 yet we have a wick which is obivously seeing an higher yet not marked .. 

so check rule can be 
the current marker high or low 
for high there shouldn't be any candle high which  should go higher than it nah
vice versa for the current low marked


there can be alteration pattern the other way too like this time it was insider then volatile then insider 

it can repeat too for n time
or other way around like first this time is volatile then insider then volatile so make sure we are covering both

and vicersa too please