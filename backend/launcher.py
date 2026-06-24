import shutil
import socket
import threading
import time
from pathlib import Path

import uvicorn
import webview

from app import repository
from app.main import app


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


class Api:
    def save_zip(self, job_id: str) -> dict:
        job = repository.get_job(job_id)
        if not job or not job["zip_path"]:
            return {"ok": False, "message": "结果包尚未生成。"}

        source = Path(job["zip_path"])
        if not source.exists():
            return {"ok": False, "message": "结果包已不存在。"}

        destination = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=f"{job_id}.zip",
            file_types=("ZIP 文件 (*.zip)",),
        )
        if not destination:
            return {"ok": False, "cancelled": True, "message": "已取消下载。"}

        target = Path(destination)
        if target.suffix.lower() != ".zip":
            target = target.with_suffix(".zip")
        shutil.copy2(source, target)
        return {"ok": True, "path": str(target)}


def wait_for_server() -> None:
    for _ in range(60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex((HOST, PORT)) == 0:
                return
        time.sleep(0.25)
    raise RuntimeError("服务启动超时，请检查端口 8000 是否被占用。")


def run_server() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def main() -> None:
    threading.Thread(target=run_server, daemon=True).start()
    wait_for_server()
    webview.create_window("批量 Word 格式处理", URL, width=1280, height=860, min_size=(980, 700), js_api=Api())
    webview.start()


if __name__ == "__main__":
    main()
