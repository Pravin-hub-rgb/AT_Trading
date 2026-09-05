the swing we are showing on the 1min chart we wanna show them exact
with some modification like
we already have zigzag pinescript i need a pinescript which marks swings that's it ...
which can be marked on any time frame i change to on the trading view
ummm i can mark like each day selector like if selected so like we start from frist candle of the day if now selected .. like toggled off or unchecked then it doesn't caare about the day so there is no cut off it just keep on connecting the candles ...
so like ... suppose it is toggled of and like we are oin btc which is 24/7 right so if that day is cheked so we start the swing fomr 00:00 to 23:59 okay and from next day we start from 1st candle ... if not we just keep on flowing ... doesn't get cut at the day end ...

how we do this??
so like the first candle is loaded on the trading view right we start from there ... and it just keeps on working ...

i'm saying this because the flowline pine script which is right now i've deployed it it only shows on few days .. so it might have limit that i will work for x candles .. we don't want that limit here ..


- issues 
1. pine marks and candles are not connected, they just drift away from each other when i drag 

2. and the time frame which is selected we use them for calculation .. it shouldn't be like we are on 10min time frame yet it still it uses 1min tf .... it should be using 10min nonly cuse we are on 10 min tf ..

3- it seems broken cuse .. like .. 
every other candle i see fs, flip b1 no reason at all 
i think you should do deep research  how we are curently showing the swing on the chart althoug those are only for 1min but we tryna make the pine flexible her e..