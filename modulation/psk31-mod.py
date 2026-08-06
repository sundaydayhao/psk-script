import wave as wv
import numpy as np
from datetime import date
import matplotlib.pyplot as plt

SampleRate = 48000
Frequency = 3000
BaudRate = 250
txtsourcepath = "C:/PSK31source/sometimes.txt"
wavdestinationpath = "C:/PSK31source/"

delim = "00"
varicodetab = {
    "\n": "11101",
    " ": "1",

    # Numbers
    "0": "10110111",
    "1": "10111101",
    "2": "11101101",
    "3": "11111111",
    "4": "101110111",
    "5": "101011011",
    "6": "101101011",
    "7": "110101101",
    "8": "110101011",
    "9": "110110111",

    # Symbols,
    "'": "101111111",
    "?": "1010101111",
    "!": "111111111",
    ";": "110111101",
    ":": "11110101",
    "\"": "101011111",
    "#": "111110101",
    "$": "111011011",
    "%": "1011010101",
    "&": "1010111011",
    "(": "11111011",
    ")": "11110111",
    "*": "101101111",
    "+": "111011111",
    ".": "1010111",
    ",": "1110101",
    "-": "110101",
    "|": "110111011",
    "_": "1010111111",
    "\\": "111110111",
    "/": "110101111",
    "=": "1010101",
    "<": "111101101",
    ">": "111010111",
    "[": "1010101101",
    "]": "111101111",

    # Lowercase
    "a": "1011",
    "b": "1011111",
    "c": "101111",
    "d": "101101",
    "e": "11",
    "f": "111101",
    "g": "1011011",
    "h": "101011",
    "i": "1101",
    "j": "111101011",
    "k": "10111111",
    "l": "11011",
    "m": "111011",
    "n": "1111",
    "o": "111",
    "p": "111111",
    "q": "110111111",
    "r": "10101",
    "s": "10111",
    "t": "101",
    "u": "110111",
    "v": "1111011",
    "w": "1101011",
    "x": "11011111",
    "y": "1011101",
    "z": "111010101",

    # Uppercase
    "A": "1111101",
    "B": "11101011",
    "C": "10101101",
    "D": "10110101",
    "E": "1110111",
    "F": "11011011",
    "G": "11111101",
    "H": "101010101",
    "I": "1111111",
    "J": "111111101",
    "K": "101111101",
    "L": "11010111",
    "M": "10111011",
    "N": "11011101",
    "O": "10101011",
    "P": "11010101",
    "Q": "111011101",
    "R": "10101111",
    "S": "1101111",
    "T": "1101101",
    "U": "101010111",
    "V": "110110101",
    "W": "101011101",
    "X": "101110101",
    "Y": "101111011",
    "Z": "1010101101",
};

Varicode = "00000000"

with open(txtsourcepath ,"r") as f:
    cstr = f.read();

for c in cstr:
    cord =  varicodetab[c] + delim ;
    Varicode =  Varicode + cord ;

Varicode =  Varicode + '11111111'

phase = 0
FrameLen = int(SampleRate / BaudRate)
deltaT = 1 / SampleRate
thetaB = np.pi * BaudRate * deltaT
thetaC = np.pi * Frequency * deltaT

level = []
CordLen = len(Varicode)

print(CordLen)
print(Varicode)

i = 0
while(i<CordLen):
    if Varicode[i] == '0':
        level0 = []
        for t in range(1, FrameLen):
            phase0 = phase + thetaC * t
            level0.append(np.round(32767 * np.cos(thetaB * t) * np.sin(phase0)))

        level.extend(level0)
        phase = phase0 + np.pi

    else:
        level1 = []
        for t in range(1, FrameLen):
            phase1 = phase + thetaC * t
            level1.append(np.round(32767 * np.sin(phase1)))

        level.extend(level1)
        phase = phase1

    i = i + 1

data = np.array(level , dtype='object')
z = data.astype('int16')
today = date.today()
pskfile = wv.open(wavdestinationpath + "sometimes" + "Psk" + str(BaudRate)  +str (today) + ".wav", "wb")
pskfile.setnchannels(1)
pskfile.setsampwidth(2)
pskfile.setframerate(SampleRate)
pskfile.writeframesraw(z)

pskfile.close()

wavfile = wv.open(wavdestinationpath +"sometimes"  "Psk" + str(BaudRate) + ".wav", "rb")
params = wavfile.getparams()
nchannels, sampwidth, framerate, nframes = params[:4]
nf = wavfile.getnframes()
data = wavfile.readframes(nf)
wavfile.close()
        # 需要根据声道数和量化单位，将读取的二进制数据转换为一个可以计算的数组
wave_data = np.frombuffer(data, dtype = np.short)
        # 转置数据
wave_data = wave_data.T
        # 通过取样点数和取样频率计算出每个取样的时间。time 也是一个数组，与wave_data配对形成系列点坐标
time = np.arange(0, nframes) / framerate

plt.plot(time, wave_data)

plt.xlabel("time")
plt.ylabel("data")
plt.show()