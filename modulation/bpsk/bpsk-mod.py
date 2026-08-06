import wave as wv
import numpy as np
from pathlib import Path

SampleRate = 48000
CarrierFrequency = 1500
OutputAmplitude = 1000
LeadingSilenceSeconds = 2
TrailingSilenceSeconds = 1
ShowPlot = False
txtsourcepath = "C:\\projects\\psk-script\\input.txt"
wavdestinationpath = "C:\\projects\\psk-script\\modulation\\bpsk"

BaudRates = (31, 63, "63F", 125, 250, 500, 1000)
PreambleSymbols = {
    "31": 32,
    "63": 64,
    "63F": 64,
    "125": 128,
    "250": 512,
    "500": 1024,
    "1000": 128,
}

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

CordLen = len(Varicode)

print(CordLen)
print(Varicode)

deltaT = 1 / SampleRate
thetaC = 2 * np.pi * CarrierFrequency * deltaT
leading_silence = [0] * int(SampleRate * LeadingSilenceSeconds)
trailing_silence = [0] * int(SampleRate * TrailingSilenceSeconds)

for BaudRate in BaudRates:
    baud_rate_label = str(BaudRate)
    baud_rate_value = 63 if baud_rate_label.upper() == "63F" else int(BaudRate)

    phase = 0
    symbol = 1.0
    FrameLen = int(SampleRate / baud_rate_value)
    tx_bits = ("0" * PreambleSymbols[baud_rate_label]) + Varicode

    level = leading_silence.copy()
    for bit in tx_bits:
        prev_symbol = symbol
        if bit == '0':
            symbol = -symbol

        for t in range(FrameLen):
            shapeA = 0.5 * np.cos(np.pi * t / FrameLen) + 0.5
            shapeB = 1.0 - shapeA
            shaped_symbol = shapeA * prev_symbol + shapeB * symbol
            level.append(np.round(OutputAmplitude * shaped_symbol * np.sin(phase)))
            phase = phase + thetaC

    level.extend(trailing_silence)

    data = np.array(level , dtype='object')
    z = data.astype('int16')
    wavpath = Path(wavdestinationpath) / ("bpsk-" + baud_rate_label + ".wav")
    pskfile = wv.open(str(wavpath), "wb")
    pskfile.setnchannels(1)
    pskfile.setsampwidth(2)
    pskfile.setframerate(SampleRate)
    pskfile.writeframesraw(z)

    pskfile.close()
    print("Wrote " + str(wavpath))

    if ShowPlot:
        import matplotlib.pyplot as plt

        wavfile = wv.open(str(wavpath), "rb")
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

        plt.figure()
        plt.plot(time, wave_data)

        plt.title("BPSK " + baud_rate_label)
        plt.xlabel("time")
        plt.ylabel("data")
        plt.show()
