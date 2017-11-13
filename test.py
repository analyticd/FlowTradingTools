import numpy as np

Window = 3# ; //(small to facilitate visual functional test). eventually could be 100 1000, but not more than 5000.
FullDataSize = 50
InputArr = (np.random.rand(FullDataSize)-0.48)/100
InputArr[0] = 100;
for i in range(1,FullDataSize):# //fill the Input array with random data.
    InputArr[i] = InputArr[i - 1] * (1+InputArr[i])#; //brownian motion data.
RollWinArray = np.empty(Window)
Low = 100
for i in range(0, Window):
    RollWinArray[i] = 10000000;

Low = 100 # 0?
LowLocation = 0
CurrentLocation = 0
Result1 = np.empty(FullDataSize)# ; //contains the caching mimimum result
i1 = 0# //incrementor, just to store the result back to the array. In real life, the result is not even stored back to array.


# //====================================== my initialy proposed caching algo
def CalcCachingMin(currentNum):
    global CurrentLocation, Low, i1, LowLocation, Low
    RollWinArray[CurrentLocation] = currentNum
    if (currentNum <= Low):
        LowLocation = CurrentLocation
        Low = currentNum
    else:
        if (CurrentLocation == LowLocation):
            ReFindHighest()

    CurrentLocation = CurrentLocation + 1
    if (CurrentLocation == Window):
        CurrentLocation = 0# //this is faster
    # //CurrentLocation = CurrentLocation % Window; //this is slower, still over 10 fold faster than ascending minima
    Result1[i1] = Low
    i1 = i1 + 1

# //full iteration run each time lowest is overwritten.
def ReFindHighest():
    Low = RollWinArray[0]
    LowLocation = 0# //bug fix. missing from initial version.
    for i in range (1, Window):
        if (RollWinArray[i] < Low):
            Low = RollWinArray[i]
            LowLocation = i


for i in range(0, FullDataSize):# //run the Caching algo.
    CalcCachingMin(InputArr[i])

