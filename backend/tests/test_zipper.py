import zipfile
from pathlib import Path

from app.services.zipper import create_result_zip, unique_relative_path, write_failure_report


def test_unique_relative_path_adds_suffix() -> None:
    used = set()

    assert unique_relative_path(Path("a.docx"), used) == Path("a.docx")
    assert unique_relative_path(Path("a.docx"), used) == Path("a_1.docx")


def test_create_result_zip_with_failure_report(tmp_path: Path) -> None:
    output = tmp_path / "done.pdf"
    output.write_text("pdf", encoding="utf-8")
    report = tmp_path / "failures.csv"
    write_failure_report(report, [{"relative_path": "bad.doc", "status": "failed", "message": "broken"}])
    zip_path = tmp_path / "result.zip"

    create_result_zip(zip_path, [(output, Path("done.pdf"))], report)

    with zipfile.ZipFile(zip_path) as archive:
        assert sorted(archive.namelist()) == ["done.pdf", "失败清单.csv"]
