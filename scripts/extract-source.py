"""Extract comparable 2020–2025 MHLW job-condition tables by company size."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import openpyxl

YEARS = list(range(2020, 2026))
SOURCES = {
    "weekend": "https://www.mhlw.go.jp/toukei/list/xls/114-1d-12.xlsx",
    "bonus": "https://www.mhlw.go.jp/toukei/list/xls/114-1d-15.xlsx",
    "commute": "https://www.mhlw.go.jp/toukei/list/xls/114-1d-18.xlsx",
}
SIZES = [
    ("ALL", "企業規模計"),
    ("LE4", "4人以下"),
    ("5-29", "5〜29人"),
    ("30-99", "30〜99人"),
    ("100-299", "100〜299人"),
    ("300-499", "300〜499人"),
    ("500-999", "500〜999人"),
    ("GE1000", "1,000人以上"),
]


def value(cell: object) -> int:
    if isinstance(cell, bool) or not isinstance(cell, (int, float)):
        raise ValueError(f"expected numeric cell, got {cell!r}")
    number = int(cell)
    if number < 0 or number != cell:
        raise ValueError(f"expected non-negative integer, got {cell!r}")
    return number


def series(sheet: object, row: int, columns: list[int]) -> list[int]:
    return [value(sheet.cell(row, column).value) for column in columns]


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: extract-source.py WEEKEND.xlsx BONUS.xlsx COMMUTE.xlsx OUTPUT_DIR")

    paths = {
        "weekend": Path(sys.argv[1]),
        "bonus": Path(sys.argv[2]),
        "commute": Path(sys.argv[3]),
    }
    output_directory = Path(sys.argv[4])
    books = {
        key: openpyxl.load_workbook(path, data_only=True, read_only=False)
        for key, path in paths.items()
    }
    weekend_sheet = books["weekend"].worksheets[0]
    bonus_sheet = books["bonus"].worksheets[1]
    commute_sheet = books["commute"].worksheets[1]
    if weekend_sheet.max_row < 10 or weekend_sheet.max_column < 76:
        raise ValueError("unexpected weekend workbook layout")
    if bonus_sheet.max_row < 18 or bonus_sheet.max_column < 8:
        raise ValueError("unexpected bonus workbook layout")
    if commute_sheet.max_row < 34 or commute_sheet.max_column < 8:
        raise ValueError("unexpected commute workbook layout")

    weekend_bases = [47, 52, 57, 62, 67, 72]
    records = []
    for offset, (size_id, name) in enumerate(SIZES):
        row = 3 + offset
        weekend_values = {key: [] for key in ("total", "complete", "other", "none")}
        for year_index, base in enumerate(weekend_bases):
            total, complete, biweekly, other, none = series(
                weekend_sheet, row, list(range(base, base + 5))
            )
            if total != complete + biweekly + other + none:
                raise ValueError(f"weekend categories do not sum for {size_id} {YEARS[year_index]}")
            weekend_values["total"].append(total)
            weekend_values["complete"].append(complete)
            weekend_values["other"].append(biweekly + other)
            weekend_values["none"].append(none)

        bonus_values = {"yes": [], "no": []}
        commute_values = {key: [] for key in ("upperLimit", "noLimit", "fixed", "none")}
        for year_index, column in enumerate(range(3, 9)):
            bonus_values["yes"].append(value(bonus_sheet.cell(row, column).value))
            bonus_values["no"].append(value(bonus_sheet.cell(row + 8, column).value))
            for block, key in enumerate(commute_values):
                commute_values[key].append(value(commute_sheet.cell(row + 8 * block, column).value))
            if sum(bonus_values[key][year_index] for key in bonus_values) != sum(
                commute_values[key][year_index] for key in commute_values
            ):
                raise ValueError(f"bonus/commute denominator mismatch for {size_id} {YEARS[year_index]}")

        records.append(
            {
                "id": size_id,
                "name": name,
                "weekend": weekend_values,
                "bonus": bonus_values,
                "commute": commute_values,
            }
        )

    for year_index, year in enumerate(YEARS):
        for metric, keys in (
            ("weekend", ("total", "complete", "other", "none")),
            ("bonus", ("yes", "no")),
            ("commute", ("upperLimit", "noLimit", "fixed", "none")),
        ):
            for key in keys:
                expected = sum(record[metric][key][year_index] for record in records[1:])
                if records[0][metric][key][year_index] != expected:
                    raise ValueError(f"size total mismatch for {metric}.{key} {year}")

    hashes = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
    index = {
        "schemaVersion": 1,
        "asOf": "2026-08-02",
        "edition": "2025年度（令和7年度）",
        "years": YEARS,
        "sizeCount": len(SIZES),
        "recordCount": len(records),
        "employment": "パートタイムを除く常用",
        "sourceValueCount": len(SIZES) * len(YEARS) * 11,
        "publishedValueCount": len(SIZES) * len(YEARS) * 10,
        "conditionPairCount": len(SIZES) * len(YEARS) * 3,
        "weekendIdentityChecked": len(SIZES) * len(YEARS),
        "sizeTotalChecked": len(YEARS) * 10,
        "sharedDenominatorChecked": len(SIZES) * len(YEARS),
        "sources": [
            {"metric": key, "url": SOURCES[key], "sha256": hashes[key], "bytes": paths[key].stat().st_size}
            for key in ("weekend", "bonus", "commute")
        ],
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (output_directory / "conditions.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"hashes": hashes, "sizes": len(records), "years": YEARS}, ensure_ascii=False))


if __name__ == "__main__":
    main()
