"""Candidate file identity across fresh Git checkouts and immutable records."""
from contextlib import closing
from hashlib import sha256
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

from equipeffi.application.services.motor_analysis_service import MotorAnalysisRequest
from equipeffi.application.services.motor_product_service import MotorHvAnalysisService
from equipeffi.application.services.motor_pmsm_analysis_service import MotorPmsmAnalysisService
from equipeffi.composition import create_motor_analysis_service, create_records_runtime
from equipeffi.domain.devices.motor_hv.calculator import Gb30254MotorCalculator
from equipeffi.domain.devices.motor_pmsm.calculator import Gb30253MotorCalculator
from equipeffi.infrastructure.persistence.app_data_paths import AppDataPaths
from equipeffi.infrastructure.standards.motor_hv_repository import load_motor_hv_pack
from equipeffi.infrastructure.standards.motor_pmsm_repository import load_motor_pmsm_pack

ROOT = Path(__file__).resolve().parents[1]
HV_PATH = Path("src/equipeffi/resources/standards/gb30254_2024_candidate.json")
PMSM_PATH = Path("src/equipeffi/resources/standards/gb30253_2024_candidate.json")
HV_VALUES = dict(category_id="gb30254_cage_induction", rated_voltage_v="3000",
                 rated_frequency_hz="50", cooling_method="IC01",
                 rated_output_power_kw="211", poles="2", rated_efficiency_pct="94.055")
PMSM_VALUES = dict(category_id="gb30253_lv_vfd", rated_voltage_v="380",
                   rated_output_power_kw="0.65", rated_speed_rpm="550", rated_efficiency_pct="82.125")


def git(directory, *arguments):
    environment = dict(os.environ)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    result = subprocess.run(["git", "-C", str(directory), *arguments],
                            env=environment, check=False, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def fresh_checkouts(directory, paths):
    """Seed exact repository blobs, then perform each first checkout independently."""
    seed = directory / "seed"
    seed.mkdir()
    git(seed, "init", "--quiet")
    git(seed, "config", "core.autocrlf", "false")
    git(seed, "config", "user.name", "Candidate identity fixture")
    git(seed, "config", "user.email", "candidate-fixture@example.invalid")
    (seed / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    expected = {}
    for path in paths:
        payload = git(ROOT, "cat-file", "blob", f"HEAD:{path.as_posix()}")
        expected[path] = payload
        destination = seed / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    git(seed, "add", "--", ".gitattributes", *(path.as_posix() for path in paths))
    git(seed, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Exact candidate fixture")
    for path in paths:
        if git(seed, "cat-file", "blob", f"HEAD:{path.as_posix()}") != expected[path]:
            raise AssertionError("Fixture changed the authoritative Git blob")
    for autocrlf in ("true", "false"):
        checkout = directory / f"checkout-{autocrlf}"
        git(directory, "clone", "--quiet", "--local", "--no-checkout", "--no-hardlinks",
            seed.as_posix(), checkout.as_posix())
        git(checkout, "config", "core.autocrlf", autocrlf)
        git(checkout, "checkout", "--quiet", "--force", "HEAD")
        yield autocrlf, checkout, expected


def high_voltage_service(path, records):
    pack, digest = load_motor_hv_pack(path)
    return MotorHvAnalysisService(pack, Gb30254MotorCalculator(), records=records, pack_sha256=digest)


def permanent_magnet_service(path, records):
    return MotorPmsmAnalysisService(load_motor_pmsm_pack(path), Gb30253MotorCalculator(), records=records)


CANDIDATES = (
    (HV_PATH, HV_VALUES, high_voltage_service),
    (PMSM_PATH, PMSM_VALUES, permanent_magnet_service),
)


def record_columns(database, record_id):
    with closing(sqlite3.connect(database)) as connection:
        return connection.execute("SELECT * FROM record WHERE record_id = ?", (record_id,)).fetchone()


class CandidateFileIdentityTests(unittest.TestCase):
    def assert_record_file_hash(self, service, values, path):
        expected = sha256(path.read_bytes()).hexdigest().upper()
        outcome = service.analyze_and_record(
            MotorAnalysisRequest(values, standard_code=getattr(service, "standard_code", None)))
        self.assertEqual(outcome.record_status, "SAVED")
        self.assertEqual(outcome.record.canonical_package_hash, expected)
        self.assertEqual(outcome.record.reference_snapshot["canonical_package_hash"], expected)
        self.assertEqual(outcome.result.references["canonical_package_hash"], expected)
        return outcome.record

    def test_fresh_checkouts_and_loaded_records_have_the_same_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = create_records_runtime(paths=AppDataPaths(root / "data"))[1]
            for autocrlf, checkout, expected in fresh_checkouts(root, (HV_PATH, PMSM_PATH)):
                for relative, values, service_factory in CANDIDATES:
                    with self.subTest(core_autocrlf=autocrlf, candidate=relative.name):
                        path = checkout / relative
                        self.assertEqual(path.read_bytes(), expected[relative])
                        self.assertNotIn(b"\r\n", path.read_bytes())
                        service = service_factory(path, records)
                        self.assertEqual(service._pack_sha256, sha256(expected[relative]).hexdigest().upper())
                        self.assert_record_file_hash(service, values, path)

    def test_current_runtime_file_hash_is_the_new_record_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            service = create_motor_analysis_service(paths=AppDataPaths(Path(directory)))
            for relative, values, _ in CANDIDATES:
                with self.subTest(candidate=relative.name):
                    path = ROOT / relative
                    self.assertEqual(path.read_bytes(), git(ROOT, "cat-file", "blob", f"HEAD:{relative.as_posix()}"))
                    self.assert_record_file_hash(service, values, path)

    def test_legacy_crlf_record_keeps_its_original_file_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = AppDataPaths(root / "data")
            records = create_records_runtime(paths=paths)[1]
            for relative, values, service_factory in CANDIDATES:
                with self.subTest(candidate=relative.name):
                    legacy_path = root / relative.name
                    payload = git(ROOT, "cat-file", "blob", f"HEAD:{relative.as_posix()}")
                    legacy_path.write_bytes(payload.replace(b"\n", b"\r\n"))
                    old = self.assert_record_file_hash(service_factory(legacy_path, records), values, legacy_path)
                    before = record_columns(paths.records_db, old.record_id)
                    path = ROOT / relative
                    current = self.assert_record_file_hash(service_factory(path, records), values, path)
                    self.assertNotEqual(old.canonical_package_hash, current.canonical_package_hash)
                    self.assertEqual(old.reference_snapshot["pack_sha256"], current.reference_snapshot["pack_sha256"])
                    self.assertEqual(record_columns(paths.records_db, old.record_id), before)
                    self.assertEqual(records.load_record(old.record_id), old)
