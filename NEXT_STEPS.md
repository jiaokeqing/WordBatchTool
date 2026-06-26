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

5. 用真实文件做验收：

   - `.docx` 排版输出 DOCX。
   - `.docx` 排版输出 PDF。
   - `.doc` 转 `.docx`。
   - 批量文件夹导入。
   - 模板新建、复制、设为默认、删除。
   - GitHub 更新检查离线/联网状态。

## 待办

- Tauri 内实现原生保存 ZIP 对话框，替代浏览器下载。
- 为 Windows、统信 UOS、华为电脑分别补构建说明和验收记录。
- 在统信 UOS 实机验证 LibreOffice headless 转换质量。
- 考虑将旧 pywebview 打包流程标记为兼容路径或移除。
