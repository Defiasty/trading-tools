import os
import socket
import threading

import webview
from waitress import serve

from app import app


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def run_server(port):
    serve(app, host="127.0.0.1", port=port, threads=6, clear_untrusted_proxy_headers=True)


if __name__ == "__main__":
    port = free_port()
    server = threading.Thread(target=run_server, args=(port,), daemon=True)
    server.start()
    icon_path = os.path.join(app.root_path, "static", "img", "app-icon.ico")
    webview.create_window(
        "Trading Tracker",
        f"http://127.0.0.1:{port}",
        width=1440,
        height=920,
        min_size=(980, 680),
        background_color="#050716",
    )
    webview.start(icon=icon_path if os.path.exists(icon_path) else None)
