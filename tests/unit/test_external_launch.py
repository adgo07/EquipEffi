from __future__ import annotations

import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from equipeffi.infrastructure import external_launch


ROOT = Path(__file__).resolve().parents[2]


class _FakeApi:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class _FakeKernel32:
    def __init__(self, dll_directory: str):
        self.dll_directory = dll_directory
        self.GetDllDirectoryW = _FakeApi(self._get_dll_directory)
        self.SetDllDirectoryW = _FakeApi(self._set_dll_directory)

    def _get_dll_directory(self, buffer_length, buffer):
        if buffer_length == 0:
            return len(self.dll_directory)
        if not self.dll_directory:
            return 0
        if len(self.dll_directory) + 1 > buffer_length:
            return len(self.dll_directory) + 1
        buffer.value = self.dll_directory
        return len(self.dll_directory)

    def _set_dll_directory(self, path):
        self.dll_directory = path or ""
        return 1


class ExternalLaunchEnvironmentTests(unittest.TestCase):
    def test_filters_only_paths_within_bundle(self):
        bundle = r"C:\app\_internal"
        value = os.pathsep.join(
            [
                r"C:\tools\bin",
                bundle,
                bundle + r"\PySide6\plugins",
                bundle + r"-backup\bin",
            ]
        )
        self.assertEqual(
            external_launch._without_bundle_paths(value, bundle),
            os.pathsep.join([r"C:\tools\bin", bundle + r"-backup\bin"]),
        )
        self.assertIsNone(external_launch._without_bundle_paths(bundle, bundle))
        self.assertEqual(external_launch._without_bundle_paths("", bundle), "")

    def test_non_frozen_windows_run_is_unchanged(self):
        original_path = os.environ.get("PATH")
        with (
            patch.object(external_launch.sys, "platform", "win32"),
            patch.object(external_launch.sys, "frozen", False, create=True),
            patch.object(external_launch.ctypes, "WinDLL", side_effect=AssertionError, create=True),
        ):
            with external_launch.external_launch_environment():
                self.assertEqual(os.environ.get("PATH"), original_path)

    def test_non_windows_frozen_run_is_unchanged(self):
        original_path = os.environ.get("PATH")
        with (
            patch.object(external_launch.sys, "platform", "linux"),
            patch.object(external_launch.sys, "frozen", True, create=True),
            patch.object(external_launch.ctypes, "WinDLL", side_effect=AssertionError, create=True),
        ):
            with external_launch.external_launch_environment():
                self.assertEqual(os.environ.get("PATH"), original_path)

    @unittest.skipUnless(sys.platform == "win32", "Windows API behavior")
    def test_frozen_windows_normal_exit_restores_environment_and_dll_directory(self):
        bundle = r"C:\app\_internal"
        values = {
            "PATH": os.pathsep.join(
                [r"C:\Windows\System32", bundle, bundle + r"\PySide6", bundle + "-copy"]
            ),
            "QT_PLUGIN_PATH": os.pathsep.join([bundle + r"\PySide6\plugins", r"C:\Qt\plugins"]),
            "QML2_IMPORT_PATH": bundle + r"\PySide6\qml",
            "QT_QPA_PLATFORM_PLUGIN_PATH": bundle + r"\PySide6\plugins\platforms",
        }
        fake_kernel = _FakeKernel32(r"C:\Windows\System32")
        with patch.dict(os.environ, values, clear=False):
            original = {name: os.environ[name] for name in values}
            with (
                patch.object(external_launch.sys, "platform", "win32"),
                patch.object(external_launch.sys, "frozen", True, create=True),
                patch.object(external_launch.sys, "_MEIPASS", bundle, create=True),
                patch.object(external_launch.ctypes, "WinDLL", return_value=fake_kernel),
            ):
                with external_launch.external_launch_environment():
                    self.assertEqual(fake_kernel.dll_directory, "")
                    self.assertEqual(
                        os.environ["PATH"],
                        os.pathsep.join([r"C:\Windows\System32", bundle + "-copy"]),
                    )
                    self.assertEqual(os.environ["QT_PLUGIN_PATH"], r"C:\Qt\plugins")
                    self.assertNotIn("QML2_IMPORT_PATH", os.environ)
                    self.assertNotIn("QT_QPA_PLATFORM_PLUGIN_PATH", os.environ)
                self.assertEqual(fake_kernel.dll_directory, r"C:\Windows\System32")
                self.assertEqual({name: os.environ[name] for name in values}, original)

    @unittest.skipUnless(sys.platform == "win32", "Windows API behavior")
    def test_frozen_windows_exception_restores_environment_and_dll_directory(self):
        bundle = r"C:\app\_internal"
        fake_kernel = _FakeKernel32(r"C:\Windows\System32")
        with patch.dict(os.environ, {"PATH": bundle, "QT_PLUGIN_PATH": bundle}, clear=False):
            old_path = os.environ["PATH"]
            old_plugins = os.environ["QT_PLUGIN_PATH"]
            with (
                patch.object(external_launch.sys, "platform", "win32"),
                patch.object(external_launch.sys, "frozen", True, create=True),
                patch.object(external_launch.sys, "_MEIPASS", bundle, create=True),
                patch.object(external_launch.ctypes, "WinDLL", return_value=fake_kernel),
            ):
                with self.assertRaisesRegex(RuntimeError, "launch failed"):
                    with external_launch.external_launch_environment():
                        self.assertNotIn("QT_PLUGIN_PATH", os.environ)
                        self.assertEqual(fake_kernel.dll_directory, "")
                        raise RuntimeError("launch failed")
                self.assertEqual(fake_kernel.dll_directory, r"C:\Windows\System32")
                self.assertEqual(os.environ["PATH"], old_path)
                self.assertEqual(os.environ["QT_PLUGIN_PATH"], old_plugins)

    @unittest.skipUnless(sys.platform == "win32", "requires Windows GetDllDirectoryW/SetDllDirectoryW")
    def test_windows_api_restores_dll_directory_in_isolated_subprocess(self):
        script = r"""
import ctypes
import os
import sys
from equipeffi.infrastructure.external_launch import external_launch_environment, _get_dll_directory, _set_dll_directory

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
get_dll = kernel32.GetDllDirectoryW
get_dll.argtypes = (ctypes.c_uint32, ctypes.POINTER(ctypes.c_wchar))
get_dll.restype = ctypes.c_uint32
set_dll = kernel32.SetDllDirectoryW
set_dll.argtypes = (ctypes.c_wchar_p,)
set_dll.restype = ctypes.c_int
original = _get_dll_directory(get_dll)
desired = os.path.join(os.environ["WINDIR"], "System32")
try:
    _set_dll_directory(set_dll, desired)
    sys.frozen = True
    sys._MEIPASS = sys.argv[1]
    bundle = sys._MEIPASS
    os.environ["PATH"] = os.pathsep.join([bundle, bundle + "-neighbor", desired])
    os.environ["QT_PLUGIN_PATH"] = os.path.join(bundle, "PySide6", "plugins") + os.pathsep + r"C:\Qt\plugins"
    original_path = os.environ["PATH"]
    original_plugins = os.environ["QT_PLUGIN_PATH"]
    with external_launch_environment():
        assert _get_dll_directory(get_dll) == ""
        assert os.environ["PATH"] == os.pathsep.join([bundle + "-neighbor", desired])
        assert os.environ["QT_PLUGIN_PATH"] == r"C:\Qt\plugins"
    assert _get_dll_directory(get_dll) == desired
    assert os.environ["PATH"] == original_path
    assert os.environ["QT_PLUGIN_PATH"] == original_plugins
    try:
        with external_launch_environment():
            assert _get_dll_directory(get_dll) == ""
            raise RuntimeError("probe")
    except RuntimeError:
        pass
    assert _get_dll_directory(get_dll) == desired
    print("GetDllDirectoryW/SetDllDirectoryW restoration passed")
finally:
    _set_dll_directory(set_dll, original)
"""
        bundle = str(Path(tempfile.gettempdir()) / "equipeffi-test-_MEI")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        environment["WINDIR"] = os.environ.get("WINDIR", r"C:\Windows")
        environment["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
        completed = subprocess.run(
            [sys.executable, "-c", script, bundle],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("GetDllDirectoryW/SetDllDirectoryW restoration passed", completed.stdout)


if __name__ == "__main__":
    unittest.main()