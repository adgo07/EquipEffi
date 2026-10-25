"""Run unittest discovery and explicitly shut down Qt before Python exits."""

from __future__ import annotations

import argparse
import gc
from pathlib import Path
import sys
import threading
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _thread_state(
    baseline_ids: set[int],
) -> tuple[list[str], int, list[str], list[threading.Thread]]:
    from PySide6.QtCore import QThread, QThreadPool
    import shiboken6

    main_ptr = tuple(shiboken6.getCppPointer(QThread.currentThread()))
    running: list[str] = []
    seen: set[tuple[int, ...]] = set()
    for obj in gc.get_objects():
        try:
            cls = type(obj)
            if QThread not in cls.__mro__ or not shiboken6.isValid(obj):
                continue
            ptr = tuple(shiboken6.getCppPointer(obj))
            if not ptr or ptr == main_ptr or ptr in seen:
                continue
            seen.add(ptr)
            if obj.isRunning():
                running.append(f"{cls.__module__}.{cls.__qualname__}(objectName={obj.objectName()!r})")
        except (RuntimeError, TypeError) as exc:
            cls = type(obj)
            running.append(f"{cls.__module__}.{cls.__qualname__}(inspection failed: {exc})")

    python_threads = [
        t for t in threading.enumerate()
        if t.ident not in baseline_ids and t.is_alive()
    ]
    hard_fail_threads = [
        t for t in python_threads
        if not t.daemon and type(t).__name__ != "_DummyThread"
    ]
    diagnostics = [
        f"{t.name}(daemon={t.daemon}, type={type(t).__name__}, ident={t.ident})"
        for t in python_threads
    ]
    return running, QThreadPool.globalInstance().activeThreadCount(), diagnostics, hard_fail_threads


def _assert_quiescent(baseline_ids: set[int]) -> None:
    running_qthreads, pool_count, python_diagnostics, hard_fail_threads = _thread_state(baseline_ids)
    if python_diagnostics:
        print("[qt-shutdown] remaining Python threads (not joined or killed): "
              + ", ".join(python_diagnostics), flush=True)
    failures = []
    if running_qthreads:
        failures.append("running QThread wrappers: " + ", ".join(running_qthreads))
    if pool_count:
        failures.append(f"QThreadPool.activeThreadCount={pool_count}")
    if hard_fail_threads:
        failures.append("new live non-daemon Python threads: " + ", ".join(
            f"{t.name}(ident={t.ident})" for t in hard_fail_threads
        ))
    if failures:
        raise RuntimeError("Qt shutdown refused; workers remain active.\n" + "\n".join(failures))


def _shutdown_qt(baseline_ids: set[int]) -> bool:
    print("[qt-shutdown] before", flush=True)
    try:
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication
        import shiboken6

        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        _assert_quiescent(baseline_ids)
        print("[qt-shutdown] Qt workers quiescent", flush=True)

        if app is not None:
            for widget in list(app.topLevelWidgets()):
                if shiboken6.isValid(widget):
                    widget.close()
                    widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()
            remaining = [w for w in app.topLevelWidgets() if shiboken6.isValid(w)]
            if remaining:
                raise RuntimeError("Top-level Qt widgets remain: " + ", ".join(
                    f"{type(w).__module__}.{type(w).__qualname__}(objectName={w.objectName()!r})"
                    for w in remaining
                ))
        print("[qt-shutdown] widgets destroyed", flush=True)

        _assert_quiescent(baseline_ids)
        if app is not None:
            print("[qt-shutdown] before QApplication deletion", flush=True)
            shiboken6.delete(app)
            if shiboken6.isValid(app):
                raise RuntimeError("QApplication remains valid after explicit deletion")
            print("[qt-shutdown] QApplication deleted", flush=True)
        else:
            print("[qt-shutdown] no QApplication instance", flush=True)
        print(f"[qt-shutdown] gc collected={gc.collect()}", flush=True)
        print("[qt-shutdown] after", flush=True)
        return True
    except Exception:
        traceback.print_exc()
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-directory", default="tests")
    parser.add_argument("--top-level-directory", default=str(ROOT))
    parser.add_argument("--pattern", default="test*.py")
    parser.add_argument("--module", action="append", default=[],
                        help="run named unittest modules instead of discovery")
    args = parser.parse_args(argv)
    baseline_ids = {t.ident for t in threading.enumerate() if t.ident is not None}
    result = None
    suite_error = False
    try:
        loader = unittest.defaultTestLoader
        if args.module:
            suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in args.module)
        else:
            start = Path(args.start_directory)
            top = Path(args.top_level_directory)
            if not start.is_absolute():
                start = ROOT / start
            if not top.is_absolute():
                top = ROOT / top
            suite = loader.discover(str(start), pattern=args.pattern, top_level_dir=str(top))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    except Exception:
        suite_error = True
        traceback.print_exc()
    shutdown_ok = _shutdown_qt(baseline_ids)
    if suite_error or result is None or not result.wasSuccessful() or not shutdown_ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
