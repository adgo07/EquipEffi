"""Prepare a PyInstaller-frozen Windows process before launching external apps.

PyInstaller documents DLL search and PATH changes inherited by child processes:
https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#windows
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import ntpath
import os
import sys
from collections.abc import Iterator


_PATH_ENVIRONMENTS = (
    "PATH",
    "QT_PLUGIN_PATH",
    "QML2_IMPORT_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
)
_MISSING = object()


def _is_within_bundle_path(path: str, bundle_root: str | None) -> bool:
    """Return whether a Windows path equals or is below the bundle root."""

    if not path or not bundle_root:
        return False
    candidate = path.strip().strip('"')
    root = bundle_root.strip().strip('"')
    try:
        candidate = ntpath.normcase(ntpath.abspath(candidate))
        root = ntpath.normcase(ntpath.abspath(root))
        return ntpath.commonpath((candidate, root)) == root
    except (OSError, ValueError):
        return False


def _without_bundle_paths(value: str, bundle_root: str | None) -> str | None:
    """Remove only path-list entries inside the bundle; preserve external entries."""

    if not bundle_root:
        return value
    parts = value.split(os.pathsep)
    kept = [part for part in parts if not _is_within_bundle_path(part, bundle_root)]
    if len(kept) == len(parts):
        return value
    if not kept:
        return None
    return os.pathsep.join(kept)


def _get_dll_directory(getter: object) -> str:
    """Read the process DLL directory using GetDllDirectoryW."""

    ctypes.set_last_error(0)
    required = int(getter(0, None))  # type: ignore[operator]
    error = ctypes.get_last_error()
    if required == 0:
        if error:
            raise ctypes.WinError(error)
        return ""

    size = required + 1
    for _ in range(4):
        buffer = ctypes.create_unicode_buffer(size)
        ctypes.set_last_error(0)
        length = int(getter(size, buffer))  # type: ignore[operator]
        error = ctypes.get_last_error()
        if length == 0:
            if error:
                raise ctypes.WinError(error)
            return ""
        if length < size:
            return buffer.value
        # A too-small buffer returns the required size; add room for its NUL.
        size = length + 1

    raise OSError("GetDllDirectoryW did not return a complete path")


def _set_dll_directory(setter: object, path: str | None) -> None:
    """Set the process DLL directory and raise when the Windows API fails."""

    ctypes.set_last_error(0)
    if setter(path):  # type: ignore[operator]
        return
    error = ctypes.get_last_error()
    if error:
        raise ctypes.WinError(error)
    raise OSError("SetDllDirectoryW failed without an error code")


def _restore_environment(snapshot: dict[str, object]) -> None:
    for name, value in snapshot.items():
        if value is _MISSING:
            os.environ.pop(name, None)
        else:
            os.environ[name] = str(value)


@contextmanager
def external_launch_environment() -> Iterator[None]:
    """Temporarily remove this frozen bundle's DLL and Qt paths for OS launches.

    This is intentionally a no-op for source runs and non-Windows platforms.
    The original process state is restored after the external launch call.
    """

    if sys.platform != "win32" or not bool(getattr(sys, "frozen", False)):
        yield
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_dll_directory = kernel32.GetDllDirectoryW
    get_dll_directory.argtypes = (ctypes.c_uint32, ctypes.POINTER(ctypes.c_wchar))
    get_dll_directory.restype = ctypes.c_uint32
    set_dll_directory = kernel32.SetDllDirectoryW
    set_dll_directory.argtypes = (ctypes.c_wchar_p,)
    set_dll_directory.restype = ctypes.c_int

    original_dll_directory = _get_dll_directory(get_dll_directory)
    original_environment: dict[str, object] = {
        name: os.environ.get(name, _MISSING) for name in _PATH_ENVIRONMENTS
    }
    bundle_root = getattr(sys, "_MEIPASS", None)

    _set_dll_directory(set_dll_directory, None)
    try:
        for name in _PATH_ENVIRONMENTS:
            value = os.environ.get(name)
            if value is None:
                continue
            filtered = _without_bundle_paths(value, bundle_root)
            if filtered == value:
                continue
            if filtered is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = filtered
        yield
    finally:
        try:
            _restore_environment(original_environment)
        finally:
            _set_dll_directory(set_dll_directory, original_dll_directory)