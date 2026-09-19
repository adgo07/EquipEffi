import io
import json
import unittest

from equipeffi.entrypoint import _api
from equipeffi.presentation.api.jsonl_server import MAX_REQUEST_LINE_BYTES, run_jsonl


class JsonlServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _api()

    def test_jsonl_handles_status_and_evaluation_in_order(self):
        incoming = io.StringIO(
            '{"request_id":"s-1","op":"status"}\n'
            '{"request_id":"e-1","op":"evaluate","payload":{"device_type":"motor","values":{'
            '"category":"三相异步电动机","rated_voltage":"0.4","rated_power":7.5,'
            '"poles":4,"rated_speed":1480,"efficiency":98}}}\n'
        )
        outgoing = io.StringIO()
        run_jsonl(self.api, incoming, outgoing)
        lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
        self.assertEqual([line["ok"] for line in lines], [True, True])
        self.assertEqual([line["protocol_version"] for line in lines], ["1.0", "1.0"])
        self.assertEqual(lines[0]["op"], "status")
        self.assertEqual(lines[0]["request_id"], "s-1")
        self.assertEqual(lines[0]["result"]["public_device_type_count"], 15)
        self.assertEqual(lines[1]["result"]["conclusion"], "1级")

    def test_jsonl_returns_line_errors_and_stops_only_on_quit(self):
        incoming = io.StringIO('not-json\n{"request_id":"u-1","op":"unknown"}\n{"request_id":"q-1","op":"quit"}\n{"op":"status"}\n')
        outgoing = io.StringIO()
        run_jsonl(self.api, incoming, outgoing)
        lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
        self.assertEqual([line["ok"] for line in lines], [False, False, True])
        self.assertEqual(lines[1]["request_id"], "u-1")
        self.assertEqual(lines[-1]["result"], {"stopped": True})

    def test_jsonl_rejects_incompatible_protocol_version_and_continues(self):
        incoming = (
            '{"request_id":"bad-v","protocol_version":"9.0","op":"status"}\n'
            '{"request_id":"q-v","protocol_version":"1.0","op":"quit"}\n'
        )
        outgoing = io.StringIO()
        run_jsonl(self.api, io.StringIO(incoming), outgoing)
        lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
        self.assertEqual(lines[0]["ok"], False)
        self.assertEqual(lines[0]["error"]["type"], "ValueError")
        self.assertEqual(lines[1]["result"], {"stopped": True})

    def test_jsonl_rejects_oversized_line_and_continues(self):
        oversized = "x" * MAX_REQUEST_LINE_BYTES
        incoming = oversized + "\n{\"request_id\":\"q-size\",\"op\":\"quit\"}\n"
        outgoing = io.StringIO()
        run_jsonl(self.api, io.StringIO(incoming), outgoing)
        lines = [json.loads(line) for line in outgoing.getvalue().splitlines()]
        self.assertEqual(lines[0]["ok"], False)
        self.assertEqual(lines[0]["error"]["type"], "request_too_large")
        self.assertEqual(lines[1]["result"], {"stopped": True})


if __name__ == "__main__":
    unittest.main()
