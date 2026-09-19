from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


class LinuxServiceScriptTests(unittest.TestCase):
    def test_service_template_has_runtime_placeholders(self):
        template = (ROOT / "scripts" / "equipeffi-web.service.template").read_text(encoding="utf-8")
        self.assertIn("__EQUIPEFFI_PYTHON__", template)
        self.assertIn("__EQUIPEFFI_HOST__", template)
        self.assertIn("__EQUIPEFFI_PORT__", template)
        self.assertIn("Restart=on-failure", template)

    def test_installer_exposes_safe_dry_run(self):
        script = (ROOT / "scripts" / "install_linux_service.sh").read_text(encoding="utf-8")
        self.assertIn('DRY_RUN=0', script)
        self.assertIn('"--dry-run"', script)
        self.assertIn("不会创建目录、虚拟环境或systemd服务", script)
        self.assertIn("systemctl --user enable --now equipeffi-web.service", script)

    def test_shell_syntax_when_bash_is_available(self):
        bash = shutil.which("bash")
        if not bash and Path(r"C:\Program Files\Git\bin\bash.exe").is_file():
            bash = str(Path(r"C:\Program Files\Git\bin\bash.exe"))
        if not bash:
            self.skipTest("当前环境没有bash")
        result = subprocess.run(
            [bash, "-n", str(ROOT / "scripts" / "install_linux_service.sh")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
