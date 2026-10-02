from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from equipeffi.entrypoint import main


class EntrypointTests(unittest.TestCase):

    def test_public_fan_examples_use_evaluator_field_names(self):
        from equipeffi.entrypoint import _public_example

        centrifugal = _public_example("centrifugal_fan")
        axial = _public_example("axial_fan")
        self.assertEqual(centrifugal["machine_no"], 10)
        self.assertIn("pressure_coefficient", centrifugal)
        self.assertIn("specific_speed", centrifugal)
        self.assertEqual(axial["machine_no"], 10)
        self.assertIn("hub_ratio", axial)

    def run_entrypoint(self, *args: str) -> str:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(args), 0)
        return output.getvalue()

    def test_list_device_types_is_public_15_type_contract(self):
        payload = json.loads(self.run_entrypoint("--list-device-types"))
        self.assertEqual(len(payload), 15)
        self.assertEqual(payload["motor"]["sheet"], "电动机")

    def test_status_reports_inactive_pmsm_and_catalog_scope(self):
        payload = json.loads(self.run_entrypoint("--status"))
        self.assertEqual(payload["public_device_type_count"], 15)
        self.assertTrue(payload["elimination"]["has_industry_catalog"])
        pmsm = next(item for item in payload["standard_packs"] if item["device_type"] == "motor_pmsm")
        self.assertEqual(pmsm["status"], "active")

    def test_api_loads_bundled_v4_contract(self):
        from equipeffi.entrypoint import _api

        schema = _api().schema("motor")
        self.assertGreater(len(schema["fields"]), 0)
        self.assertEqual(schema["fields"][0]["field_id"], "device_name")

    def test_core_api_can_skip_v4_template_loading(self):
        """JSON/status callers must not parse the XLSX template eagerly."""
        from equipeffi import composition as bootstrap
        from equipeffi.entrypoint import _api

        with patch.object(bootstrap, "load_v4_contract", side_effect=AssertionError("template must stay lazy")):
            api = _api(load_template=False)
        self.assertIsNone(api.contract)
        self.assertEqual(len(api.device_types()), 15)

    def test_status_path_does_not_load_v4_template(self):
        from equipeffi import composition as bootstrap

        with patch.object(bootstrap, "load_v4_contract", side_effect=AssertionError("template must stay lazy")):
            payload = json.loads(self.run_entrypoint("--status"))
        self.assertEqual(payload["public_device_type_count"], 15)

    def test_transformer_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import TransformerEvaluator as LegacyTransformerEvaluator
        from equipeffi.domain.evaluation.evaluators.transformer import TransformerEvaluator

        self.assertIs(LegacyTransformerEvaluator, TransformerEvaluator)

    def test_compressor_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import CompressorEvaluator as LegacyCompressorEvaluator
        from equipeffi.domain.evaluation.evaluators.compressor import CompressorEvaluator

        self.assertIs(LegacyCompressorEvaluator, CompressorEvaluator)

    def test_submersible_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import SubmersibleEvaluator as LegacySubmersibleEvaluator
        from equipeffi.domain.evaluation.evaluators.submersible import SubmersibleEvaluator

        self.assertIs(LegacySubmersibleEvaluator, SubmersibleEvaluator)

    def test_boiler_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import BoilerEvaluator as LegacyBoilerEvaluator
        from equipeffi.domain.evaluation.evaluators.boiler import BoilerEvaluator

        self.assertIs(LegacyBoilerEvaluator, BoilerEvaluator)

    def test_heat_treatment_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import HeatTreatmentEvaluator as LegacyHeatTreatmentEvaluator
        from equipeffi.domain.evaluation.evaluators.heat_treatment import HeatTreatmentEvaluator

        self.assertIs(LegacyHeatTreatmentEvaluator, HeatTreatmentEvaluator)

    def test_blower_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import BlowerEvaluator as LegacyBlowerEvaluator
        from equipeffi.domain.evaluation.evaluators.blower import BlowerEvaluator

        self.assertIs(LegacyBlowerEvaluator, BlowerEvaluator)

    def test_fan_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import FanEvaluator as LegacyFanEvaluator
        from equipeffi.domain.evaluation.evaluators.fan import FanEvaluator

        self.assertIs(LegacyFanEvaluator, FanEvaluator)

    def test_hvac_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import HvacEvaluator as LegacyHvacEvaluator
        from equipeffi.domain.evaluation.evaluators.hvac import HvacEvaluator

        self.assertIs(LegacyHvacEvaluator, HvacEvaluator)

    def test_motor_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import MotorEvaluator as LegacyMotorEvaluator
        from equipeffi.domain.evaluation.evaluators.motor import MotorEvaluator

        self.assertIs(LegacyMotorEvaluator, MotorEvaluator)

    def test_pmsm_split_keeps_legacy_export_identity(self):
        from equipeffi.domain.evaluation.device_evaluators import PmsmEvaluator as LegacyPmsmEvaluator
        from equipeffi.domain.evaluation.evaluators.motor import PmsmEvaluator

        self.assertIs(LegacyPmsmEvaluator, PmsmEvaluator)

    def test_shared_helpers_are_the_legacy_export_source(self):
        from equipeffi.domain.evaluation import device_evaluators as legacy
        from equipeffi.domain.evaluation.evaluators import shared

        for name in ("_value", "_interval_hit", "_result", "_record_matches"):
            with self.subTest(name=name):
                self.assertIs(getattr(legacy, name), getattr(shared, name))

    def test_evaluator_registry_is_the_legacy_factory_source(self):
        from equipeffi.domain.evaluation import device_evaluators as legacy
        from equipeffi.domain.evaluation.evaluator_registry import EVALUATOR_FACTORIES

        self.assertIs(legacy.EVALUATOR_FACTORIES, EVALUATOR_FACTORIES)
        self.assertEqual(set(EVALUATOR_FACTORIES), {
            "transformer", "motor_lv", "motor_hv", "motor_pmsm", "compressor",
            "pump_water", "pump_chemical", "fan", "blower", "submersible",
            "boiler", "heat_treatment", "heat_pump_chiller",
            "heat_pump_water_heater", "duct_ac", "unitary_ac", "multi_split_ac",
        })

    def test_json_evaluation_does_not_require_desktop_window(self):
        payload = json.loads(self.run_entrypoint(
            "--device-type", "motor", "--json",
            '{"category":"三相异步电动机（一般用途）","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}',
        ))
        self.assertEqual(payload["conclusion"], "1级")
        self.assertEqual(payload["public_device_type"], "motor")

    def test_json_evaluation_accepts_as_of(self):
        payload = json.loads(self.run_entrypoint(
            "--device-type", "motor", "--as-of", "2027-03-04", "--json",
            '{"category":"三相异步电动机（一般用途）","rated_voltage":"0.4","rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}',
        ))
        normalization = next(item for item in payload["trace"] if item.get("step_type") == "输入规范化")
        self.assertEqual(normalization["as_of"], "2027-03-04")

    def test_batch_json_evaluation_returns_array(self):
        payload = json.loads(self.run_entrypoint(
            "--batch-json",
            '{"records":[{"record_id":"CLI-B1","device_type":"motor","values":{'
            '"category":"三相异步电动机（一般用途）","rated_voltage":"0.4",'
            '"rated_power":7.5,"poles":4,"rated_speed":1480,"efficiency":98}}]}',
        ))
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["record_id"], "CLI-B1")
        self.assertEqual(payload[0]["conclusion"], "1级")

    def test_example_is_available_from_public_entrypoint(self):
        payload = json.loads(self.run_entrypoint("--device-type", "transformer", "--example"))
        self.assertIn("category", payload)
        self.assertIn("capacity_kva", payload)

    def test_all_public_examples_are_accepted_by_json_api(self):
        """Keep the documented 15-class examples executable, not just printable."""
        from equipeffi.entrypoint import _api, _public_example
        from equipeffi.domain.evaluation.device_types import PUBLIC_DEVICE_TYPES

        api = _api()
        for device_type in PUBLIC_DEVICE_TYPES:
            with self.subTest(device_type=device_type):
                payload = api.evaluate({
                    "record_id": f"EX-{device_type}",
                    "device_type": device_type,
                    "values": _public_example(device_type),
                })
                self.assertIn("conclusion", payload)
                self.assertEqual(payload["public_device_type"], device_type)
                self.assertNotEqual(payload["conclusion"], "无法判定")

    def test_example_rejects_internal_profile(self):
        with self.assertRaises(SystemExit):
            main(("--device-type", "motor_lv", "--example"))

    def test_template_audit_is_available_without_desktop_or_excel(self):
        template = Path(__file__).resolve().parents[2] / "src" / "equipeffi" / "resources" / "templates" / "设备能效分析空白模板_重构版V4_20260825.xlsx"
        payload = json.loads(self.run_entrypoint("--audit-template", str(template)))
        self.assertTrue(payload["is_valid"])
        self.assertEqual(payload["forbidden_fields"], [])

    def test_core_json_api_imports_without_optional_site_packages(self):
        source_root = Path(__file__).resolve().parents[2] / "src"
        code = (
            "from equipeffi.entrypoint import _api; "
            "api=_api(); print(len(api.device_types())); "
            "print(api.evaluate({'device_type':'blower','values':{"
            "'category':'单级双支撑低速离心鼓风机','polytropic_efficiency':80,"
            "'impeller_width_mm':100,'impeller_diameter_mm':1000}})['conclusion'])"
        )
        # 子进程仍然使用 -S 运行，因此本测试依旧证明“没有 optional site-packages
        # 也能导入核心 JSON API”。这里只修复 Windows CI 可移植性：继承父环境而不是
        # 构造只含 PYTHONPATH 的空环境（Windows 上缺少 SystemRoot 等变量会影响子进程），
        # 并显式固定 UTF-8，避免依赖 runner 默认代码页（cp1252）导致中文输出编解码失败。
        env = os.environ.copy()
        env["PYTHONPATH"] = str(source_root)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        completed = subprocess.run(
            [sys.executable, "-S", "-c", code],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        # 失败时把 stderr 带进断言信息，避免只看到一个 CalledProcessError。
        self.assertEqual(
            completed.returncode,
            0,
            msg=(
                "isolated python (-S) failed with exit "
                f"{completed.returncode}\n--- stdout ---\n{completed.stdout}"
                f"\n--- stderr ---\n{completed.stderr}"
            ),
        )
        self.assertEqual(completed.stdout.splitlines(), ["15", "节能评价值"])

    def test_gui_entrypoint_uses_packaged_launcher(self):
        with patch("equipeffi.presentation.desktop.launcher.launch_packaged_gui") as launch_gui:
            self.assertEqual(main(("--gui",)), 0)
        launch_gui.assert_called_once_with()

    def test_packaged_gui_falls_back_to_web_when_tk_runtime_is_missing(self):
        # tkinter may be importable while Tcl/Tk itself is not installed.  The
        # launcher should keep the same public API available through Web.
        from equipeffi.presentation.desktop import launcher

        TclError = type("TclError", (Exception,), {})
        with patch.object(launcher, "launch", side_effect=TclError("init.tcl missing")):
            with patch("equipeffi.presentation.web.server.run_web") as run_web:
                launcher.launch_packaged_gui()
        run_web.assert_called_once()
        args, kwargs = run_web.call_args
        self.assertEqual(args[1:3], ("127.0.0.1", 8765))
        self.assertTrue(kwargs["open_browser"])
        self.assertIsNotNone(kwargs["template_transfer"].download)

    def test_packaged_gui_keeps_excel_callbacks_as_ports_by_default(self):
        # Excel导入/回写暂不进入手工输入MVP；启动器只保留端口，
        # 环境变量不能绕过当前阶段边界启用试验实现。
        from equipeffi.presentation.desktop import launcher

        with patch.object(launcher, "launch") as launch_window:
            launcher.launch_packaged_gui()
        _args, kwargs = launch_window.call_args
        callbacks = kwargs["callbacks"]
        self.assertIsNotNone(callbacks.download_template)
        self.assertIsNone(callbacks.upload_workbook)
        self.assertIsNone(callbacks.export_workbook)

    def test_packaged_gui_does_not_enable_excel_adapter_from_environment(self):
        from equipeffi.presentation.desktop import launcher

        with patch.dict("os.environ", {"EQUIPEFFI_ENABLE_EXCEL_ADAPTER": "1"}, clear=False):
            with patch.object(launcher, "launch") as launch_window:
                launcher.launch_packaged_gui()
        callbacks = launch_window.call_args.kwargs["callbacks"]
        self.assertIsNone(callbacks.upload_workbook)
        self.assertIsNone(callbacks.export_workbook)

    def test_web_entrypoint_injects_static_template_download_port(self):
        with patch("equipeffi.presentation.web.server.run_web") as run_web:
            self.assertEqual(main(("--web", "--host", "127.0.0.1", "--port", "8766")), 0)
        run_web.assert_called_once()
        args, kwargs = run_web.call_args
        self.assertEqual(args[1:3], ("127.0.0.1", 8766))
        self.assertFalse(kwargs["open_browser"])
        filename, content = kwargs["template_transfer"].download()
        self.assertTrue(filename.endswith(".xlsx"))
        self.assertGreater(len(content), 100_000)

    def test_batch_json_cannot_be_mixed_with_modes(self):
        with self.assertRaises(SystemExit):
            main(("--batch-json", '{"records":[]}', "--list-device-types"))

    def test_jsonl_mode_is_exposed_by_public_entrypoint(self):
        output = StringIO()
        incoming = StringIO('{"op":"status"}\n{"op":"quit"}\n')
        with patch("sys.stdin", incoming), redirect_stdout(output):
            self.assertEqual(main(("--jsonl",)), 0)
        lines = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([line["op"] for line in lines], ["status", "quit"])


if __name__ == "__main__":
    unittest.main()
