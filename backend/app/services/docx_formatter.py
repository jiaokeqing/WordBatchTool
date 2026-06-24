from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from ..schemas import BuiltInTemplate, TemplatePreview


def apply_builtin_template(input_path: Path, output_path: Path, template: BuiltInTemplate) -> None:
    document = Document(input_path)
    remove_empty_paragraphs(document)
    for section in document.sections:
        section.top_margin = Cm(template.margin_top_cm)
        section.bottom_margin = Cm(template.margin_bottom_cm)
        section.left_margin = Cm(template.margin_left_cm)
        section.right_margin = Cm(template.margin_right_cm)

    for index, paragraph in enumerate(document.paragraphs):
        level = detect_paragraph_level(paragraph.text, index)
        font_name, font_size = font_for_level(template, level)
        paragraph_format = paragraph.paragraph_format
        paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        paragraph_format.line_spacing = Pt(template.line_spacing_pt)
        paragraph_format.space_before = Pt(template.space_before_pt)
        paragraph_format.space_after = Pt(template.space_after_pt)
        paragraph_format.left_indent = Pt(0)
        paragraph_format.right_indent = Pt(0)
        paragraph_format.first_line_indent = Pt(font_size * template.first_line_indent_chars) if level == "body" else Pt(0)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == "title" else WD_ALIGN_PARAGRAPH.LEFT

        for run in paragraph.runs:
            if template.normalize_spacing or template.normalize_parentheses:
                run.text = normalize_text(run.text, template)
            apply_run_font(run, font_name, template.latin_font, font_size)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def apply_sample_template(input_path: Path, output_path: Path, sample_path: Path) -> None:
    sample = Document(sample_path)
    builtin = BuiltInTemplate()
    for paragraph in sample.paragraphs:
        if not paragraph.runs:
            continue
        font = paragraph.runs[0].font
        if font.name:
            builtin.body_font = font.name
        if font.size:
            builtin.body_size = int(font.size.pt)
        break
    apply_builtin_template(input_path, output_path, builtin)


def preview_template(sample_path: Path) -> TemplatePreview:
    document = Document(sample_path)
    styles = sorted({paragraph.style.name for paragraph in document.paragraphs if paragraph.style})
    return TemplatePreview(styles=styles[:50], paragraphs=len(document.paragraphs), tables=len(document.tables))


def remove_empty_paragraphs(document: Document) -> None:
    for paragraph in list(document.paragraphs):
        if paragraph.text.strip():
            continue
        element = paragraph._element
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)


def detect_paragraph_level(text: str, index: int) -> str:
    stripped = text.strip()
    if not stripped:
        return "body"
    if is_salutation(stripped):
        return "salutation"
    if index == 0 and is_probable_title(stripped):
        return "title"
    if re.match(r"^[一二三四五六七八九十]+、", stripped):
        return "heading1"
    if re.match(r"^（[一二三四五六七八九十]+）", stripped) or re.match(r"^\([一二三四五六七八九十]+\)", stripped):
        return "heading2"
    if re.match(r"^\d+[\.．、]", stripped):
        return "heading3"
    return "body"


def is_salutation(text: str) -> bool:
    return text.endswith(("：", ":"))


def is_probable_title(text: str) -> bool:
    if re.match(r"^[一二三四五六七八九十]+、", text):
        return False
    if re.match(r"^（[一二三四五六七八九十]+）", text) or re.match(r"^\([一二三四五六七八九十]+\)", text):
        return False
    if re.match(r"^\d+[\.．、]", text):
        return False
    return not is_salutation(text)


def font_for_level(template: BuiltInTemplate, level: str) -> tuple[str, int]:
    if level == "title":
        return template.title_font, template.title_size
    if level == "heading1":
        return template.heading_font, template.heading_size
    if level == "heading2":
        return template.second_heading_font, template.heading_size
    if level == "heading3":
        return template.third_heading_font, template.heading_size
    return template.body_font, template.body_size


def apply_run_font(run, east_asia_font: str, latin_font: str, size: int) -> None:
    run.font.name = latin_font
    run.font.size = Pt(size)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), east_asia_font)
    r_fonts.set(qn("w:ascii"), latin_font)
    r_fonts.set(qn("w:hAnsi"), latin_font)


def normalize_text(text: str, template: BuiltInTemplate) -> str:
    value = text
    if template.normalize_spacing:
        value = re.sub(r"[ \t\u3000]+", " ", value).strip()
    if template.normalize_parentheses:
        value = re.sub(r"\(([一二三四五六七八九十]+)\)", r"（\1）", value)
    return value
