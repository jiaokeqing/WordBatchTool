import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ConversionError(RuntimeError):
    pass


EngineStatus = Literal["recommended", "available", "missing", "unsupported"]


@dataclass(frozen=True)
class EngineInfo:
    id: str
    name: str
    status: EngineStatus
    description: str
    executable: str | None = None


def detect_engines() -> list[EngineInfo]:
    system = platform.system()
    libreoffice = _libreoffice_executable()
    return [
        EngineInfo(
            id="auto",
            name="自动选择",
            status="recommended",
            description="按系统检测可用引擎，优先使用效果最稳定的方案。",
        ),
        EngineInfo(
            id="office",
            name="WPS / Office",
            status="available" if system == "Windows" else "unsupported",
            description="Windows 桌面环境下用于 .doc 转换和 PDF 导出。",
        ),
        EngineInfo(
            id="libreoffice",
            name="LibreOffice Headless",
            status="available" if libreoffice else "missing",
            description="跨平台备用引擎，适用于统信 UOS 和 Linux 环境。",
            executable=libreoffice,
        ),
    ]


def recommended_engine_id() -> str:
    if platform.system() == "Windows":
        return "office"
    return "libreoffice"


def convert_doc_to_docx(input_path: Path, output_path: Path) -> None:
    if input_path.suffix.lower() == ".docx":
        shutil.copy2(input_path, output_path)
        return
    if platform.system() == "Windows":
        try:
            _convert_with_word_com(input_path, output_path, target_format=16)
            return
        except ConversionError:
            if not _libreoffice_executable():
                raise
    _convert_with_libreoffice(input_path, output_path, "docx")


def export_pdf(input_path: Path, output_path: Path) -> None:
    if platform.system() == "Windows":
        try:
            _convert_with_word_com(input_path, output_path, target_format=17)
            return
        except ConversionError:
            if not _libreoffice_executable():
                raise
    _convert_with_libreoffice(input_path, output_path, "pdf")


def _convert_with_word_com(input_path: Path, output_path: Path, target_format: int) -> None:
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise ConversionError("缺少 pywin32，无法调用 WPS/Office 自动化。") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    app = None
    document = None
    pythoncom.CoInitialize()
    try:
        last_error = None
        for prog_id in ("Word.Application", "KWPS.Application", "WPS.Application"):
            try:
                app = win32com.client.DispatchEx(prog_id)
                break
            except Exception as exc:  # pragma: no cover - requires desktop COM
                last_error = exc

        if app is None:
            raise ConversionError(
                "未找到可用的 Microsoft Word 或 WPS Office 自动化组件。"
                "请确认已安装桌面版 Office/WPS，并能正常打开 Word 文档。"
            ) from last_error

        app.Visible = False
        document = app.Documents.Open(str(input_path.resolve()))
        document.SaveAs(str(output_path.resolve()), FileFormat=target_format)
    except Exception as exc:  # pragma: no cover - requires Windows desktop automation
        if isinstance(exc, ConversionError):
            raise
        raise ConversionError(str(exc)) from exc
    finally:
        if document is not None:
            document.Close(False)
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()


def _convert_with_libreoffice(input_path: Path, output_path: Path, target_format: str) -> None:
    executable = _libreoffice_executable()
    if not executable:
        raise ConversionError("未找到 LibreOffice。请安装 LibreOffice 后重试，或在 Windows 上安装 WPS/Office。")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "--headless",
        "--convert-to",
        target_format,
        "--outdir",
        str(output_path.parent.resolve()),
        str(input_path.resolve()),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ConversionError("LibreOffice 转换超时。") from exc
    except OSError as exc:
        raise ConversionError(f"无法启动 LibreOffice：{exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ConversionError(f"LibreOffice 转换失败：{detail or '未知错误'}")

    produced = output_path.parent / f"{input_path.stem}.{target_format}"
    if not produced.exists():
        matches = sorted(output_path.parent.glob(f"{input_path.stem}.*"))
        produced = matches[0] if matches else produced
    if not produced.exists():
        raise ConversionError("LibreOffice 未生成预期的输出文件。")
    if produced.resolve() != output_path.resolve():
        if output_path.exists():
            output_path.unlink()
        produced.replace(output_path)


def _libreoffice_executable() -> str | None:
    for name in ("soffice", "libreoffice"):
        executable = shutil.which(name)
        if executable:
            return executable
    return None
