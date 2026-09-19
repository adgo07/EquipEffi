from __future__ import annotations

import unittest

from tools.audit_hvac_boundaries import audit_payload


def _record(data_id: str, minimum, maximum, *, min_inclusive=True, max_inclusive=True):
    return {
        "data_id": data_id,
        "table": "表1",
        "conditions": {"category": "测试机组"},
        "range_metric": "cooling_capacity_kw",
        "metric_field": "primary_metric_value",
        "metric_name": "COP",
        "min": minimum,
        "max": maximum,
        "min_inclusive": min_inclusive,
        "max_inclusive": max_inclusive,
    }


class HvacBoundaryAuditTests(unittest.TestCase):
    def test_real_hvac_resource_has_no_boundary_findings(self):
        from pathlib import Path
        import json

        root = Path(__file__).resolve().parents[2]
        payload = json.loads((root / "src/equipeffi/resources/standards/hvac_thresholds.json").read_text(encoding="utf-8"))
        result = audit_payload(payload)
        self.assertTrue(result["is_valid"], result["findings"])
        self.assertEqual(result["finding_count"], 0)
        self.assertGreater(result["groups_checked"], 0)

    def test_open_endpoint_is_contiguous(self):
        payload = {"devices": {"test": {"records": [
            _record("A", None, 10, max_inclusive=True),
            _record("B", 10, None, min_inclusive=False),
        ]}}}
        result = audit_payload(payload)
        self.assertTrue(result["is_valid"], result["findings"])

    def test_closed_closed_endpoint_is_overlap(self):
        payload = {"devices": {"test": {"records": [
            _record("A", None, 10, max_inclusive=True),
            _record("B", 10, None, min_inclusive=True),
        ]}}}
        result = audit_payload(payload)
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["findings"][0]["type"], "overlap")

    def test_open_open_endpoint_is_gap(self):
        payload = {"devices": {"test": {"records": [
            _record("A", None, 10, max_inclusive=False),
            _record("B", 10, None, min_inclusive=False),
        ]}}}
        result = audit_payload(payload)
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["findings"][0]["type"], "gap")


if __name__ == "__main__":
    unittest.main()
