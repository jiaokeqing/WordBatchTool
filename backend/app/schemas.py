from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BuiltInTemplate(BaseModel):
    preset: str = "custom"
    title_font: str = "方正小标宋_GBK"
    title_size: int = Field(default=22, ge=8, le=48)
    body_font: str = "仿宋_GB2312"
    body_size: int = Field(default=16, ge=8, le=36)
    heading_font: str = "黑体"
    heading_size: int = Field(default=16, ge=8, le=48)
    second_heading_font: str = "楷体_GB2312"
    third_heading_font: str = "仿宋_GB2312"
    latin_font: str = "Times New Roman"
    line_spacing_pt: float = Field(default=28, ge=12, le=60)
    space_before_pt: int = Field(default=0, ge=0, le=48)
    space_after_pt: int = Field(default=0, ge=0, le=48)
    first_line_indent_chars: int = Field(default=2, ge=0, le=8)
    margin_top_cm: float = Field(default=3.7, ge=1.0, le=5.0)
    margin_bottom_cm: float = Field(default=3.5, ge=1.0, le=5.0)
    margin_left_cm: float = Field(default=2.8, ge=1.0, le=5.0)
    margin_right_cm: float = Field(default=2.6, ge=1.0, le=5.0)
    normalize_spacing: bool = True
    normalize_parentheses: bool = True


class TemplateConfig(BaseModel):
    mode: str = "builtin"
    builtin: BuiltInTemplate = Field(default_factory=BuiltInTemplate)
    sample_template_filename: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    config: TemplateConfig = Field(default_factory=TemplateConfig)


class TemplateUpdate(TemplateCreate):
    pass


class TemplateLibraryItem(BaseModel):
    id: str
    name: str
    description: str
    config: TemplateConfig
    is_builtin: bool
    is_default: bool
    created_at: str
    updated_at: str


class AppInfo(BaseModel):
    name: str
    version: str
    mode: str
    data_dir: str
    default_open_dir: str
    max_files_per_job: int
    retention_hours: int
    worker_count: int
    github_repo: str


class AppSettingsUpdate(BaseModel):
    default_open_dir: str = Field(default="", max_length=500)
    max_files_per_job: int = Field(default=100, ge=1, le=500)
    retention_hours: int = Field(default=24, ge=1, le=720)
    github_repo: str = Field(default="", max_length=200)


class UpdateCheck(BaseModel):
    ok: bool
    status: str
    current_version: str
    latest_version: Optional[str] = None
    release_url: Optional[str] = None
    message: str


class PlatformEngine(BaseModel):
    id: str
    name: str
    status: str
    description: str


class PlatformInfo(BaseModel):
    os: str
    machine: str
    platform_label: str
    engines: list[PlatformEngine]
    recommended_engine: str
    offline_ready: bool
    message: str


class JobSummary(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str
    expires_at: str
    total_files: int
    succeeded_files: int
    failed_files: int
    export_pdf: bool


class JobFileResult(BaseModel):
    id: str
    original_name: str
    relative_path: str
    status: str
    message: str
    output_path: Optional[str]


class JobDetail(JobSummary):
    files: list[JobFileResult]
    download_ready: bool


class TemplatePreview(BaseModel):
    styles: list[str]
    paragraphs: int
    tables: int
