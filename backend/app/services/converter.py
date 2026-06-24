import platform
import shutil
from pathlib import Path


class ConversionError(RuntimeError):
    pass


def convert_doc_to_docx(input_path: Path, output_path: Path) -> None:
    if input_path.suffix.lower() == ".docx":
        shutil.copy2(input_path, output_path)
        return
    if platform.system() != "Windows":
        raise ConversionError("DOC 转 DOCX 需要 Windows + WPS/Office 自动化环境。")
    _convert_with_word_com(input_path, output_path, target_format=16)


def export_pdf(input_path: Path, output_path: Path) -> None:
    if platform.system() != "Windows":
        raise ConversionError("PDF 导出需要 Windows + WPS/Office 自动化环境。")
    _convert_with_word_com(input_path, output_path, target_format=17)


def _convert_with_word_com(input_path: Path, output_path: Path, target_format: int) -> None:
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise ConversionError("缺少 pywin32，无法调用 WPS/Office 自动化。") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    app = win32com.client.Dispatch("Word.Application")
    app.Visible = False
    document = None
    try:
        document = app.Documents.Open(str(input_path.resolve()))
        document.SaveAs(str(output_path.resolve()), FileFormat=target_format)
    except Exception as exc:  # pragma: no cover - requires Windows desktop automation
        raise ConversionError(str(exc)) from exc
    finally:
        if document is not None:
            document.Close(False)
        app.Quit()
