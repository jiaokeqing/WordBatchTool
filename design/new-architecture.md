# 客户端工作台新架构草案

## 目标

- 去掉服务器共享目录入口，所有处理都从本机文件或文件夹选择开始。
- 面向 Windows、华为电脑、统信 UOS 做桌面客户端适配。
- 核心功能离线可用：模板库、批量排版、任务记录、本地导出、版本信息。
- GitHub 只用于联网时提示新版本，不作为运行依赖。

## 推荐架构

- 桌面壳：Tauri，脚手架位于 `frontend/src-tauri/`。
- 前端：React + Vite + 自定义 CSS tokens。
- 本地处理服务：Python sidecar/worker，入口为 `backend/sidecar.py`。
- 本地存储：SQLite + 文件系统任务目录。
- 打包方式：每个平台在目标系统上分别构建。

## 平台策略

- Windows：优先使用 WPS / Microsoft Office 自动化完成 `.doc` 转 `.docx` 和 PDF 导出。
- 华为电脑：按实际操作系统分流；Windows 版走 Windows 策略，Linux/统信环境走 Linux 策略。
- 统信 UOS / Linux：优先使用 LibreOffice headless 作为转换引擎。

## 转换引擎抽象

定义统一的文档转换接口：

- `detect()`：检测当前系统可用引擎和版本。
- `convert_doc_to_docx(source, target)`：转换旧版 `.doc`。
- `export_pdf(source, target)`：导出 PDF。
- `health()`：返回 UI 可展示的能力状态。

引擎优先级：

1. Windows WPS / Office 自动化。
2. LibreOffice headless。
3. 只输出格式化 DOCX，并提示 PDF 或 `.doc` 转换不可用。

## 新版本 UI

设计图位于本目录：

- `process.png`：处理任务页，已移除服务器共享目录。
- `templates.png`：模板库。
- `history.png`：任务记录。
- `settings.png`：设置。
- `platforms.png`：平台适配与转换引擎检测。

## 清理说明

上一轮被中断的半成品研发改动已从代码目录恢复，当前新分支只保留设计稿和新架构说明，后续实现应基于本架构重新拆分任务。

## Tauri 脚手架

- `frontend/src-tauri/tauri.conf.json` 配置窗口、Vite 构建和 sidecar。
- `frontend/src-tauri/src/lib.rs` 在应用启动时拉起 `word-batch-sidecar`。
- `scripts/build_sidecar.py` 用 PyInstaller 生成带 target triple 后缀的 sidecar 二进制。
- 详细步骤见根目录 `TAURI_DESKTOP.md`。
