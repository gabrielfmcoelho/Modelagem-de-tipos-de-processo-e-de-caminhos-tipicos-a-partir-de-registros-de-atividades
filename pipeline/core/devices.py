
from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator
from typing import Literal

from .config import Settings

log = logging.getLogger(__name__)

DevicePreference = Literal["auto", "cuda", "xpu", "mps", "cpu"]
DtypePreference = Literal["bf16", "fp16", "fp32"]


def _torch():
    try:
        import torch
    except ImportError as e:
        raise RuntimeError(
            "torch is required for GPU acceleration. Install with "
            "`pip install -r requirements-gpu.txt` (CUDA) or "
            "`pip install torch` (CPU)."
        ) from e
    return torch


def _cuda_available() -> bool:
    try:
        torch = _torch()
    except RuntimeError:
        return False
    return torch.cuda.is_available() and torch.cuda.device_count() > 0


def _xpu_available() -> bool:
    try:
        torch = _torch()
    except RuntimeError:
        return False
    return hasattr(torch, "xpu") and torch.xpu.is_available()


def _mps_available() -> bool:
    try:
        torch = _torch()
    except RuntimeError:
        return False
    return (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
        and torch.backends.mps.is_built()
    )


def select_device(preference: str | None = None, settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    raw = (preference or settings.pipeline_device).strip().lower()

    if raw == "cpu":
        return "cpu"

    if raw == "cuda":
        if _cuda_available():
            return "cuda"
        log.warning("PIPELINE_DEVICE=cuda requested but CUDA unavailable — using CPU.")
        return "cpu"

    if raw == "xpu":
        if _xpu_available():
            return "xpu"
        log.warning("PIPELINE_DEVICE=xpu requested but XPU unavailable — using CPU.")
        return "cpu"

    if raw == "mps":
        if _mps_available():
            return "mps"
        log.warning("PIPELINE_DEVICE=mps requested but MPS unavailable — using CPU.")
        return "cpu"

    if _cuda_available():
        return "cuda"
    if _xpu_available():
        return "xpu"
    if _mps_available():
        return "mps"
    return "cpu"


def select_dtype(preference: str | None = None, settings: Settings | None = None):
    settings = settings or Settings.from_env()
    raw = (preference or settings.pipeline_dtype).strip().lower()
    torch = _torch()
    mapping = {
        "bf16": torch.bfloat16,
        "bfloat16": torch.bfloat16,
        "fp16": torch.float16,
        "float16": torch.float16,
        "half": torch.float16,
        "fp32": torch.float32,
        "float32": torch.float32,
        "full": torch.float32,
    }
    if raw not in mapping:
        log.warning("Unknown PIPELINE_DTYPE=%s — falling back to bf16.", raw)
        return torch.bfloat16
    return mapping[raw]


@contextlib.contextmanager
def autocast_for(
    device: str, dtype_preference: str | None = None, settings: Settings | None = None,
) -> Iterator[None]:
    if device not in ("cuda", "xpu"):
        yield
        return

    settings = settings or Settings.from_env()
    raw = (dtype_preference or settings.pipeline_dtype).strip().lower()
    if raw in ("fp32", "float32", "full"):
        yield
        return

    torch = _torch()
    dtype = select_dtype(dtype_preference, settings)
    with torch.autocast(device_type=device, dtype=dtype):
        yield


def device_summary(settings: Settings | None = None) -> str:
    settings = settings or Settings.from_env()
    dev = select_device(settings=settings)
    try:
        torch = _torch()
    except RuntimeError:
        return f"device={dev} (torch not installed)"
    bits = [f"device={dev}"]
    if dev == "cuda":
        try:
            n = torch.cuda.device_count()
            name = torch.cuda.get_device_name(0) if n else "?"
            bits.append(f"name={name!r}")
            bits.append(f"count={n}")
        except Exception as e:
            bits.append(f"name_err={e}")
    bits.append(f"dtype={settings.pipeline_dtype}")
    return " ".join(bits)
