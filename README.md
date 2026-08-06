# psk-python

这个仓库整理了 PSK31 / QPSK31 调制相关的 Python 实验脚本。

## 目录结构

- `20251127-psk31/`
  - `psk31-mod.py`：PSK31 调制脚本
  - `qpsk31-mod.py`：QPSK31 调制脚本
- `Youth-qpsk31/`
  - `qpsk31-mod(20240222).py`：QPSK31 调制脚本
  - `Youth.txt`：示例文本源
- `generate_psk_wavs.py`：结合本机 `C:\projects\fldigi` 的 varicode 表和调制参数，批量生成 BPSK / 多载波 BPSK / QPSK / 8PSK WAV 测试音频。

## 环境依赖

脚本使用 Python 3，并依赖：

- `numpy`
`generate_psk_wavs.py` 使用 Python 3 和 `numpy`。

可使用下面的命令安装依赖：

```bash
pip install numpy
```

## 使用说明

脚本中包含输入文本路径、输出目录、采样率、载波频率和符号率等参数，例如：

- `SampleRate`
- `Frequency`
- `BaudRate`
- `txtsourcepath`
- `wavdestinationpath`

运行前请根据本机目录调整脚本中的输入和输出路径。

```bash
python 20251127-psk31/psk31-mod.py
python 20251127-psk31/qpsk31-mod.py
```

批量生成 fldigi 风格 PSK WAV：

```bash
python generate_psk_wavs.py --all --out-dir C:\projects\psk-script\generated-wav
```

默认输出为 48 kHz / 16-bit / 单声道，中心频率 1500 Hz，峰值幅度 0.6，最小时长 60 秒。默认生成路径按 `C:\projects\fldigi\src\psk\psk.cxx` 的前导、尾部、相位映射和标准符号率实现，便于 fldigi 直接解码。若需要旧实验脚本波形，可加 `--legacy-single-carrier`。

为提高 fldigi 解码稳定性，脚本默认生成一段连续发射：重复正文文本，但只保留一次前导和一次尾部，并在 WAV 开头和结尾各加 1 秒静音。`8PSK*F` 这类 FEC 模式编码成本较高，使用完整 fldigi 报文包重复。

`BPSK63F`、`BPSK250`、`BPSK500`、`BPSK1000` 使用更长前导，以便 fldigi 在高符号率或 FEC 模式下更稳定锁定。

生成单个或多个模式：

```bash
python generate_psk_wavs.py --mode BPSK31 --mode 8PSK500F --text "CQ CQ CQ DE TEST"
```

指定更长时长：

```bash
python generate_psk_wavs.py --mode BPSK63 --duration 260
```

默认生成下面 27 个模式：

- BPSK31, BPSK63, BPSK63F, BPSK125, BPSK250, BPSK500, BPSK1000
- 12xPSK125, 6xPSK250, 2xPSK500, 4xPSK500, 2xPSK800, 2xPSK1000
- QPSK31, QPSK63, QPSK125, QPSK250, QPSK500
- 8PSK125, 8PSK250, 8PSK500, 8PSK1000, 8PSK125F, 8PSK250F, 8PSK500F, 8PSK1000F, 8PSK1200F

## 说明

当前代码更偏向算法验证和波形生成实验，不是已经封装好的 Python 包。
