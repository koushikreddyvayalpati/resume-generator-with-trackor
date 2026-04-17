import os
import socket
import threading
import time
import webbrowser


def _find_port(start: int = 5123) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No local port available for Resume Tool")


def _open_browser(url: str) -> None:
    time.sleep(1.0)
    webbrowser.open(url)


def main() -> None:
    os.environ.setdefault("RESUME_DESKTOP_MODE", "1")
    os.environ.setdefault("FLASK_ENV", "production")

    from app import app

    port = int(os.getenv("RESUME_TOOL_PORT") or _find_port())
    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    try:
        from waitress import serve

        serve(app, host="127.0.0.1", port=port, threads=8)
    except ImportError:
        app.run(debug=False, host="127.0.0.1", port=port, threaded=True)


if __name__ == "__main__":
    main()
