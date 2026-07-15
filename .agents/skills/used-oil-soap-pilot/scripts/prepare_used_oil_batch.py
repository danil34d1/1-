"""Create a Soap Calc oil record from a laboratory-tested UCO batch."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any, Mapping


NAOH_TO_KOH_MOLAR_RATIO = 40.0 / 56.1056


class BatchBlocked(ValueError):
    """The batch is incomplete or did not pass the project intake gate."""


def number(data: Mapping[str, Any], field: str) -> float:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BatchBlocked(f"{field} must be a laboratory numeric result, got {value!r}")
    return float(value)


def text(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BatchBlocked(f"{field} is required")
    return value.strip()


def build_record(data: Mapping[str, Any]) -> dict[str, Any]:
    batch_id = text(data, "batch_id")
    source = text(data, "source")
    report = text(data, "lab_report_number")
    measured_on = text(data, "measured_on")
    try:
        date.fromisoformat(measured_on)
    except ValueError as exc:
        raise BatchBlocked("measured_on must use YYYY-MM-DD") from exc

    sap = number(data, "sap_koh_mg_g")
    moisture = number(data, "moisture_pct")
    insolubles = number(data, "insolubles_pct")
    acid_value = number(data, "acid_value_mg_koh_g")

    errors: list[str] = []
    if not 100.0 <= sap <= 300.0:
        errors.append("sap_koh_mg_g is outside the project gate 100-300 mg/g")
    if not 0.0 <= moisture <= 1.0:
        errors.append("moisture_pct is outside the project gate 0-1%")
    if not 0.0 <= insolubles <= 1.0:
        errors.append("insolubles_pct is outside the project gate 0-1%")
    if acid_value < 0:
        errors.append("acid_value_mg_koh_g cannot be negative")
    if data.get("mineral_oil_detected") is not False:
        errors.append("mineral_oil_detected must be explicitly false")
    if data.get("detergent_detected") is not False:
        errors.append("detergent_detected must be explicitly false")
    if errors:
        raise BatchBlocked("; ".join(errors))

    sap_koh = sap / 1000.0
    fatty_acids = data.get("fatty_acids")
    profile = fatty_acids if isinstance(fatty_acids, dict) else {
        "lauric": 0.0,
        "myristic": 0.0,
        "palmitic": 0.0,
        "stearic": 0.0,
        "ricinoleic": 0.0,
        "oleic": 0.0,
        "linoleic": 0.0,
        "linolenic": 0.0,
    }
    profile_note = "laboratory profile supplied" if isinstance(fatty_acids, dict) else "fatty-acid profile unknown"

    return {
        "name": f"Used sunflower oil - batch {batch_id}",
        "sap_koh": round(sap_koh, 6),
        "sap_naoh": round(sap_koh * NAOH_TO_KOH_MOLAR_RATIO, 6),
        "iodine": float(data.get("iodine", 0.0)),
        "ins": float(data.get("ins", 0.0)),
        "fatty_acids": profile,
        "notes": (
            f"Batch-specific laboratory record. Source: {source}; report: {report}; "
            f"measured: {measured_on}; moisture: {moisture:g}%; "
            f"insolubles: {insolubles:g}%; acid value: {acid_value:g} mg KOH/g; "
            f"{profile_note}."
        ),
    }


def self_test() -> None:
    valid = {
        "batch_id": "UCO-001",
        "source": "Pilot cafe",
        "lab_report_number": "LAB-001",
        "measured_on": "2026-07-15",
        "sap_koh_mg_g": 190.0,
        "moisture_pct": 0.4,
        "insolubles_pct": 0.2,
        "acid_value_mg_koh_g": 5.0,
        "mineral_oil_detected": False,
        "detergent_detected": False,
    }
    record = build_record(valid)
    assert record["sap_koh"] == 0.19
    assert record["sap_naoh"] == round(0.19 * NAOH_TO_KOH_MOLAR_RATIO, 6)
    for field, value in (
        ("moisture_pct", 1.1),
        ("insolubles_pct", 1.1),
        ("mineral_oil_detected", True),
        ("detergent_detected", True),
        ("sap_koh_mg_g", "unknown"),
    ):
        blocked = dict(valid)
        blocked[field] = value
        try:
            build_record(blocked)
        except BatchBlocked:
            continue
        raise AssertionError(f"batch was not blocked for {field}={value!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", nargs="?", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("OK: UCO conversion and blocking self-tests passed")
        return 0
    if args.batch is None:
        parser.error("batch is required unless --self-test is used")

    try:
        record = build_record(json.loads(args.batch.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, BatchBlocked, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps([record], ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Created {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
