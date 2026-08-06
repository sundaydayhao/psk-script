#!/usr/bin/env python3
"""Generate fldigi-style PSK WAV test signals.

The script reads PSK and MFSK varicode tables from a local fldigi checkout and
generates 16-bit mono WAV files for the BPSK, multi-carrier BPSK, QPSK, and
8PSK modes listed in MODE_ORDER.
"""

from __future__ import annotations

import argparse
import array
import math
import re
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


TWOPI = 2.0 * math.pi

K = 5
POLY1 = 0x17
POLY2 = 0x19

PSKR_K = 7
PSKR_POLY1 = 0x6D
PSKR_POLY2 = 0x4F

K13 = 13
K13_POLY1 = 0o16461
K13_POLY2 = 0o12767

K16 = 16
K16_POLY1 = 0o152711
K16_POLY2 = 0o126723


SYM_VEC_POS = (
    complex(-1.0, 0.0),
    complex(-0.9238, -0.3826),
    complex(-0.7071, -0.7071),
    complex(-0.3826, -0.9238),
    complex(0.0, -1.0),
    complex(0.3826, -0.9238),
    complex(0.7071, -0.7071),
    complex(0.9238, -0.3826),
    complex(1.0, 0.0),
    complex(0.9238, 0.3826),
    complex(0.7071, 0.7071),
    complex(0.3826, 0.9238),
    complex(0.0, 1.0),
    complex(-0.3826, 0.9238),
    complex(-0.7071, 0.7071),
    complex(-0.9238, 0.3826),
)

GRAY_8PSK_POS = (
    complex(1.0, 0.0),
    complex(0.7071, 0.7071),
    complex(-0.7071, 0.7071),
    complex(0.0, 1.0),
    complex(0.7071, -0.7071),
    complex(0.0, -1.0),
    complex(-1.0, 0.0),
    complex(-0.7071, -0.7071),
)


@dataclass(frozen=True)
class ModeSpec:
    name: str
    family: str
    baud: float
    carriers: int = 1
    dcdbits: int = 32
    fec_disabled: bool = False
    puncturing: bool = False
    flushlength: int = 0
    fec_k: int | None = None
    fec_poly1: int | None = None
    fec_poly2: int | None = None

    @property
    def symbits(self) -> int:
        if self.family == "qpsk":
            return 2
        if self.family == "8psk":
            return 3
        return 1

    @property
    def uses_mfsk_varicode(self) -> bool:
        return self.family in ("8psk", "bpsk_fec")

    @property
    def uses_fec(self) -> bool:
        return self.family in ("qpsk", "bpsk_fec") or (
            self.family == "8psk" and not self.fec_disabled
        )


MODES: dict[str, ModeSpec] = {
    "BPSK31": ModeSpec("BPSK31", "bpsk", 31.25, dcdbits=32),
    "BPSK63": ModeSpec("BPSK63", "bpsk", 62.5, dcdbits=64),
    "BPSK63F": ModeSpec("BPSK63F", "bpsk_fec", 62.5, dcdbits=64, fec_k=PSKR_K, fec_poly1=PSKR_POLY1, fec_poly2=PSKR_POLY2),
    "BPSK125": ModeSpec("BPSK125", "bpsk", 125.0, dcdbits=128),
    "BPSK250": ModeSpec("BPSK250", "bpsk", 250.0, dcdbits=256),
    "BPSK500": ModeSpec("BPSK500", "bpsk", 500.0, dcdbits=512),
    "BPSK1000": ModeSpec("BPSK1000", "bpsk", 1000.0, dcdbits=128),
    "12xPSK125": ModeSpec("12xPSK125", "bpsk", 125.0, carriers=12, dcdbits=128),
    "6xPSK250": ModeSpec("6xPSK250", "bpsk", 250.0, carriers=6, dcdbits=512),
    "2xPSK500": ModeSpec("2xPSK500", "bpsk", 500.0, carriers=2, dcdbits=512),
    "4xPSK500": ModeSpec("4xPSK500", "bpsk", 500.0, carriers=4, dcdbits=512),
    "2xPSK800": ModeSpec("2xPSK800", "bpsk", 800.0, carriers=2, dcdbits=512),
    "2xPSK1000": ModeSpec("2xPSK1000", "bpsk", 1000.0, carriers=2, dcdbits=1024),
    "QPSK31": ModeSpec("QPSK31", "qpsk", 31.25, dcdbits=32, fec_k=K, fec_poly1=POLY1, fec_poly2=POLY2),
    "QPSK63": ModeSpec("QPSK63", "qpsk", 62.5, dcdbits=64, fec_k=K, fec_poly1=POLY1, fec_poly2=POLY2),
    "QPSK125": ModeSpec("QPSK125", "qpsk", 125.0, dcdbits=128, fec_k=K, fec_poly1=POLY1, fec_poly2=POLY2),
    "QPSK250": ModeSpec("QPSK250", "qpsk", 250.0, dcdbits=256, fec_k=K, fec_poly1=POLY1, fec_poly2=POLY2),
    "QPSK500": ModeSpec("QPSK500", "qpsk", 500.0, dcdbits=512, fec_k=K, fec_poly1=POLY1, fec_poly2=POLY2),
    "8PSK125": ModeSpec("8PSK125", "8psk", 125.0, dcdbits=128, fec_disabled=True),
    "8PSK250": ModeSpec("8PSK250", "8psk", 250.0, dcdbits=256, fec_disabled=True),
    "8PSK500": ModeSpec("8PSK500", "8psk", 500.0, dcdbits=512, fec_disabled=True),
    "8PSK1000": ModeSpec("8PSK1000", "8psk", 1000.0, dcdbits=1024, fec_disabled=True),
    "8PSK125F": ModeSpec("8PSK125F", "8psk", 125.0, dcdbits=128, flushlength=55, fec_k=K16, fec_poly1=K16_POLY1, fec_poly2=K16_POLY2),
    "8PSK250F": ModeSpec("8PSK250F", "8psk", 250.0, dcdbits=256, flushlength=65, fec_k=K16, fec_poly1=K16_POLY1, fec_poly2=K16_POLY2),
    "8PSK500F": ModeSpec("8PSK500F", "8psk", 500.0, dcdbits=512, puncturing=True, flushlength=80, fec_k=K13, fec_poly1=K13_POLY1, fec_poly2=K13_POLY2),
    "8PSK1000F": ModeSpec("8PSK1000F", "8psk", 1000.0, dcdbits=1024, puncturing=True, flushlength=120, fec_k=PSKR_K, fec_poly1=PSKR_POLY1, fec_poly2=PSKR_POLY2),
    "8PSK1200F": ModeSpec("8PSK1200F", "8psk", 16000.0 / 13.0, dcdbits=2048, puncturing=True, flushlength=175, fec_k=PSKR_K, fec_poly1=PSKR_POLY1, fec_poly2=PSKR_POLY2),
}

MODE_ORDER = (
    "BPSK31",
    "BPSK63",
    "BPSK63F",
    "BPSK125",
    "BPSK250",
    "BPSK500",
    "BPSK1000",
    "12xPSK125",
    "6xPSK250",
    "2xPSK500",
    "4xPSK500",
    "2xPSK800",
    "2xPSK1000",
    "QPSK31",
    "QPSK63",
    "QPSK125",
    "QPSK250",
    "QPSK500",
    "8PSK125",
    "8PSK250",
    "8PSK500",
    "8PSK1000",
    "8PSK125F",
    "8PSK250F",
    "8PSK500F",
    "8PSK1000F",
    "8PSK1200F",
)


def parity(value: int) -> int:
    return value.bit_count() & 1


class Encoder:
    def __init__(self, k: int, poly1: int, poly2: int) -> None:
        self.k = k
        self.poly1 = poly1
        self.poly2 = poly2
        self.mask = (1 << k) - 1
        self.shreg = 0
        self.output = [
            parity(poly1 & state) | (parity(poly2 & state) << 1)
            for state in range(1 << k)
        ]

    def init(self) -> None:
        self.shreg = 0

    def encode(self, bit: int) -> int:
        self.shreg = ((self.shreg << 1) | (1 if bit else 0)) & self.mask
        return self.output[self.shreg]


class Interleave:
    def __init__(self, size: int, depth: int) -> None:
        self.size = size
        self.depth = depth
        self.table = [
            [[0 for _ in range(size)] for _ in range(size)]
            for _ in range(depth)
        ]

    def flush(self) -> None:
        for k in range(self.depth):
            for i in range(self.size):
                for j in range(self.size):
                    self.table[k][i][j] = 0

    def bits(self, value: int) -> int:
        syms = [(value >> (self.size - i - 1)) & 1 for i in range(self.size)]
        for k in range(self.depth):
            for i in range(self.size):
                row = self.table[k][i]
                for j in range(self.size - 1):
                    row[j] = row[j + 1]
                row[self.size - 1] = syms[i]
            syms = [self.table[k][i][self.size - i - 1] for i in range(self.size)]
        out = 0
        for bit in syms:
            out = (out << 1) | bit
        return out


class PskGenerator:
    def __init__(
        self,
        mode: ModeSpec,
        sample_rate: int,
        center_frequency: float,
        amplitude: float,
        psk_varicode: list[str],
        mfsk_varicode: list[str],
    ) -> None:
        self.mode = mode
        self.sample_rate = sample_rate
        self.center_frequency = center_frequency
        self.amplitude = amplitude
        self.psk_varicode = psk_varicode
        self.mfsk_varicode = mfsk_varicode
        self.samples_per_symbol = int(sample_rate / mode.baud)

        self.separation = 1.4
        self.sc_bw = mode.baud
        self.inter_carrier = self.separation * self.sc_bw
        self.prev_symbols = [complex(1.0, 0.0) for _ in range(mode.carriers)]
        self.phase_acc = [0.0 for _ in range(mode.carriers)]
        self.pending_symbols: list[int] = []
        self.blocks: list[np.ndarray] = []
        self.sample_index = np.arange(self.samples_per_symbol, dtype=np.float64)
        self.shape = 0.5 * np.cos(self.sample_index * math.pi / self.samples_per_symbol) + 0.5
        self.disable_fec_now = mode.fec_disabled

        self.encoder = None
        self.interleaver = None
        if mode.uses_fec:
            if mode.fec_k is None or mode.fec_poly1 is None or mode.fec_poly2 is None:
                raise ValueError(f"{mode.name}: FEC parameters are missing")
            self.encoder = Encoder(mode.fec_k, mode.fec_poly1, mode.fec_poly2)
            if mode.family == "8psk":
                self.interleaver = Interleave(2, self._interleave_depth())

        self._bitcount = 0
        self._xpsk_sym = 0

    def _interleave_depth(self) -> int:
        if self.mode.name == "8PSK125F":
            return 384
        if self.mode.name == "8PSK250F":
            return 512
        if self.mode.name == "8PSK500F":
            return 640
        if self.mode.name in ("8PSK1000F", "8PSK1200F"):
            return 512
        return 2

    def generate(self, text: str) -> array.array:
        self.tx_preamble()
        for byte in text.encode("latin-1", errors="replace"):
            self.tx_char(byte)
        self.tx_flush()
        if self.pending_symbols:
            pad = 4 if self.mode.family == "8psk" else 2
            while self.pending_symbols:
                self.tx_symbol(pad)
        self.blocks.append(np.zeros(int(0.25 * self.sample_rate), dtype=np.float64))
        wave_data = np.concatenate(self.blocks) if self.blocks else np.zeros(0, dtype=np.float64)
        peak = float(np.max(np.abs(wave_data))) if wave_data.size else 0.0
        scale = (32767.0 * self.amplitude / peak) if peak > 0 else 0.0
        wave_data = np.clip(np.round(wave_data * scale), -32767, 32767).astype(np.int16)
        pcm = array.array("h")
        pcm.frombytes(wave_data.tobytes())
        return pcm

    def tx_preamble(self) -> None:
        preamble_symbols = self.preamble_symbols()
        if self.mode.family == "bpsk_fec":
            if self.mode.name == "BPSK63F":
                for _ in range(self.mode.dcdbits):
                    self.tx_symbol(0)
            for _ in range(preamble_symbols // 2):
                self.tx_bit(1)
                self.tx_bit(0)
            while len(self.pending_symbols) % self.mode.carriers:
                self.tx_bit(0)
            for _ in range(6 if self.mode.name == "BPSK63F" else 1):
                self.tx_char(0)
            return

        if self.mode.family == "8psk":
            if not self.mode.fec_disabled:
                self.clear_fec()
                old_disable = self.disable_fec_now
                self.disable_fec_now = True
                for _ in range(preamble_symbols // 2):
                    self.tx_symbol(0)
                self.disable_fec_now = old_disable
                for _ in range(preamble_symbols // 2):
                    self.tx_bit(0)
                    self.tx_bit(0)
                self.tx_char(0)
            else:
                for _ in range(preamble_symbols):
                    self.tx_symbol(0)
                self.tx_char(0)
            return

        for _ in range(preamble_symbols):
            self.tx_symbol(0)

    def preamble_symbols(self) -> int:
        if self.mode.name == "BPSK63F":
            return max(self.mode.dcdbits, 256)
        if self.mode.name in ("BPSK250", "BPSK500", "BPSK1000"):
            return max(self.mode.dcdbits, int(3.0 * self.mode.baud))
        return self.mode.dcdbits

    def tx_flush(self) -> None:
        if self.mode.family == "bpsk_fec":
            while len(self.pending_symbols) % self.mode.carriers:
                self.tx_bit(0)
            for _ in range(self.mode.dcdbits // 2):
                self.tx_bit(1)
                self.tx_bit(1)
        elif self.mode.family == "qpsk":
            for _ in range(self.mode.dcdbits):
                self.tx_bit(0)
        elif self.mode.family == "8psk" and not self.mode.fec_disabled:
            for _ in range(self.mode.flushlength):
                self.tx_char(0)
        elif self.mode.family == "8psk":
            for _ in range(self.mode.symbits):
                self.tx_char(0)
            for _ in range(97):
                self.tx_symbol(4)
        else:
            for _ in range(self.mode.dcdbits):
                self.tx_symbol(2)

    def clear_fec(self) -> None:
        if self.encoder:
            self.encoder.init()
        if self.interleaver:
            self.interleaver.flush()
        self._bitcount = 0
        self._xpsk_sym = 0

    def tx_char(self, byte: int) -> None:
        table = self.mfsk_varicode if self.mode.uses_mfsk_varicode else self.psk_varicode
        for bit_char in table[byte]:
            self.tx_bit(1 if bit_char == "1" else 0)
        if not self.mode.uses_mfsk_varicode:
            self.tx_bit(0)
            self.tx_bit(0)

    def tx_bit(self, bit: int) -> None:
        if self.mode.family == "bpsk_fec":
            assert self.encoder is not None
            bits = self.encoder.encode(bit)
            self.tx_symbol((bits & 1) << 1)
            self.tx_symbol(bits & 2)
        elif self.mode.family == "qpsk":
            assert self.encoder is not None
            self.tx_symbol(self.encoder.encode(bit) & 3)
        elif self.mode.family == "8psk":
            if self.disable_fec_now:
                self._xpsk_sym |= (bit & 1) << self._bitcount
                self._bitcount += 1
                if self._bitcount == self.mode.symbits:
                    self.tx_symbol(self._xpsk_sym)
                    self._bitcount = 0
                    self._xpsk_sym = 0
            else:
                self.tx_8psk_fec_bit(bit)
        else:
            self.tx_symbol((bit & 1) << 1)

    def tx_8psk_fec_bit(self, bit: int) -> None:
        assert self.encoder is not None
        assert self.interleaver is not None
        if self.mode.puncturing and (self._bitcount & 1):
            self._bitcount = 0
        fecbits = self.interleaver.bits(self.encoder.encode(bit))
        if self.mode.puncturing:
            if self._bitcount == 0:
                self._xpsk_sym = fecbits
                self._bitcount = 2
            elif self._bitcount == 2:
                self._xpsk_sym |= (fecbits & 1) << 2
                self.tx_symbol(self._xpsk_sym & 7)
                self._xpsk_sym = 0
                self._bitcount = 0
            return

        if self._bitcount == 0:
            self._xpsk_sym = fecbits
            self._bitcount = 2
        elif self._bitcount == 1:
            self._xpsk_sym |= (fecbits & 1) << 1
            self._xpsk_sym |= (fecbits & 2) << 1
            self.tx_symbol(self._xpsk_sym)
            self._xpsk_sym = 0
            self._bitcount = 0
        elif self._bitcount == 2:
            self._xpsk_sym |= (fecbits & 1) << 2
            self.tx_symbol(self._xpsk_sym)
            self._xpsk_sym = (fecbits & 2) >> 1
            self._bitcount = 1

    def tx_symbol(self, symbol: int) -> None:
        self.pending_symbols.append(symbol)
        if len(self.pending_symbols) == self.mode.carriers:
            self.tx_carriers()
            self.pending_symbols.clear()

    def tx_carriers(self) -> None:
        n = self.samples_per_symbol
        block = np.zeros(n, dtype=np.float64)
        first = self.center_frequency + ((-1 * self.mode.carriers) + 1) * self.inter_carrier / 2.0
        for car, raw_symbol in enumerate(self.pending_symbols):
            symbol = self.map_symbol(raw_symbol, car)
            prev = self.prev_symbols[car]
            freq = first + car * self.inter_carrier
            delta = TWOPI * freq / self.sample_rate
            phases = self.phase_acc[car] + delta * self.sample_index
            i_val = self.shape * prev.real + (1.0 - self.shape) * symbol.real
            q_val = self.shape * prev.imag + (1.0 - self.shape) * symbol.imag
            block += (i_val * np.cos(phases) + q_val * np.sin(phases)) / self.mode.carriers
            self.phase_acc[car] = (self.phase_acc[car] + delta * n) % TWOPI
            self.prev_symbols[car] = symbol

        peak = float(np.max(np.abs(block))) if block.size else 0.0
        if peak > 0:
            block = block / peak
        self.blocks.append(block)

    def map_symbol(self, symbol: int, carrier: int) -> complex:
        if self.mode.family == "8psk" and not self.disable_fec_now:
            return self.prev_symbols[carrier] * GRAY_8PSK_POS[symbol & 7]

        mapped = symbol
        if self.mode.family == "qpsk":
            mapped = (4 - mapped) & 3
            mapped *= 4
        elif self.mode.family == "8psk":
            mapped *= 2
        else:
            mapped *= 4
        return self.prev_symbols[carrier] * SYM_VEC_POS[mapped & 0xF]


def generate_legacy_bpsk(
    mode: ModeSpec,
    text: str,
    sample_rate: int,
    frequency: float,
    amplitude: float,
    psk_varicode: list[str],
) -> array.array:
    """Generate the short-preamble BPSK waveform used by the legacy scripts."""
    bits = ["0"] * 8
    for byte in text.encode("latin-1", errors="replace"):
        bits.extend(psk_varicode[byte])
        bits.extend(("0", "0"))
    bits.extend(["1"] * 8)

    frame_len = int(sample_rate / mode.baud)
    t = np.arange(1, frame_len, dtype=np.float64)
    theta_b = np.pi * mode.baud / sample_rate
    theta_c = np.pi * frequency / sample_rate
    level_parts = []
    phase = 0.0
    for bit in bits:
        if bit == "0":
            phasev = phase + theta_c * t
            level_parts.append(np.round(32767.0 * np.cos(theta_b * t) * np.sin(phasev)))
            phase = float(phasev[-1] + np.pi)
        else:
            phasev = phase + theta_c * t
            level_parts.append(np.round(32767.0 * np.sin(phasev)))
            phase = float(phasev[-1])

    wave_data = np.concatenate(level_parts) if level_parts else np.zeros(0, dtype=np.float64)
    if amplitude != 1.0 and wave_data.size:
        wave_data *= amplitude
    wave_data = np.clip(np.round(wave_data), -32767, 32767).astype(np.int16)
    pcm = array.array("h")
    pcm.frombytes(wave_data.tobytes())
    return pcm


QPSK_MAP = {
    ("00", "000"): "2", ("00", "001"): "1", ("00", "010"): "3", ("00", "011"): "0",
    ("00", "100"): "3", ("00", "101"): "0", ("00", "110"): "2", ("00", "111"): "1",
    ("01", "000"): "0", ("01", "001"): "3", ("01", "010"): "1", ("01", "011"): "2",
    ("01", "100"): "1", ("01", "101"): "2", ("01", "110"): "0", ("01", "111"): "3",
    ("10", "000"): "1", ("10", "001"): "2", ("10", "010"): "0", ("10", "011"): "3",
    ("10", "100"): "0", ("10", "101"): "3", ("10", "110"): "1", ("10", "111"): "2",
    ("11", "000"): "3", ("11", "001"): "0", ("11", "010"): "2", ("11", "011"): "1",
    ("11", "100"): "2", ("11", "101"): "1", ("11", "110"): "3", ("11", "111"): "0",
}

QPSK_SIGNS = {
    0: (1.0, 1.0),
    1: (-1.0, 1.0),
    2: (-1.0, -1.0),
    3: (1.0, -1.0),
}


def qpsk_symbols_from_varicode(varicode: str) -> str:
    if len(varicode) % 2:
        varicode += "1"
    symbols = []
    tsym = "0"
    for i in range(len(varicode)):
        tsym = QPSK_MAP.get((varicode[i:i + 2], varicode[i + 2:i + 5]), tsym)
        symbols.append(tsym)
    return "".join(symbols)


def generate_legacy_qpsk(
    mode: ModeSpec,
    text: str,
    sample_rate: int,
    frequency: float,
    amplitude: float,
    psk_varicode: list[str],
) -> array.array:
    bits = ["0"] * 32
    for byte in text.encode("latin-1", errors="replace"):
        bits.extend(psk_varicode[byte])
        bits.extend(("0", "0"))
    bits.extend(["1"] * 30)
    symbols = qpsk_symbols_from_varicode("".join(bits))

    frame_len_half = int(0.5 * sample_rate / mode.baud)
    theta_b = np.pi * mode.baud / sample_rate
    theta_c = np.pi * frequency / sample_rate
    level_i_parts: list[np.ndarray] = []
    level_q_parts: list[np.ndarray] = []

    level_i_parts.append(np.zeros(max(frame_len_half - 1, 0), dtype=np.float64))
    level_q_parts.append(np.zeros(max(frame_len_half - 1, 0), dtype=np.float64))

    t = np.arange(frame_len_half + 1, 2 * frame_len_half, dtype=np.float64)
    phasev = theta_c * t
    if t.size:
        level_i_parts.append(np.round(-22000.0 * np.cos(theta_b * t) * np.cos(phasev)))
        level_q_parts.append(np.round(-22000.0 * np.cos(theta_b * t) * np.sin(phasev)))
        phase0 = float(phasev[-1])
    else:
        phase0 = 0.0

    curphase = 0
    t_full = np.arange(1, 2 * frame_len_half, dtype=np.float64)
    cos_shape = np.cos(theta_b * t_full)
    ones = np.ones_like(t_full)

    for sym in symbols:
        prephase = curphase
        curphase = (curphase + int(sym)) % 4
        prev_i, prev_q = QPSK_SIGNS[prephase]
        curr_i, curr_q = QPSK_SIGNS[curphase]
        env_i = prev_i * cos_shape if prev_i != curr_i else curr_i * ones
        env_q = prev_q * cos_shape if prev_q != curr_q else curr_q * ones
        phasev = phase0 + theta_c * t_full
        level_i_parts.append(np.round(22000.0 * env_i * np.cos(phasev)))
        level_q_parts.append(np.round(22000.0 * env_q * np.sin(phasev)))
        if phasev.size:
            phase0 = float(phasev[-1])

    t_tail = np.arange(1, frame_len_half, dtype=np.float64)
    cos_tail = np.cos(theta_b * t_tail)
    curr_i, curr_q = QPSK_SIGNS[curphase]
    phasev = phase0 + theta_c * t_tail
    if t_tail.size:
        level_i_parts.append(np.round(22000.0 * curr_i * cos_tail * np.cos(phasev)))
        level_q_parts.append(np.round(22000.0 * curr_q * cos_tail * np.sin(phasev)))

    level_i_parts.append(np.zeros(max(frame_len_half - 1, 0), dtype=np.float64))
    level_q_parts.append(np.zeros(max(frame_len_half - 1, 0), dtype=np.float64))

    level_i = np.concatenate(level_i_parts) if level_i_parts else np.zeros(0, dtype=np.float64)
    level_q = np.concatenate(level_q_parts) if level_q_parts else np.zeros(0, dtype=np.float64)
    wave_data = level_i[: min(level_i.size, level_q.size)] + level_q[: min(level_i.size, level_q.size)]
    if amplitude != 1.0 and wave_data.size:
        wave_data *= amplitude
    wave_data = np.clip(np.round(wave_data), -32767, 32767).astype(np.int16)
    pcm = array.array("h")
    pcm.frombytes(wave_data.tobytes())
    return pcm


def parse_varicode_table(source: Path, table_name: str) -> list[str]:
    text = source.read_text(encoding="latin-1")
    match = re.search(rf"static const char \*{re.escape(table_name)}\[\]\s*=\s*\{{(.*?)\}};", text, re.S)
    if not match:
        raise ValueError(f"Unable to find {table_name} in {source}")
    values = re.findall(r'"([01]+)"', match.group(1))
    if len(values) != 256:
        raise ValueError(f"{source}: expected 256 entries in {table_name}, found {len(values)}")
    return values


def load_varicode_tables(fldigi_root: Path) -> tuple[list[str], list[str]]:
    psk = parse_varicode_table(fldigi_root / "src" / "psk" / "pskvaricode.cxx", "varicodetab1")
    mfsk = parse_varicode_table(fldigi_root / "src" / "mfsk" / "mfskvaricode.cxx", "varicode")
    return psk, mfsk


def write_wav(path: Path, sample_rate: int, samples: array.array) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())


def make_samples(
    spec: ModeSpec,
    text: str,
    sample_rate: int,
    frequency: float,
    amplitude: float,
    psk_varicode: list[str],
    mfsk_varicode: list[str],
    legacy_single_carrier: bool,
) -> array.array:
    if legacy_single_carrier and spec.family == "bpsk" and spec.carriers == 1:
        return generate_legacy_bpsk(
            mode=spec,
            text=text,
            sample_rate=sample_rate,
            frequency=frequency,
            amplitude=amplitude,
            psk_varicode=psk_varicode,
        )
    if legacy_single_carrier and spec.family == "qpsk" and spec.carriers == 1:
        return generate_legacy_qpsk(
            mode=spec,
            text=text,
            sample_rate=sample_rate,
            frequency=frequency,
            amplitude=amplitude,
            psk_varicode=psk_varicode,
        )

    generator = PskGenerator(
        mode=spec,
        sample_rate=sample_rate,
        center_frequency=frequency,
        amplitude=amplitude,
        psk_varicode=psk_varicode,
        mfsk_varicode=mfsk_varicode,
    )
    return generator.generate(text)


def make_min_duration_samples(
    spec: ModeSpec,
    text: str,
    min_duration: float,
    sample_rate: int,
    frequency: float,
    amplitude: float,
    psk_varicode: list[str],
    mfsk_varicode: list[str],
    legacy_single_carrier: bool,
) -> array.array:
    payload = text if text else " "
    samples = make_samples(spec, payload, sample_rate, frequency, amplitude, psk_varicode, mfsk_varicode, legacy_single_carrier)
    target_frames = int(min_duration * sample_rate)
    if min_duration > 0 and 0 < len(samples) < target_frames:
        factor = max(2, math.ceil(target_frames / len(samples)))
        while len(samples) < target_frames:
            payload = (text if text else " ") * factor
            samples = make_samples(spec, payload, sample_rate, frequency, amplitude, psk_varicode, mfsk_varicode, legacy_single_carrier)
            factor *= 2
    return samples


def add_silence(samples: array.array, sample_rate: int, lead_seconds: float, tail_seconds: float) -> array.array:
    lead = int(lead_seconds * sample_rate)
    tail = int(tail_seconds * sample_rate)
    if lead <= 0 and tail <= 0:
        return samples
    out = array.array("h", [0]) * lead
    out.extend(samples)
    out.extend(array.array("h", [0]) * tail)
    return out


def read_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.input is not None:
        return Path(args.input).read_text(encoding=args.encoding)
    return Path(r"C:\projects\psk-script\input.txt").read_text(encoding=args.encoding)


def selected_modes(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(MODE_ORDER)
    if args.mode:
        missing = [mode for mode in args.mode if mode not in MODES]
        if missing:
            raise ValueError(f"Unknown mode(s): {', '.join(missing)}")
        return args.mode
    return list(MODE_ORDER)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate WAV files for fldigi-style PSK modes.")
    parser.add_argument("--fldigi-root", default=r"C:\projects\fldigi", help="Path to the fldigi checkout.")
    parser.add_argument("--out-dir", default=r"C:\projects\psk-script\generated-wav", help="Output directory.")
    parser.add_argument("--input", help="Text file to transmit.")
    parser.add_argument("--text", help="Literal text to transmit.")
    parser.add_argument("--encoding", default="utf-8", help="Encoding for --input text.")
    parser.add_argument("--sample-rate", type=int, default=48000, help="WAV sample rate.")
    parser.add_argument("--frequency", type=float, default=1500.0, help="Center audio frequency in Hz.")
    parser.add_argument("--amplitude", type=float, default=0.6, help="Peak amplitude, 0.0 to 1.0.")
    parser.add_argument("--duration", type=float, default=60.0, help="Minimum WAV duration in seconds. Use 0 to disable repetition.")
    parser.add_argument("--lead-silence", type=float, default=1.0, help="Seconds of silence before the transmission.")
    parser.add_argument("--tail-silence", type=float, default=1.0, help="Seconds of silence after the transmission.")
    parser.add_argument("--mode", action="append", help="Mode to generate. Repeat for multiple modes.")
    parser.add_argument("--all", action="store_true", help="Generate all supported modes.")
    parser.add_argument(
        "--legacy-single-carrier",
        action="store_true",
        help="Use the older numpy scripts for single-carrier BPSK/QPSK instead of fldigi-compatible generation.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not (0.0 < args.amplitude <= 1.0):
        parser.error("--amplitude must be in the range (0.0, 1.0]")
    if args.duration < 0:
        parser.error("--duration must be >= 0")
    if args.lead_silence < 0 or args.tail_silence < 0:
        parser.error("--lead-silence and --tail-silence must be >= 0")

    fldigi_root = Path(args.fldigi_root)
    out_dir = Path(args.out_dir)
    modes = selected_modes(args)

    text = read_text(args)
    psk_varicode, mfsk_varicode = load_varicode_tables(fldigi_root)

    for mode_name in modes:
        spec = MODES[mode_name]
        samples = make_min_duration_samples(
            spec=spec,
            text=text,
            min_duration=args.duration,
            sample_rate=args.sample_rate,
            frequency=args.frequency,
            amplitude=args.amplitude,
            psk_varicode=psk_varicode,
            mfsk_varicode=mfsk_varicode,
            legacy_single_carrier=args.legacy_single_carrier,
        )
        samples = add_silence(samples, args.sample_rate, args.lead_silence, args.tail_silence)
        out_path = out_dir / f"{mode_name}.wav"
        write_wav(out_path, args.sample_rate, samples)
        seconds = len(samples) / args.sample_rate
        print(f"{mode_name:10s} {out_path} {seconds:.2f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
