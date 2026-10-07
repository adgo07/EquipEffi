"""M3-G1 — 标准包实例级缓存正确性。

必须证明（Owner M3 要求）：

1. 第一次访问仍执行完整 ``read → parse → validate → SHA256``；
2. 同一 repository 实例的**后续访问不重复**磁盘读取 / parse / hash / 结构校验；
3. 返回对象仍**互相隔离**：调用方修改一次返回的 dict，不污染下一次 ``get_pack``；
4. **不改变** ``data_version``、source hash、provenance、``Decimal``、Canonical、
   Numeric、evaluator output。

缓存范围必须是 **repository instance scoped**：不得是进程级、磁盘级或跨启动缓存。
本模块只证明行为，不依赖实现细节（不改私有状态，只统计真实发生的 I/O 与解析）。
"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest import mock

from equipeffi.application.services.centrifugal_pump_analysis_service import (
    build_pump_evaluator,
)
from equipeffi.infrastructure.standards.json_repository import (
    JsonStandardRepository,
    StandardPackError,
    canonical_source_sha256,
)
from equipeffi.infrastructure.standards.pack_validator import StandardPackValidator


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "specs" / "equipment_efficiency" / "golden"


@contextmanager
def count_pack_load_work():
    """统计一次 ``get_pack`` 真正发生的磁盘读取 / JSON 解析 / 哈希 / 结构校验次数。"""

    import equipeffi.infrastructure.standards.json_repository as module

    counts = {"read_text": 0, "json_loads": 0, "sha256": 0, "validate": 0}
    real_read_text = Path.read_text
    real_loads = module.json.loads
    real_sha = module.canonical_source_sha256
    real_validate = StandardPackValidator.validate

    def counting_read_text(self, *args, **kwargs):
        counts["read_text"] += 1
        return real_read_text(self, *args, **kwargs)

    def counting_loads(*args, **kwargs):
        counts["json_loads"] += 1
        return real_loads(*args, **kwargs)

    def counting_sha(path):
        counts["sha256"] += 1
        return real_sha(path)

    def counting_validate(self, pack):
        counts["validate"] += 1
        return real_validate(self, pack)

    with mock.patch.object(Path, "read_text", counting_read_text), \
            mock.patch.object(module.json, "loads", counting_loads), \
            mock.patch.object(module, "canonical_source_sha256", counting_sha), \
            mock.patch.object(StandardPackValidator, "validate", counting_validate):
        yield counts


def _approved_golden_cases() -> list[tuple[str, dict]]:
    cases: list[tuple[str, dict]] = []
    for profile in ("pump_water", "pump_chemical"):
        for path in sorted((GOLDEN_ROOT / profile).glob("GC-PUMP-V*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if str(data.get("approval_status", "")).upper() == "APPROVED":
                cases.append((profile, data))
    return cases


class StandardPackFirstAccessTests(unittest.TestCase):
    """1 + 2：首次访问完整，后续访问不重复。"""

    def test_first_access_still_reads_parses_hashes_and_validates(self):
        repository = JsonStandardRepository(ROOT)  # 构造放计数块之外：清单读取不计入
        with count_pack_load_work() as counts:
            pack = repository.get_pack("pump_water")

        self.assertEqual(counts["read_text"], 1, "首次访问必须真实读取标准包文件")
        self.assertEqual(counts["json_loads"], 1, "首次访问必须真实解析 JSON")
        self.assertEqual(counts["sha256"], 1, "首次访问必须真实计算 source hash")
        self.assertEqual(counts["validate"], 1, "首次访问必须真实执行结构校验")
        self.assertIn("pack_hash", pack)

    def test_later_access_reuses_snapshot_without_disk_read(self):
        repository = JsonStandardRepository(ROOT)
        first = repository.get_pack("pump_water")

        with count_pack_load_work() as counts:
            repeats = [repository.get_pack("pump_water") for _ in range(5)]

        self.assertEqual(
            counts, {"read_text": 0, "json_loads": 0, "sha256": 0, "validate": 0},
            "同实例后续访问不得重复磁盘读取 / parse / hash / 结构校验")
        for repeat in repeats:
            self.assertEqual(repeat, first)

    def test_each_device_type_is_cached_separately(self):
        """同一 Canonical 文件服务两个设备类型时，各自只读一次。"""

        repository = JsonStandardRepository(ROOT)
        with count_pack_load_work() as first:
            repository.get_pack("pump_water")
        with count_pack_load_work() as second:
            chemical = repository.get_pack("pump_chemical")
        with count_pack_load_work() as third:
            repository.get_pack("pump_chemical")

        self.assertEqual(first["read_text"], 1)
        self.assertEqual(second["read_text"], 1, "另一个设备类型仍须自己读一次")
        self.assertEqual(second["validate"], 0, "同一 Canonical 源的结构校验仍只做一次")
        self.assertEqual(third["read_text"], 0)
        self.assertEqual(chemical["device_type"], "pump_chemical")


class StandardPackCacheIsolationTests(unittest.TestCase):
    """3：返回对象互相隔离，且缓存不是进程级共享。"""

    def test_caller_mutation_does_not_pollute_next_get_pack(self):
        repository = JsonStandardRepository(ROOT)
        expected = JsonStandardRepository(ROOT).get_pack("pump_water")

        mutated = repository.get_pack("pump_water")
        mutated["data_version"] = "MUTATED"
        mutated["pack_hash"] = "MUTATED"
        mutated["injected_by_caller"] = {"nested": [1, 2, 3]}
        mutated["water"]["formulas"]["单级"]["a"] = Decimal("-999")

        after = repository.get_pack("pump_water")
        self.assertEqual(after, expected)
        self.assertNotIn("injected_by_caller", after)
        self.assertNotEqual(after["data_version"], "MUTATED")

    def test_successive_returns_do_not_share_nested_objects(self):
        repository = JsonStandardRepository(ROOT)
        one = repository.get_pack("pump_water")
        two = repository.get_pack("pump_water")

        self.assertIsNot(one, two)
        self.assertIsNot(one["water"], two["water"])
        self.assertIsNot(one["water"]["formulas"], two["water"]["formulas"])

    def test_cache_is_instance_scoped_not_process_global(self):
        first_repo = JsonStandardRepository(ROOT)
        second_repo = JsonStandardRepository(ROOT)

        with count_pack_load_work() as first:
            first_repo.get_pack("pump_water")
        with count_pack_load_work() as second:
            second_repo.get_pack("pump_water")

        self.assertEqual(first["read_text"], 1)
        self.assertEqual(second["read_text"], 1,
                         "另一个 repository 实例仍必须自己读一次（不是进程级缓存）")

        pack_a = first_repo.get_pack("pump_water")
        pack_b = second_repo.get_pack("pump_water")
        self.assertIsNot(pack_a, pack_b)
        pack_a["data_version"] = "MUTATED"
        self.assertNotEqual(second_repo.get_pack("pump_water")["data_version"], "MUTATED")


class StandardPackCacheSemanticsTests(unittest.TestCase):
    """4：元数据 / source hash / Decimal / Canonical 语义不因缓存改变。"""

    def setUp(self):
        self.repository = JsonStandardRepository(ROOT)
        self.repository.get_pack("pump_water")          # 预热：填充实例缓存
        self.cached = self.repository.get_pack("pump_water")   # 从缓存返回
        self.fresh = JsonStandardRepository(ROOT).get_pack("pump_water")  # 无缓存路径

    def test_cached_and_uncached_packs_are_identical(self):
        self.assertEqual(self.cached, self.fresh)

    def test_data_version_and_provenance_fields_are_unchanged(self):
        entry = next(item for item in self.repository.list_packs()
                     if item["device_type"] == "pump_water")

        self.assertEqual(self.cached["pack_id"], entry["pack_id"])
        self.assertEqual(self.cached["data_version"], entry["data_version"])
        self.assertEqual(self.cached["device_type"], "pump_water")
        self.assertEqual(self.cached["status"], entry.get("status", self.cached["status"]))
        self.assertEqual(self.cached["source_file"], self.fresh["source_file"])
        self.assertTrue(self.cached["source_file"].replace("\\", "/").endswith(
            str(entry["source"]).replace("\\", "/")))

    def test_source_hash_is_recomputed_from_canonical_file(self):
        entry = next(item for item in self.repository.list_packs()
                     if item["device_type"] == "pump_water")
        source = ROOT / "src" / "equipeffi" / Path(str(entry["source"]))

        expected = canonical_source_sha256(source)
        self.assertEqual(self.cached["pack_hash"], expected)
        self.assertEqual(self.cached["pack_hash"], self.fresh["pack_hash"])
        self.assertEqual(len(self.cached["pack_hash"]), 64)
        self.assertEqual(self.cached["pack_hash"], self.cached["pack_hash"].upper())

    def test_canonical_decimal_lexemes_are_preserved(self):
        entry = next(item for item in self.repository.list_packs()
                     if item["device_type"] == "pump_water")
        source = ROOT / "src" / "equipeffi" / Path(str(entry["source"]))
        raw = json.loads(source.read_text(encoding="utf-8"), parse_float=Decimal)

        # Canonical 源按十进制字面量解析；缓存返回的必须是同一批 Decimal 值。
        self.assertEqual(self.cached["water"], raw["water"])
        coefficient = self.cached["water"]["formulas"]["单级"]["a"]
        self.assertIsInstance(coefficient, Decimal)
        self.assertEqual(coefficient, raw["water"]["formulas"]["单级"]["a"])

    def test_failed_validation_is_not_cached(self):
        repository = JsonStandardRepository(ROOT)
        original = repository._validator.validate
        repository._validator.validate = lambda _pack: ["测试结构错误"]
        try:
            with self.assertRaises(StandardPackError):
                repository.get_pack("transformer")
            with self.assertRaises(StandardPackError):
                repository.get_pack("transformer")
        finally:
            repository._validator.validate = original


class CachedPackEvaluatorOutputTests(unittest.TestCase):
    """4：Approved Golden 原输入回放，缓存 pack 与全新 pack 的 evaluator output 完全一致。"""

    def test_29_approved_golden_evaluator_output_is_identical(self):
        cases = _approved_golden_cases()
        self.assertEqual(len(cases), 29, "Approved Golden 必须仍是 18 water + 11 chemical")

        cached_repo = JsonStandardRepository(ROOT)
        fresh_repo = JsonStandardRepository(ROOT)
        cached_repo.get_pack("pump_water")
        cached_repo.get_pack("pump_chemical")

        for profile, case in cases:
            with self.subTest(case_id=case["case_id"]):
                evaluator = build_pump_evaluator(profile)
                fresh_result = evaluator.evaluate(
                    case["raw_inputs"], fresh_repo.get_pack(profile))
                cached_result = evaluator.evaluate(
                    case["raw_inputs"], cached_repo.get_pack(profile))
                self.assertEqual(cached_result, fresh_result)


if __name__ == "__main__":
    unittest.main()
