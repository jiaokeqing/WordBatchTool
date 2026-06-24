import socket
import threading
import time
import webbrowser

import uvicorn

from app.main import app


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def wait_and_open_browser() -> None:
    for _ in range(60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex((HOST, PORT)) == 0:
                webbrowser.open(URL)
                return
        time.sleep(0.25)


def main() -> None:
    threading.Thread(target=wait_and_open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
