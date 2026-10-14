"""
desktop_app.py - Standalone Desktop Launcher
=============================================
Starts the local Python simulation backend and opens it inside a dedicated
native desktop application window (MS Edge App Mode) with custom dimensions,
clean styling, and desktop shortcut integration.
"""

import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser

from desktop_server import (
    DesktopRequestHandler,
    PROJECT_ROOT,
    SERVER_ACTIVITY,
    SIM_STATE
)


def find_free_port(start_port: int = 5055) -> int:
    """Finds an open TCP port on 127.0.0.1."""
    port = start_port
    while port < 6000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1
    return start_port


def wait_for_server(url: str, timeout: float = 4.0) -> bool:
    """Polls the local server until it responds with HTTP 200."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


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
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("6 HANELİ KOD İSTATİSTİKSEL ANOMALİ SİMÜLATÖRÜ — MASAÜSTÜ UYGULAMASI")
    print("=" * 70)

    # Change working directory to project root
    os.chdir(PROJECT_ROOT)

    port = find_free_port(5055)
    app_url = f"http://127.0.0.1:{port}"
    print(f"[*] Yerel simülasyon sunucusu başlatılıyor: {app_url}")

    # Start server
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DesktopRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Wait until server is definitely responding
    if not wait_for_server(app_url, timeout=4.0):
        print(f"[UYARI] Sunucu yanıtı gecikti, arayüz yine de açılıyor...")

    print(f"[OK] Simülasyon sunucusu aktif: {app_url}")

    edge_bin = find_edge_binary()

    if edge_bin and sys.platform.startswith("win"):
        print(f"[*] Masaüstü uygulama penceresi açılıyor (Edge App Mode)...")
        profile_dir = os.path.join(tempfile.gettempdir(), "sim_app_edge_profile")
        os.makedirs(profile_dir, exist_ok=True)

        cmd = [
            edge_bin,
            f"--app={app_url}",
            f"--user-data-dir={profile_dir}",
            "--window-size=1400,900",
            "--window-position=center",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        try:
            subprocess.Popen(cmd)
            print("[OK] Masaüstü penceresi başarıyla açıldı.")
        except Exception as e:
            print(f"[!] Edge app modu açılamadı ({e}), varsayılan tarayıcı kullanılıyor...")
            webbrowser.open(app_url)
    else:
        print(f"[*] Varsayılan tarayıcı arayüzü açılıyor...")
        webbrowser.open(app_url)

    print("[*] Uygulama çalışıyor. Kapatmak için pencereyi kapatınız veya bu konsolda Ctrl+C yapınız.")

    # Watchdog monitor: keeps server alive and cleanly terminates on window close or timeout
    def watchdog_monitor():
        # Allow 45 seconds for user/browser to make first connection
        t0 = time.time()
        while time.time() - t0 < 45:
            if SERVER_ACTIVITY.has_client:
                break
            time.sleep(0.5)

        # Loop checking for shutdown request or heartbeats
        while True:
            time.sleep(2)
            if SERVER_ACTIVITY.shutdown_requested:
                print("\n[*] Arayüz kapatma sinyali alındı. Sunucu sonlandırılıyor...")
                server.shutdown()
                break
            # If client was connected before, but no heartbeat for > 25 seconds (and not actively running a sim)
            if SERVER_ACTIVITY.has_client and not SIM_STATE.is_running:
                idle_seconds = time.time() - SERVER_ACTIVITY.last_seen
                if idle_seconds > 25:
                    print(f"\n[*] Arayüz penceresi kapatıldı ({idle_seconds:.0f}s sessiz). Sunucu sonlandırılıyor...")
                    server.shutdown()
                    break

    threading.Thread(target=watchdog_monitor, daemon=True).start()

    # Block main thread until server is stopped or Ctrl+C
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] Kullanıcı çıkış yaptı.")
    finally:
        print("[*] Sunucu kapatıldı.")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
