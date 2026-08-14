
from __future__ import annotations

from unittest import mock

import torch

from ..core import devices


class TestSelectDevice:
    def test_cpu_explicit_short_circuits(self):
        with mock.patch.object(devices, "_cuda_available", return_value=True):
            assert devices.select_device("cpu") == "cpu"

    def test_env_var_overrides_when_arg_absent(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DEVICE", "cpu")
        with mock.patch.object(devices, "_cuda_available", return_value=True):
            assert devices.select_device() == "cpu"

    def test_arg_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DEVICE", "cpu")
        with mock.patch.object(devices, "_cuda_available", return_value=True):
            assert devices.select_device("cuda") == "cuda"

    def test_cuda_falls_back_to_cpu_when_unavailable(self, caplog):
        with mock.patch.object(devices, "_cuda_available", return_value=False):
            assert devices.select_device("cuda") == "cpu"
        assert any("CUDA unavailable" in r.message for r in caplog.records)

    def test_xpu_falls_back_to_cpu_when_unavailable(self):
        with mock.patch.object(devices, "_xpu_available", return_value=False):
            assert devices.select_device("xpu") == "cpu"

    def test_mps_falls_back_to_cpu_when_unavailable(self):
        with mock.patch.object(devices, "_mps_available", return_value=False):
            assert devices.select_device("mps") == "cpu"

    def test_auto_prefers_cuda(self):
        with mock.patch.object(devices, "_cuda_available", return_value=True), \
             mock.patch.object(devices, "_xpu_available", return_value=True), \
             mock.patch.object(devices, "_mps_available", return_value=True):
            assert devices.select_device("auto") == "cuda"

    def test_auto_uses_xpu_when_no_cuda(self):
        with mock.patch.object(devices, "_cuda_available", return_value=False), \
             mock.patch.object(devices, "_xpu_available", return_value=True):
            assert devices.select_device("auto") == "xpu"

    def test_auto_uses_mps_when_no_cuda_or_xpu(self):
        with mock.patch.object(devices, "_cuda_available", return_value=False), \
             mock.patch.object(devices, "_xpu_available", return_value=False), \
             mock.patch.object(devices, "_mps_available", return_value=True):
            assert devices.select_device("auto") == "mps"

    def test_auto_falls_through_to_cpu(self):
        with mock.patch.object(devices, "_cuda_available", return_value=False), \
             mock.patch.object(devices, "_xpu_available", return_value=False), \
             mock.patch.object(devices, "_mps_available", return_value=False):
            assert devices.select_device("auto") == "cpu"

    def test_unknown_value_treated_as_auto(self):
        with mock.patch.object(devices, "_cuda_available", return_value=True):
            assert devices.select_device("nonsense") == "cuda"

    def test_whitespace_and_case_tolerant(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DEVICE", "  CPU  ")
        assert devices.select_device() == "cpu"


class TestSelectDtype:
    def test_default_is_bf16(self, monkeypatch):
        monkeypatch.delenv("PIPELINE_DTYPE", raising=False)
        assert devices.select_dtype() is torch.bfloat16

    def test_bf16_aliases(self):
        assert devices.select_dtype("bf16") is torch.bfloat16
        assert devices.select_dtype("bfloat16") is torch.bfloat16

    def test_fp16_aliases(self):
        assert devices.select_dtype("fp16") is torch.float16
        assert devices.select_dtype("float16") is torch.float16
        assert devices.select_dtype("half") is torch.float16

    def test_fp32_aliases(self):
        assert devices.select_dtype("fp32") is torch.float32
        assert devices.select_dtype("float32") is torch.float32
        assert devices.select_dtype("full") is torch.float32

    def test_unknown_value_falls_back_to_bf16(self, caplog):
        assert devices.select_dtype("nonsense") is torch.bfloat16
        assert any("Unknown PIPELINE_DTYPE" in r.message for r in caplog.records)

    def test_env_var_used_when_arg_absent(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DTYPE", "fp16")
        assert devices.select_dtype() is torch.float16


class TestAutocastFor:
    def test_cpu_is_no_op(self):
        with mock.patch("torch.autocast") as autocast:
            with devices.autocast_for("cpu"):
                pass
            autocast.assert_not_called()

    def test_mps_is_no_op(self):
        with mock.patch("torch.autocast") as autocast:
            with devices.autocast_for("mps"):
                pass
            autocast.assert_not_called()

    def test_fp32_skips_autocast_even_on_cuda(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DTYPE", "fp32")
        with mock.patch("torch.autocast") as autocast:
            with devices.autocast_for("cuda"):
                pass
            autocast.assert_not_called()

    def test_cuda_bf16_enters_autocast_with_correct_args(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DTYPE", "bf16")
        with mock.patch("torch.autocast") as autocast:
            with devices.autocast_for("cuda"):
                pass
            autocast.assert_called_once_with(device_type="cuda", dtype=torch.bfloat16)

    def test_xpu_fp16_enters_autocast(self, monkeypatch):
        monkeypatch.setenv("PIPELINE_DTYPE", "fp16")
        with mock.patch("torch.autocast") as autocast:
            with devices.autocast_for("xpu"):
                pass
            autocast.assert_called_once_with(device_type="xpu", dtype=torch.float16)


class TestDeviceSummary:
    def test_includes_device_marker(self):
        s = devices.device_summary()
        assert isinstance(s, str)
        assert "device=" in s
        assert "dtype=" in s

    def test_torch_missing_branch(self):
        with mock.patch.object(devices, "_torch", side_effect=RuntimeError("no torch")):
            s = devices.device_summary()
            assert "torch not installed" in s
