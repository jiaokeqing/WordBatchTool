# Windows 客户端 EXE 打包说明

目标产物是一个 Windows 桌面客户端：

- 一个 `WordBatchTool.exe`
- 前端 React 页面嵌入在客户端窗口中
- 后端 FastAPI 服务在本机后台启动
- 运行数据保存在 exe 同目录的 `data` 文件夹

## 环境要求

- Windows 10/11
- Python 3.12
- Node.js 18+
- WPS Office 或 Microsoft Office，用于 `.doc` 转换和 PDF 导出

## 打包命令

在项目根目录打开 PowerShell：

```powershell
.\build_windows.ps1
```

打包完成后生成：

```text
backend\dist\WordBatchTool.exe
```

## 使用方式

双击 `WordBatchTool.exe`，程序会打开一个 Windows 客户端窗口。窗口内就是批量 Word 处理页面。

如果端口 `8000` 被占用，程序会启动失败；关闭占用该端口的软件后重新打开即可。
