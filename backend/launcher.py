import socket
import threading
import time

import uvicorn
import webview

from app.main import app


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


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
    webview.create_window("批量 Word 格式处理", URL, width=1280, height=860, min_size=(980, 700))
    webview.start()


if __name__ == "__main__":
    main()
