from __future__ import annotations

import csv
import zipfile
from pathlib import Path


def unique_relative_path(path: Path, used: set[str]) -> Path:
    candidate = path
    index = 1
    while str(candidate) in used:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        index += 1
    used.add(str(candidate))
    return candidate


def write_failure_report(path: Path, failures: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["文件", "状态", "错误"])
        for item in failures:
            writer.writerow([item["relative_path"], item["status"], item["message"]])


def create_result_zip(zip_path: Path, output_files: list[tuple[Path, Path]], failure_report: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, relative in output_files:
            if source.exists():
                archive.write(source, relative.as_posix())
        if failure_report.exists():
            archive.write(failure_report, "失败清单.csv")
