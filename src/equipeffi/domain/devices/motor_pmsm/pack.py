"""Decode the version-pinned candidate asset into immutable source tables."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping

from .numeric import PROFILE_ID, exact_decimal

PACK_ID = "gb30253_2024_candidate"
PACK_SHA256 = "b55a45b6de2930708a510b4132ed2a6f18c84f49fbfbdf93388b578ead446da7"
STANDARD_ID = "GB30253-2024"
SCHEMA = "equipeffi.motor-pmsm-candidate.v1"


class PmsmPackError(RuntimeError):
    """Failed to load the authoritative candidate resource or Profile."""


@dataclass(frozen=True)
class Axis:
    text: str
    low: Fraction | None
    high: Fraction | None
    include_low: bool = True

    @property
    def is_point(self) -> bool:
        return self.low is not None and self.low == self.high

    def includes(self, value: Fraction) -> bool:
        return (self.low is None or value > self.low or self.include_low and value == self.low) and (
            self.high is None or value <= self.high)

    @classmethod
    def from_source(cls, text: str) -> Axis:
        if "～" in text:
            low, high = text.split("～")
            return cls(text, exact_decimal(low.removeprefix(">")), exact_decimal(high), not low.startswith(">"))
        if text.startswith((">", "≥")):
            return cls(text, exact_decimal(text[1:]), None, text.startswith("≥"))
        if text.startswith("≤"):
            return cls(text, None, exact_decimal(text[1:]))
        point = exact_decimal(text)
        return cls(text, point, point)


@dataclass(frozen=True)
class Column:
    letter: str
    grade: int
    axis: Axis
    unit: str


@dataclass(frozen=True)
class Row:
    number: int
    power: Axis
    efficiencies: tuple[str, ...]
    pdf_page: int
    printed_page: int
    pdf_table_on_page: int
    pdf_row: int


@dataclass(frozen=True)
class Table:
    number: int
    sheet: str
    columns: tuple[Column, ...]
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class PmsmPack:
    tables: tuple[Table, ...]
    excluded_cells: Mapping[str, str]
    source_files: Mapping[str, Mapping[str, str]]
    resource_sha256: str
    integrity_sha256: str

    @classmethod
    def from_bytes(cls, payload: bytes) -> PmsmPack:
        try:
            pack = json.loads(payload)
            integrity = pack.pop("integrity_sha256")
            digest = sha256(json.dumps(pack, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
            if (digest != PACK_SHA256 or digest != integrity or pack["schema_version"] != SCHEMA
                    or pack["standard_id"] != STANDARD_ID or pack["numeric_profile_id"] != PROFILE_ID):
                raise PmsmPackError("永磁电机候选包身份或完整性错误")
            tables = tuple(
                Table(table["number"], table["sheet"], tuple(
                    Column(column["cell"][:-1], column["grade"], Axis.from_source(column["axis"]), column["unit"])
                    for column in table["columns"]), tuple(
                    Row(row["row"], Axis.from_source(row["power_kw"]), tuple(row["efficiencies_pct"]),
                        row["pdf_page"], row["printed_page"], row["pdf_table_on_page"], row["pdf_row"])
                    for row in table["rows"]))
                for table in pack["tables"]
            )
            source_files = {label: MappingProxyType(info) for label, info in pack["source_files"].items()}
            return cls(tables, MappingProxyType(pack["excluded_cells"]), MappingProxyType(source_files),
                       sha256(payload).hexdigest().upper(), digest)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise PmsmPackError("永磁电机候选包损坏") from exc
