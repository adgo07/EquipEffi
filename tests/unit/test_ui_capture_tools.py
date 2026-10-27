"""Capture tools must execute under -O, fail closed and preserve existing evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ("ui_stage1_capture", "ui_final_capture", "ui_records_layout_capture")


class CaptureToolTests(unittest.TestCase):
    def invoke(self, name, data, output, *, optimized=False, injection="", extra=()):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), QT_QPA_PLATFORM="offscreen",
                   PYTHONIOENCODING="utf-8")
        env.pop("QT_SCALE_FACTOR", None)
        command = [sys.executable] + (["-O"] if optimized else [])
        if injection:
            harness = ("import sys, runpy\nfrom unittest.mock import patch\n"
                       "sys.path.insert(0, 'tools')\n" + injection +
                       f"\nrunpy.run_path('tools/{name}.py', run_name='__main__')\n")
            command += ["-c", harness]
        else:
            command += [f"tools/{name}.py"]
        command += ["--data-root", str(data), "--output", str(output), *extra]
        return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=45)

    def evidence(self, output, name):
        return json.loads((output / ("capture.json" if name == TOOLS[0] else "operations.json")).read_text(encoding="utf-8"))

    def test_normal_and_optimized_execute_the_same_actions(self):
        with TemporaryDirectory() as temp:
            for name in TOOLS:
                outcomes = []
                for optimized in (False, True):
                    with self.subTest(tool=name, optimized=optimized):
                        base = Path(temp) / f"{name}-{optimized}"
                        result = self.invoke(name, base / "data", base / "images", optimized=optimized)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        evidence = self.evidence(base / "images", name)
                        self.assertEqual(evidence["status"], "completed")
                        self.assertFalse(evidence["failures"])
                        captures = evidence["captures"]
                        self.assertTrue(captures)
                        self.assertTrue(all((base / "images" / c["file"]).stat().st_size > 0 for c in captures))
                        outcomes.append([c["file"] for c in captures])
                        if name == TOOLS[0]:
                            self.assertTrue(evidence["analysis"]["record_id"])
                        elif name == TOOLS[1]:
                            batch = next(o for o in evidence["operations"] if "single_ids_before" in o)
                            self.assertEqual(batch["single_count_before"], 3)
                            self.assertEqual(batch["single_ids_before"], batch["single_ids_after"])
                            self.assertEqual(batch["batch_count_after"] - batch["batch_count_before"], 1)
                            self.assertTrue(batch["wait_completed"])
                        else:
                            self.assertTrue(all(c["complete_row_visible"] for c in captures))
                            for operation in evidence["roundtrips"]:
                                self.assertTrue(operation["detail_opened"])
                                self.assertEqual(operation["before"], operation["after"])
                                self.assertEqual(len(operation["detail"]["tabs"]), 2)
                self.assertEqual(*outcomes)

    def test_startup_action_save_and_early_close_fail_with_evidence(self):
        injections = {
            "startup": "patch('equipeffi.composition.create_settings_runtime', side_effect=OSError('startup injection')).start()",
            "action": "patch('equipeffi.presentation.qt.shell.MainWindow.open_analysis', side_effect=RuntimeError('action injection')).start()",
            "save": "patch('PySide6.QtGui.QPixmap.save', return_value=False).start()",
            "close": ("from equipeffi.presentation.qt.shell import MainWindow\nfrom PySide6.QtCore import QTimer\n"
                      "original_show=MainWindow.show\ndef show(window):\n original_show(window)\n QTimer.singleShot(0, window.close)\n"
                      "patch.object(MainWindow, 'show', show).start()"),
        }
        with TemporaryDirectory() as temp:
            for name in TOOLS:
                for label, injection in injections.items():
                    with self.subTest(tool=name, failure=label):
                        base = Path(temp) / f"{name}-{label}"
                        cleanup_probe = ("\nimport ui_capture_runtime\noriginal_close=ui_capture_runtime.close_logging\n"
                            "def close(logger):\n original_close(logger)\n print('LOG_CLOSED', file=sys.stderr)\n"
                            "ui_capture_runtime.close_logging=close\n")
                        result = self.invoke(name, base / "data", base / "images", optimized=True, injection=injection + cleanup_probe)
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        evidence = self.evidence(base / "images", name)
                        self.assertEqual(evidence["status"], "failed")
                        self.assertTrue(evidence["failures"])
                        if label != "startup":
                            self.assertIn("LOG_CLOSED", result.stderr)

    def test_timeout_and_unwritable_evidence_are_nonzero(self):
        with TemporaryDirectory() as temp:
            for name in TOOLS:
                base = Path(temp) / name
                result = self.invoke(name, base / "data", base / "images", extra=("--timeout-ms", "1000"),
                    injection="import time\npatch('equipeffi.composition.create_settings_runtime', side_effect=lambda **kw: time.sleep(10)).start()")
                self.assertEqual(result.returncode, 124, result.stderr)
                self.assertEqual(self.evidence(base / "images", name)["status"], "failed")
                bad = Path(temp) / (name + "-bad")
                result = self.invoke(name, bad / "data", bad / "images",
                    injection="patch('pathlib.Path.mkdir', side_effect=PermissionError('unwritable injection')).start()")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("JSON无法写入", result.stderr)
                self.assertFalse((bad / "images").exists())

    def test_rejects_existing_nested_and_file_paths_before_any_writes(self):
        with TemporaryDirectory() as temp:
            for name in TOOLS:
                for case in ("output", "data", "same", "nested-output", "nested-data", "file", "parent-file"):
                    with self.subTest(tool=name, case=case):
                        base = Path(temp) / f"{name}-{case}"
                        base.mkdir()
                        data, output = base / "data", base / "images"
                        if case in ("output", "data"):
                            target = output if case == "output" else data
                            target.mkdir()
                            (target / "keep.bin").write_bytes(b"preserve\x00\xff")
                        elif case == "same": output = data
                        elif case == "nested-output": output = data / "images"
                        elif case == "nested-data": data = output / "data"
                        elif case == "file": output.write_bytes(b"preserve")
                        else:
                            output.write_bytes(b"preserve")
                            output = output / "child"
                        before = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob("*") if p.is_file()}
                        result = self.invoke(name, data, output)
                        self.assertNotEqual(result.returncode, 0)
                        after = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob("*") if p.is_file()}
                        self.assertEqual(before, after)
                        self.assertEqual(sorted(p.name for p in base.iterdir()), sorted({p.split('/')[0].split('\\')[0] for p in before}))
