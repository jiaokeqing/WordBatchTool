import shutil
from pathlib import Path

from .. import repository
from ..schemas import TemplateConfig
from .converter import ConversionError, convert_doc_to_docx, export_pdf
from .docx_formatter import apply_builtin_template, apply_sample_template
from .zipper import create_result_zip, unique_relative_path, write_failure_report


def process_job(job_id: str, job_dir: Path) -> None:
    job = repository.get_job(job_id)
    if not job:
        return
    repository.update_job_status(job_id, "running")
    template_config = repository.parse_template_config(job)
    files = repository.get_job_files(job_id)
    outputs: list[tuple[Path, Path]] = []
    used_paths: set[str] = set()

    for item in files:
        try:
            output = process_file(job_dir, item, template_config, bool(job["export_pdf"]))
            relative = unique_relative_path(Path(item["relative_path"]).with_suffix(output.suffix), used_paths)
            outputs.append((output, relative))
            repository.update_file_result(item["id"], "succeeded", "处理完成", str(output))
        except Exception as exc:
            repository.update_file_result(item["id"], "failed", str(exc), None)
        repository.refresh_job_counts(job_id)

    failures = [item for item in repository.get_job_files(job_id) if item["status"] == "failed"]
    failure_report = job_dir / "failures.csv"
    write_failure_report(failure_report, failures)
    zip_path = job_dir / "result.zip"
    create_result_zip(zip_path, outputs, failure_report)
    repository.refresh_job_counts(job_id)
    final = "succeeded"
    if failures and len(failures) == len(files):
        final = "failed"
    elif failures:
        final = "partial_failed"
    repository.update_job_status(job_id, final, str(zip_path))


def process_file(job_dir: Path, item: dict, template_config: TemplateConfig, export_as_pdf: bool) -> Path:
    source = job_dir / "uploads" / item["relative_path"]
    work_dir = job_dir / "work" / item["id"]
    work_dir.mkdir(parents=True, exist_ok=True)
    docx_path = work_dir / f"{source.stem}.docx"
    formatted_path = work_dir / f"{source.stem}.formatted.docx"

    if source.suffix.lower() not in {".doc", ".docx"}:
        raise ValueError("只支持 .doc 和 .docx 文件。")

    if source.suffix.lower() == ".doc":
        convert_doc_to_docx(source, docx_path)
    else:
        shutil.copy2(source, docx_path)

    if template_config.mode == "sample" and template_config.sample_template_filename:
        sample_path = job_dir / template_config.sample_template_filename
        apply_sample_template(docx_path, formatted_path, sample_path)
    else:
        apply_builtin_template(docx_path, formatted_path, template_config.builtin)

    if not export_as_pdf:
        return formatted_path

    pdf_path = work_dir / f"{source.stem}.pdf"
    try:
        export_pdf(formatted_path, pdf_path)
    except ConversionError:
        raise
    return pdf_path
