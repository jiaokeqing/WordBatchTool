# Tauri 桌面壳 / Sidecar 脚手架

本项目的新桌面壳位于 `frontend/src-tauri/`。前端仍使用 `frontend/` 的 React/Vite，后端以 Python sidecar 方式运行 FastAPI。

## 结构

- `frontend/src-tauri/`：Tauri v2 桌面壳。
- `backend/sidecar.py`：本地 API sidecar 入口，只启动 FastAPI，不创建窗口。
- `scripts/build_sidecar.py`：用 PyInstaller 构建 sidecar，并复制到 Tauri 需要的 `src-tauri/binaries/`。
- `frontend/`：Vite 前端。打包时通过 `VITE_API_BASE=http://127.0.0.1:8765` 指向 sidecar。

## 构建前准备

每个平台需要在目标系统本机上构建：

- Windows / 华为 Windows：安装 Rust、Node.js、pnpm、Python、WPS 或 Office。
- 统信 UOS / Linux：安装 Rust、Node.js、pnpm、Python、LibreOffice、系统 WebKit 依赖。

## Sidecar 构建

在项目根目录运行：

```bash
python scripts/build_sidecar.py
```

脚本会生成：

```text
frontend/src-tauri/binaries/word-batch-sidecar-{target-triple}
```

Tauri v2 要求 sidecar 文件名带目标平台 triple，例如：

- `word-batch-sidecar-x86_64-pc-windows-msvc.exe`
- `word-batch-sidecar-x86_64-unknown-linux-gnu`
- `word-batch-sidecar-aarch64-unknown-linux-gnu`

如需指定：

```bash
python scripts/build_sidecar.py --target-triple x86_64-unknown-linux-gnu
```

## 开发运行

```bash
cd frontend
pnpm install
pnpm tauri:dev
```

开发模式下如果 sidecar 尚未生成，Tauri 窗口仍会启动，但接口不可用。可临时手动启动后端：

```bash
cd backend
python sidecar.py --host 127.0.0.1 --port 8765
```

## 打包

推荐使用项目脚本执行完整桌面打包流程：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target windows
```

如果 Python 已安装但当前终端没有识别，可显式传入 Python 路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target windows -PythonCommand "C:\Path\To\python.exe"
```

华为 Windows 电脑仍使用 Windows x64 构建目标：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target huawei-windows
```

华为统信 UOS / ARM64 设备需要在目标设备本机执行 Linux 构建流程，sidecar 目标为：

```bash
scripts/package_desktop.sh huawei-uos-arm64
```

如果 Python 命令不是 `python3`，可指定：

```bash
PYTHON_BIN=/path/to/python3 scripts/package_desktop.sh huawei-uos-arm64
```

也可以手动拆分执行：

```bash
python scripts/build_sidecar.py --target-triple aarch64-unknown-linux-gnu
cd frontend
pnpm tauri:build
```

手动拆分步骤如下：

```bash
python scripts/build_sidecar.py
cd frontend
pnpm tauri:build
```

## 后续待办

- Windows / 华为 Windows x64 已完成最新 Release 构建，产物见 `release/windows-x64/`、`release/huawei-windows-x64/` 和 `frontend/src-tauri/target/release/bundle/nsis/`。
- 在华为统信 UOS / ARM64 设备上执行 `python scripts/build_sidecar.py --target-triple aarch64-unknown-linux-gnu` 和 `pnpm tauri:build` 并记录产物。
- 将 pywebview 打包流程标记为旧版兼容路径。
