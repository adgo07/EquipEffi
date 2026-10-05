from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


class BuildLockTests(unittest.TestCase):
    def test_second_process_is_rejected_without_waiting(self):
        script = """from pathlib import Path
import sys
import time
from tools.build_lock import build_lock

with build_lock(Path(sys.argv[1]), operation='测试构建'):
    print('locked', flush=True)
    time.sleep(0.8)
"""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            first = subprocess.Popen(
                [sys.executable, "-c", script, str(root)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            try:
                self.assertEqual(first.stdout.readline().strip(), "locked")
                second = subprocess.run(
                    [sys.executable, "-c", script, str(root)],
                    cwd=str(ROOT),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=3,
                )
                self.assertNotEqual(second.returncode, 0)
                self.assertIn("已有测试构建在运行", second.stderr)
            finally:
                first.wait(timeout=3)
                if first.stdout is not None:
                    first.stdout.close()
                if first.stderr is not None:
                    first.stderr.close()

    def test_human_review_builder_acquires_same_project_lock(self):
        from tools import build_human_review_book

        marker = Path(tempfile.gettempdir()) / "equipeffi-human-review-lock-test.xlsx"
        with patch.object(build_human_review_book, "_write_book_unlocked", return_value=marker) as unlocked:
            result = build_human_review_book._write_book(marker)
        self.assertEqual(result, marker)
        unlocked.assert_called_once_with(marker)


if __name__ == "__main__":
    unittest.main()
