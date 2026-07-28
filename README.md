# psk-python

这个仓库整理了 PSK31 / QPSK31 调制相关的 Python 实验脚本。

## 目录结构

- `20251127-psk31/`
  - `psk31-mod.py`：PSK31 调制脚本
  - `qpsk31-mod.py`：QPSK31 调制脚本
- `Youth-qpsk31/`
  - `qpsk31-mod(20240222).py`：QPSK31 调制脚本
  - `Youth.txt`：示例文本源

## 环境依赖

脚本使用 Python 3，并依赖：

- `numpy`
- `matplotlib`

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

## 说明

当前代码更偏向算法验证和波形生成实验，不是已经封装好的 Python 包。
