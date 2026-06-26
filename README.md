# 批量 Word 格式处理 Web 程序

一个用于办公室局域网的批量 Word 处理工具。支持上传 Word 文件或从服务器共享目录导入，批量统一排版，导出 PDF，并生成 ZIP 结果包下载。

## 技术栈

- Backend: FastAPI, SQLite, python-docx
- Frontend: React, Vite
- 转换引擎: Windows 上优先通过 WPS/Office COM 自动化导出 PDF；非 Windows 环境会记录清晰失败原因

## 快速启动

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

前端开发服务默认访问 `http://localhost:5173`，后端 API 默认访问 `http://localhost:8000`。
如果电脑上存在较旧的 Node.js，请优先使用 Node 18+。

## 功能边界

- 每批最多 100 个 `.doc` / `.docx` 文件。
- 结果以 ZIP 包输出，不覆盖原文件。
- 上传、中间文件和结果文件默认保留 24 小时。
- 第一版不提供登录鉴权，请仅部署在可信局域网。
- `.doc` 转 `.docx` 和 PDF 导出依赖 Windows 桌面环境中的 WPS/Office 自动化能力。

## 运行测试

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Windows 打包 EXE

在 Windows 电脑上安装 Python 3.12、Node.js 18+ 和 WPS/Office 后，在项目根目录运行：

```powershell
.\build_windows.ps1
```

生成文件位于 `backend\dist\WordBatchTool.exe`。双击后会打开 Windows 客户端窗口，前端页面嵌入在窗口内，后端服务在本机后台运行。

运行数据会保存到 exe 同目录的 `data` 文件夹中。PDF 导出和 `.doc` 转换仍需要 Windows 上安装可自动化调用的 WPS/Office。

## 新版 Tauri 桌面壳

新版跨平台桌面壳脚手架位于 `frontend/src-tauri`，Python API sidecar 入口为 `backend/sidecar.py`。

详细说明见 `TAURI_DESKTOP.md`。当前目标是适配 Windows、华为电脑和统信 UOS；Windows 优先使用 WPS/Office，统信 UOS/Linux 优先使用 LibreOffice headless。
