import cmath as cm
import math
import wave as wv
import numpy as np
from itertools import chain
from datetime import date
import matplotlib.pyplot as plt

source_file_path =  "./youth.txt"
bpsk_file = "./bpsk.wav"
qpsk_I_file = "./qpsk_i.wav"
qpsk_Q_file = "./qpsk_q.wav"
qpsk_file = "./qpsk.wav"
Channels = 1  #通道数，单声道
Sampwidth = 2  #采样位宽，16位
WAV_VAL = []

SampleRate = 48000#采样率,可取48000，96000，192000
# BaudRate = 31.25#波特率，可取31.25,62.5,125,250,500
BaudRate = 125#波特率，可取31.25,62.5,125,250,500
Freq_Carrier = 1000#频率为整数，大于0.5*波特率

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


M = int(SampleRate/BaudRate)#符号样本点数，SampleRate=48000,BaudRate=0,SampleRate/BaudRate=48000/31.25=1536;cf 对于不同的采样率与波特率组合，取值见下表：
#             波特率31.25     62.5     125     250     500
#采样率48000       [1536      768      384     192     96 ]
#采样率96000       [3072      1536     768     384     192]
#采样率192000      [6144      3072     1536    768     384]
half_sample = 0.5*M
tri_M = 3*M
CD_M = 400*M
all_circle = 144000*M#360*400=144000
half_circle = 72000*M#180*400=72000
quarter_circle = 36000*M#90*400=36000

Pha_c = 0
Pha_s = 0
Pha_sum = Pha_s + Pha_c
Pha_diff = Pha_s - Pha_c

class CORDIC_FIXED:
    def __init__(self, iterations=16):
        self.iterations = iterations
        self.K_fixed = 7680  # 1111000000000，约等于增益因子0.607252935*12674，12674*2=25294，此数25294可变，小于32768即可，相当于16位位深音量调节，此处因积化和差有1/2系数，故取12674的一半
        self.angles_fixed = [27648000,16321597,8623841,4377600,2197279,1099715,550011,275005,137503,68751,34406,17203,8602,4301,2150,1044,553,246,123,61]  # 45*400*1536……
    def cos_sin_fixed(self, phase):
        """定点CORDIC计算sin和cos"""
        # 初始化：x = K, y = 0
        x = self.K_fixed
        y = 0

        # 角度预处理（象限转换）
        if phase >= half_circle:
            phase = phase - all_circle
        if phase < -half_circle:
            phase = phase + all_circle
        if phase >= half_circle:
            print("phase error:phase > half_circle")
        if phase < -half_circle:
            print("phase error:phase <= -half_circle")

        if (phase > quarter_circle) and (phase <= half_circle):
            phase = phase - half_circle
            sin_sign = -1
            cos_sign = -1
        elif (phase >= -half_circle) and (phase < -quarter_circle):
            phase = half_circle + phase
            sin_sign = -1
            cos_sign = -1
        else:
            sin_sign = 1
            cos_sign = 1

        z = phase

        for i in range(self.iterations):
            if z >= 0:
                x_new = x - (y >> i)
                y_new = y + (x >> i)
                z -= self.angles_fixed[i]
            else:
                x_new = x + (y >> i)
                y_new = y - (x >> i)
                z += self.angles_fixed[i]
            x = x_new
            y = y_new

        x, y = cos_sign * x, sin_sign * y
        return x, y

def varicode(stri):
    Varicode = "00000000"
    for c in stri:
        cord = varicodetab[c] + delim;
        Varicode = Varicode + cord;

    Varicode = Varicode + '11111111'

    CordLen = len(Varicode)

    if CordLen & 1 == 1:
        Varicode = Varicode + '1'
    return Varicode

def sym_change(list):
    symbol_G = ""
    tsym = ''
    list_Len = len(list)
    i = 0
    while (i < list_Len):
        if list[i:i + 2] == '00':
            if list[i + 2:i + 5] == '000':
                tsym = '2'
            elif list[i + 2:i + 5] == '001':
                tsym = '1'
            elif list[i + 2:i + 5] == '010':
                tsym = '3'
            elif list[i + 2:i + 5] == '011':
                tsym = '0'
            elif list[i + 2:i + 5] == '100':
                tsym = '3'
            elif list[i + 2:i + 5] == '101':
                tsym = '0'
            elif list[i + 2:i + 5] == '110':
                tsym = '2'
            elif list[i + 2:i + 5] == '111':
                tsym = '1'

        elif list[i:i + 2] == '01':
            if list[i + 2:i + 5] == '000':
                tsym = '0'
            elif list[i + 2:i + 5] == '001':
                tsym = '3'
            elif list[i + 2:i + 5] == '010':
                tsym = '1'
            elif list[i + 2:i + 5] == '011':
                tsym = '2'
            elif list[i + 2:i + 5] == '100':
                tsym = '1'
            elif list[i + 2:i + 5] == '101':
                tsym = '2'
            elif list[i + 2:i + 5] == '110':
                tsym = '0'
            elif list[i + 2:i + 5] == '111':
                tsym = '3'

        elif list[i:i + 2] == '10':
            if list[i + 2:i + 5] == '000':
                tsym = '1'
            elif list[i + 2:i + 5] == '001':
                tsym = '2'
            elif list[i + 2:i + 5] == '010':
                tsym = '0'
            elif list[i + 2:i + 5] == '011':
                tsym = '3'
            elif list[i + 2:i + 5] == '100':
                tsym = '0'
            elif list[i + 2:i + 5] == '101':
                tsym = '3'
            elif list[i + 2:i + 5] == '110':
                tsym = '1'
            elif list[i + 2:i + 5] == '111':
                tsym = '2'

        elif list[i:i + 2] == '11':
            if list[i + 2:i + 5] == '000':
                tsym = '3'
            elif list[i + 2:i + 5] == '001':
                tsym = '0'
            elif list[i + 2:i + 5] == '010':
                tsym = '2'
            elif list[i + 2:i + 5] == '011':
                tsym = '1'
            elif list[i + 2:i + 5] == '100':
                tsym = '2'
            elif list[i + 2:i + 5] == '101':
                tsym = '1'
            elif list[i + 2:i + 5] == '110':
                tsym = '3'
            elif list[i + 2:i + 5] == '111':
                tsym = '0'

        else:
            tsym = '0'
        symbol_G = symbol_G + tsym
        i = i + 1
    # print(symbol_G)

    symbol_I = ""
    symbol_Q = ""
    symbol_Len = len(symbol_G)
    i = 0
    curphase = 0
    while (i < symbol_Len):
        prephase = curphase
        curphase = curphase + int(symbol_G[i])
        if curphase >= 4:
            curphase -= 4
        if prephase == 0:
            if curphase == 0:
                I_sym = '1'
                Q_sym = '1'
            elif curphase == 1:
                I_sym = '0'
                Q_sym = '1'
            elif curphase == 2:
                I_sym = '0'
                Q_sym = '0'
            else:
                I_sym = '1'
                Q_sym = '0'
        if prephase == 1:
            if curphase == 0:
                I_sym = '0'
                Q_sym = '1'
            elif curphase == 1:
                I_sym = '1'
                Q_sym = '1'
            elif curphase == 2:
                I_sym = '1'
                Q_sym = '0'
            else:
                I_sym = '0'
                Q_sym = '0'
        if prephase == 2:
            if curphase == 0:
                I_sym = '0'
                Q_sym = '0'
            elif curphase == 1:
                I_sym = '1'
                Q_sym = '0'
            elif curphase == 2:
                I_sym = '1'
                Q_sym = '1'
            else:
                I_sym = '0'
                Q_sym = '1'
        if prephase == 3:
            if curphase == 0:
                I_sym = '1'
                Q_sym = '0'
            elif curphase == 1:
                I_sym = '0'
                Q_sym = '0'
            elif curphase == 2:
                I_sym = '0'
                Q_sym = '1'
            else:
                I_sym = '1'
                Q_sym = '1'
        symbol_I = symbol_I + I_sym
        symbol_Q = symbol_Q + Q_sym

        i = i + 1

    return symbol_I,symbol_Q

def bpsk(str_list):
    global Pha_s,Pha_c,Delta_Pha_s,Delta_Pha_c
    cordic_fix = CORDIC_FIXED(iterations=16)

    list_Len = len(str_list)

    level = []
    i = 0
    while (i < list_Len):
        if str_list[i] == '1':
            Delta_Pha_s = 0
        else:
            Delta_Pha_s = 180 * 400

        m = 0
        WAV_VAL = []
        while m < M:
            Pha_s += Delta_Pha_s
            Pha_c += Delta_Pha_c
            if Pha_s >= half_circle :  # 当相位值大于Pi时，减2Pi
                Pha_s -= all_circle
            if Pha_s >= half_circle :  # 当相位值仍大于Pi时，报错
                print("symbol phase error:Pha_s >= half_circle")
            if Pha_c >= half_circle :  # 当相位值大于Pi时，减2Pi
                Pha_c -= all_circle
            if Pha_c >= half_circle :  # 当相位值仍大于Pi时，报错
                print("carrier phase error:Pha_c >= half_circle")
            Pha_sum = Pha_s + Pha_c
            Pha_diff = Pha_s - Pha_c
            if Pha_sum >= half_circle:  # 当相位值大于Pi时，减2Pi
                Pha_sum -= all_circle
            if Pha_diff >= half_circle:  # 当相位值大于Pi时，减2Pi
                Pha_diff -= all_circle
            cos_val_sum, sin_val_sum = cordic_fix.cos_sin_fixed(Pha_sum)
            cos_val_diff, sin_val_diff = cordic_fix.cos_sin_fixed(Pha_diff)
            WAV_VAL.append(sin_val_sum - sin_val_diff)
            # WAV_VAL.append(cos_val_sum + cos_val_diff)
            m += 1

        level = level + WAV_VAL
        Pha_s = 0
        if str_list[i] == '0':
            Pha_c += half_circle
        i = i + 1

    return level

def qpsk(str_list):
    global Pha_c
    qpsk_I_sym_str,qpsk_Q_sym_str = sym_change(str_list)
    # print(len(qpsk_I_sym_str))
    # print(qpsk_I_sym_str)
    # print(len(qpsk_Q_sym_str))
    # print(qpsk_Q_sym_str)
    Pha_c = 0
    level_I = bpsk(qpsk_I_sym_str)
    Pha_c = -quarter_circle

    level_Q = bpsk(qpsk_Q_sym_str)
    return level_I,level_Q

def save_to_wav_file(l, filename):
#将列表中的数据转存到wav文件
    dist_file =  filename    #数据wav文件路径
    data = wv.open(dist_file, "wb") #输出I数据到WAV文件
    data.setnchannels(Channels)   #单通道
    data.setsampwidth(Sampwidth)   #采样位宽16位（2字节）
    data.setframerate(SampleRate)   #采样率
    data.writeframesraw(l) #数据写入音频帧
    data.close()   #关闭文件

if __name__ == "__main__":

    with open(source_file_path, "r") as f:
        stri = f.read();

    Pha_c = 0
    Delta_Pha_c = tri_M * Freq_Carrier
    string_list = varicode(stri)
    print(len(string_list))
    print(string_list)

    level_bpsk = []
    level_bpsk = bpsk(string_list)
    DATA_bpsk = np.array(level_bpsk, dtype=np.int16)
    save_to_wav_file(DATA_bpsk, bpsk_file)

    level_qpsk_I =[]
    level_qpsk_Q =[]
    level_qpsk = []
    level_qpsk_I,level_qpsk_Q = qpsk(string_list)
    # level_qpsk = level_qpsk_I + level_qpsk_Q
    level_qpsk = [level_qpsk_I[i] + level_qpsk_Q[i]>>1 for i in range(min(len(level_qpsk_I), len(level_qpsk_Q)))]
    DATA_qpsk_I = np.array(level_qpsk_I, dtype=np.int16)
    DATA_qpsk_Q = np.array(level_qpsk_Q, dtype=np.int16)
    DATA_qpsk = np.array(level_qpsk, dtype=np.int16)
    save_to_wav_file(DATA_qpsk_I, qpsk_I_file)
    save_to_wav_file(DATA_qpsk_Q, qpsk_Q_file)
    save_to_wav_file(DATA_qpsk, qpsk_file)










