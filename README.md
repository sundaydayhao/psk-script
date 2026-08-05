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
- `matplotlib`

`generate_psk_wavs.py` 只使用 Python 标准库，不需要安装额外依赖。

可使用下面的命令安装依赖：

```bash
pip install numpy matplotlib
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

生成单个或多个模式：

```bash
python generate_psk_wavs.py --mode BPSK31 --mode 8PSK500F --text "CQ CQ CQ DE TEST"
```

默认生成下面 27 个模式：

- BPSK31, BPSK63, BPSK63F, BPSK125, BPSK250, BPSK500, BPSK1000
- 12xPSK125, 6xPSK250, 2xPSK500, 4xPSK500, 2xPSK800, 2xPSK1000
- QPSK31, QPSK63, QPSK125, QPSK250, QPSK500
- 8PSK125, 8PSK250, 8PSK500, 8PSK1000, 8PSK125F, 8PSK250F, 8PSK500F, 8PSK1000F, 8PSK1200F

## 说明

当前代码更偏向算法验证和波形生成实验，不是已经封装好的 Python 包。
