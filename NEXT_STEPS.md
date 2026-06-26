# 后续操作记录

当前开发分支：`codex/new-architecture-workbench`

## 已完成

- 重设计并实现工作台 UI：处理任务、模板库、任务记录、平台适配、设置。
- 移除服务器共享目录入口。
- 新增本地模板库 API 和 SQLite 表。
- 新增平台适配 API 和转换引擎检测。
- 抽象转换引擎：
  - Windows 优先 WPS / Office COM。
  - 统信 UOS / Linux 优先 LibreOffice headless。
  - Windows 在 Office/WPS 不可用且有 LibreOffice 时可降级。
- 新增 Tauri v2 桌面壳脚手架：`frontend/src-tauri/`。
- 新增 Python sidecar：`backend/sidecar.py`。
- 新增 sidecar 构建脚本：`scripts/build_sidecar.py`。

## 已验证

- 后端测试：`18 passed`，后续新增 health 后为 `19 passed`。
- 前端构建：`pnpm run build` 成功。
- `pnpm tauri info` 能识别 Tauri App 配置。
- 当前机器缺少 Rust/Cargo，因此尚未实际执行 `pnpm tauri:build`。
- 2026-06-26 当前机器复核：
  - `pnpm.cmd install --frozen-lockfile --store-dir ..\.npm-cache\pnpm-store` 已补齐前端依赖。
  - `pnpm.cmd run build` 成功。
  - `pnpm.cmd tauri info` 能识别 Tauri App 配置，但提示缺少 Rust/Cargo、rustup、Visual Studio Build Tools 的 MSVC/SDK 组件。
  - 当前 `python` / `python3` 指向 Windows Store 占位程序，未检测到可用 Python 解释器，因此暂不能构建 sidecar 或执行后端测试。
- 2026-06-26 已新增桌面打包脚本：`scripts/package_desktop.ps1`，用于 Windows / 华为 Windows 目标的前置检查、依赖安装、sidecar 构建和 Tauri 打包。
- 2026-06-26 已新增华为 UOS / Linux 打包脚本：`scripts/package_desktop.sh`，用于 `huawei-uos-arm64` 和 `linux-x64` 目标的前置检查、依赖安装、sidecar 构建和 Tauri 打包。
- 2026-06-26 当前 PowerShell 禁止直接执行 `.ps1`，需使用 `powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target windows`。
- 2026-06-26 当前机器 `pnpm.cmd tauri info` 已检测到 MSVC / Visual Studio Build Tools 可用；仍缺 Rust/Cargo/rustup，且 Python 入口不可用。
- 2026-06-26 再次复核：`frontend/src-tauri/target/release/bundle` 下未发现已生成安装包；Windows / 华为可执行文件尚未产出，阻塞项仍为 Python 入口不可用、Rust/Cargo/rustup 未安装。
- 2026-06-26 Rust 已安装但当前 Codex 会话 PATH 未刷新；`scripts/package_desktop.ps1` 已自动追加默认 Rust 路径 `%USERPROFILE%\.cargo\bin`，并支持 `-PythonCommand` 显式指定 Python 路径。
- 2026-06-26 Windows 打包成功：
  - NSIS 安装包：`frontend/src-tauri/target/release/bundle/nsis/格式通_1.0.0_x64-setup.exe`
  - Windows 绿色版：`release/windows-x64/格式通.exe` + `release/windows-x64/word-batch-sidecar.exe`
  - 华为 Windows x64 绿色版：`release/huawei-windows-x64/格式通.exe` + `release/huawei-windows-x64/word-batch-sidecar.exe`
  - 华为统信 UOS / ARM64 仍需在目标设备本机执行 `scripts/package_desktop.sh huawei-uos-arm64`。
- 2026-06-26 已完成格式通优化交付：
  - 任务记录列表和文件结果列表已增加高缩放下的横向滚动、最小列宽和省略显示。
  - Tauri 主进程和 Python sidecar 已切换为 Windows GUI / 无控制台窗口模式。
  - 软件名称、窗口标题、本地 API 信息和前端品牌已统一为“格式通”。
  - 已新增现代科技感 SVG logo 与 Tauri `icon.ico`。
  - 已输出 Markdown / PDF 安装使用手册：`docs/格式通安装使用手册.md`、`docs/格式通安装使用手册.pdf`。
  - 已用最新代码重新生成 Windows / 华为 Windows 绿色版和 NSIS 安装包。

## 换电脑后的准备

1. 克隆仓库并切换分支：

   ```bash
   git clone https://github.com/jiaokeqing/WordBatchTool.git
   cd WordBatchTool
   git switch codex/new-architecture-workbench
   ```

2. 安装基础工具：

   - Node.js 18+ 或更新版本。
   - pnpm。
   - Python 3.12。
   - Rust / Cargo / rustup。
   - Windows：安装 WPS 或 Microsoft Office。
   - 统信 UOS / Linux：安装 LibreOffice。

3. 安装依赖：

   ```bash
   cd backend
   python -m pip install -r requirements.txt

   cd ../frontend
   pnpm install
   ```

## 下一步优先级

1. 在新电脑安装 Rust/Cargo 后运行：

   ```bash
   cd frontend
   pnpm tauri info
   ```

2. 构建 Python sidecar：

   ```bash
   python scripts/build_sidecar.py
   ```

   如在统信 UOS / ARM64 华为设备上构建，可显式指定：

   ```bash
   python scripts/build_sidecar.py --target-triple aarch64-unknown-linux-gnu
   ```

3. 运行 Tauri 开发模式：

   ```bash
   cd frontend
   pnpm tauri:dev
   ```

4. 执行桌面打包：

   ```bash
   cd frontend
   pnpm tauri:build
   ```

   Windows / 华为 Windows 也可以在项目根目录执行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target windows
   ```

   华为 Windows 设备可执行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\package_desktop.ps1 -Target huawei-windows
   ```

   华为统信 UOS / ARM64 设备需在目标设备本机执行：

   ```bash
   scripts/package_desktop.sh huawei-uos-arm64
   ```

5. 用真实文件做验收：

   - `.docx` 排版输出 DOCX。
   - `.docx` 排版输出 PDF。
   - `.doc` 转 `.docx`。
   - 批量文件夹导入。
   - 模板新建、复制、设为默认、删除。
   - GitHub 更新检查离线/联网状态。

## 待办

- Tauri 内已接入原生保存 ZIP 对话框入口；Release 构建已通过，仍建议用真实任务实机验证保存对话框。
- 为 Windows、统信 UOS、华为电脑分别补构建说明和验收记录。
- 在统信 UOS 实机验证 LibreOffice headless 转换质量。
- 考虑将旧 pywebview 打包流程标记为兼容路径或移除。
