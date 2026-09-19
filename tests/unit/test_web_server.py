from __future__ import annotations

import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from equipeffi.application.services.evaluation_facade import EvaluationFacade
from equipeffi.application.services.evaluation_service import EvaluationService
from equipeffi.infrastructure.standards.json_repository import JsonStandardRepository
from equipeffi.infrastructure.excel.template_resource import V4TemplateResource
from equipeffi.infrastructure.excel.v4_reader import V4WorkbookReaderImpl
from equipeffi.presentation.api.application_api import ApplicationApi
from equipeffi.presentation.web.server import TemplateTransferPort, create_server


ROOT = Path(__file__).resolve().parents[2]


class WebServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 与正式入口一致加载V4字段契约；Web层本身不复制或维护字段定义。
        contract = V4WorkbookReaderImpl().read_contract(V4TemplateResource().template_path)
        facade = EvaluationFacade(EvaluationService(JsonStandardRepository(ROOT)), contract=contract)
        cls.server = create_server(ApplicationApi(facade, contract=contract), port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def get(self, path: str):
        with urlopen(self.base + path, timeout=5) as response:
            raw = response.read()
            if response.headers.get_content_type() == "application/json":
                raw = json.loads(raw)
            return response.status, response.headers.get_content_type(), raw

    def test_index_and_public_contract_endpoints(self):
        status, content_type, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html")
        html = body.decode() if isinstance(body, bytes) else ""
        self.assertIn("设备能效分析", html)
        self.assertIn("上传V4工作簿", html)
        self.assertIn("summaryStandard", html)
        self.assertIn("summaryQuality", html)
        self.assertIn("schema&&schema.conclusion_field||'能效等级'", html)
        self.assertIn("URL.createObjectURL(blob)", html)
        self.assertIn("a.download='设备能效分析空白模板_重构版V4.xlsx'", html)
        self.assertIn("applyDynamicLimits", html)
        self.assertIn("input.accept='image/*'", html)
        self.assertIn("const seenFields=new Set()", html)
        status, _, types = self.get("/api/device-types")
        self.assertEqual((status, len(types)), (200, 15))
        status, _, schema = self.get("/api/schema?device_type=motor")
        self.assertEqual(status, 200)
        self.assertTrue(schema["fields"])
        efficiency = next(item for item in schema["fields"] if item["field_id"] == "efficiency")
        self.assertEqual((efficiency["minimum"], efficiency["maximum"]), (1, 100))
        self.assertTrue(schema["result_fields"])
        locked_ids = {item["field_id"] for item in schema["result_fields"]}
        self.assertTrue({"standard_code", "reference_grade", "conclusion", "auto_note"}.issubset(locked_ids))
        self.assertTrue(all(item["editable"] is False for item in schema["result_fields"]))

        status, _, capability = self.get("/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(capability["elimination"]["default_scope"], "高耗能落后机电设备淘汰目录第一至第四批")
        self.assertEqual(len(capability["elimination"]["scope_options"]), 3)

    def test_boiler_schema_exposes_condensing_efficiency_limit(self):
        status, _, schema = self.get("/api/schema?device_type=industrial_boiler")
        self.assertEqual(status, 200)
        field = next(item for item in schema["fields"] if item["field_id"] == "design_efficiency")
        self.assertEqual(field["conditional_limits"][0]["maximum"], 110)
        self.assertEqual(field["conditional_limits"][1]["maximum"], 100)

    def test_evaluate_endpoint_reuses_application_api(self):
        request = Request(
            self.base + "/api/evaluate",
            data=json.dumps({"device_type": "motor", "values": {
                "category": "三相异步电动机", "rated_voltage": "0.4", "rated_power": 7.5,
                "poles": 4, "rated_speed": 1480, "efficiency": 98,
            }}, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        self.assertEqual(result["conclusion"], "1级")
        self.assertIn("trace", result)

    def test_batch_evaluate_endpoint_preserves_record_order(self):
        payload = {"records": [
            {"record_id": "WEB-B2", "device_type": "motor", "values": {
                "category": "三相异步电动机", "rated_voltage": "0.4", "rated_power": 7.5,
                "poles": 4, "rated_speed": 1480, "efficiency": 98,
            }},
            {"record_id": "WEB-B1", "device_type": "motor", "values": {
                "category": "三相异步电动机", "rated_voltage": "0.4", "rated_power": 7.5,
                "poles": 4, "rated_speed": 1480, "efficiency": 98,
            }},
        ]}
        request = Request(
            self.base + "/api/evaluate-batch",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        self.assertEqual([item["record_id"] for item in result], ["WEB-B2", "WEB-B1"])

    def test_malformed_requests_return_json_errors(self):
        request = Request(self.base + "/api/evaluate", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=5)
        self.assertEqual(context.exception.code, 400)
        payload = json.loads(context.exception.read())
        self.assertIn("error", payload)

    def test_template_upload_is_explicit_adapter_placeholder(self):
        request = Request(
            self.base + "/api/template/upload",
            data=b"placeholder",
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=5)
        self.assertEqual(context.exception.code, 501)
        payload = json.loads(context.exception.read())
        self.assertIn("Excel适配器", payload["error"])

    def test_template_transfer_port_can_be_supplied_by_host_adapter(self):
        received = {}
        transfer = TemplateTransferPort(
            download=lambda: ("模板.xlsx", b"xlsx-bytes"),
            upload=lambda name, content: received.update(name=name, content=content) or {"accepted": True},
        )
        server = create_server(self.server.api, port=0, template_transfer=transfer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/template", timeout=5) as response:
                self.assertEqual(response.read(), b"xlsx-bytes")
                self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
            request = Request(
                base + "/api/template/upload",
                data=b"uploaded",
                headers={"Content-Type": "application/octet-stream", "X-Filename": "%E6%B5%8B%E8%AF%95.xlsx"},
                method="POST",
            )
            with urlopen(request, timeout=5) as response:
                self.assertEqual(json.loads(response.read())["accepted"], True)
            self.assertEqual(received, {"name": "测试.xlsx", "content": b"uploaded"})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
