from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import converter
from app.services.converter import ConversionError, convert_doc_to_docx, detect_engines, export_pdf, recommended_engine_id


def test_convert_docx_copies_without_engine(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    output = tmp_path / "output.docx"
    source.write_text("docx", encoding="utf-8")

    convert_doc_to_docx(source, output)

    assert output.read_text(encoding="utf-8") == "docx"


def test_liberoffice_conversion_moves_generated_file(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.doc"
    output = tmp_path / "custom.docx"
    source.write_text("doc", encoding="utf-8")
    monkeypatch.setattr(converter.platform, "system", lambda: "Linux")
    monkeypatch.setattr(converter, "_libreoffice_executable", lambda: "/usr/bin/soffice")

    def fake_run(command, check, capture_output, text, timeout):
        assert command[:3] == ["/usr/bin/soffice", "--headless", "--convert-to"]
        (tmp_path / "source.docx").write_text("converted", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(converter.subprocess, "run", fake_run)

    convert_doc_to_docx(source, output)

    assert output.read_text(encoding="utf-8") == "converted"


def test_export_pdf_requires_available_engine(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.docx"
    output = tmp_path / "source.pdf"
    source.write_text("docx", encoding="utf-8")
    monkeypatch.setattr(converter.platform, "system", lambda: "Linux")
    monkeypatch.setattr(converter, "_libreoffice_executable", lambda: None)

    with pytest.raises(ConversionError, match="未找到 LibreOffice"):
        export_pdf(source, output)


def test_detect_engines_reports_liberoffice(monkeypatch) -> None:
    monkeypatch.setattr(converter.platform, "system", lambda: "Linux")
    monkeypatch.setattr(converter, "_libreoffice_executable", lambda: "/usr/bin/soffice")

    engines = {engine.id: engine for engine in detect_engines()}

    assert engines["office"].status == "unsupported"
    assert engines["libreoffice"].status == "available"
    assert recommended_engine_id() == "libreoffice"
