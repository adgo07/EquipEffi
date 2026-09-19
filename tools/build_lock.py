"""跨平台构建互斥锁。

发布构建可能同时被桌面窗口、CI 或人工命令触发。多个 ``pip wheel`` /
PyInstaller 实例会重复编译并把 CPU 占满，因此构建入口使用同一把锁。
锁文件位于系统临时目录；进程异常退出时由操作系统释放，不会留下永久
阻塞状态，也不会修改项目目录。
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Iterator


class BuildInProgressError(RuntimeError):
    """已有同一项目的构建正在运行。"""


def _lock_path(root: Path) -> Path:
    key = hashlib.sha256(str(Path(root).resolve()).encode("utf-8")).hexdigest()[:20]
    return Path(tempfile.gettempdir()) / f"equipeffi-build-{key}.lock"


@contextmanager
def build_lock(root: Path, *, operation: str = "构建") -> Iterator[Path]:
    """以非阻塞方式取得项目级构建锁，成功时返回锁文件路径。"""

    path = _lock_path(Path(root))
    handle = path.open("a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, 2)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise BuildInProgressError(f"已有{operation}在运行（锁文件：{path}）") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise BuildInProgressError(f"已有{operation}在运行（锁文件：{path}）") from exc
        acquired = True
        yield path
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
