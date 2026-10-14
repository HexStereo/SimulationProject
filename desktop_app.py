"""
desktop_app.py - Standalone Desktop Launcher
=============================================
Starts the local Python simulation backend and opens it inside a dedicated
native desktop application window (MS Edge App Mode) with custom dimensions,
clean styling, and desktop shortcut integration.
"""

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import http.server

from desktop_server import DesktopRequestHandler


def find_free_port(start_port: int = 5055) -> int:
    """Finds an open TCP port on 127.0.0.1."""
    port = start_port
    while port < 6000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1
    return start_port


def start_server_in_thread(port: int):
    """Starts the ThreadingHTTPServer in a background daemon thread."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DesktopRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def find_edge_binary() -> str | None:
    """Locates Microsoft Edge binary on Windows."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def main():
    print("=" * 70)
    print("6 HANELİ KOD İSTATİSTİKSEL ANOMALİ SİMÜLATÖRÜ — MASAÜSTÜ UYGULAMASI")
    print("=" * 70)

    port = find_free_port(5055)
    app_url = f"http://127.0.0.1:{port}"
    print(f"[*] Yerel simülasyon sunucusu başlatılıyor: {app_url}")

    # Start server
    start_server_in_thread(port)
    time.sleep(0.3)

    edge_bin = find_edge_binary()
    if edge_bin and sys.platform.startswith("win"):
        print(f"[*] Masaüstü uygulama penceresi açılıyor (Edge App Mode)...")
        # Launch standalone window without browser chrome
        cmd = [
            edge_bin,
            f"--app={app_url}",
            "--window-size=1400,900",
            "--window-position=center",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        try:
            proc = subprocess.Popen(cmd)
            print("[OK] Masaüstü penceresi aktif. Çıkış yapmak için pencereyi kapatınız.")
            proc.wait()
            sys.exit(0)
        except Exception as e:
            print(f"[!] Edge app modu başlatılamadı ({e}), varsayılan tarayıcı açılıyor...")
            webbrowser.open(app_url)
    else:
        print(f"[*] Tarayıcı arayüzü açılıyor...")
        webbrowser.open(app_url)

    # Keep server alive if opened in standard browser
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Masaüstü uygulaması kapatıldı.")
        sys.exit(0)


if __name__ == "__main__":
    main()
