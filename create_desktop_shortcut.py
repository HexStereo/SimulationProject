"""
create_desktop_shortcut.py - Creates Windows Desktop Shortcut with Custom Icon
================================================================================
"""

import os
import subprocess
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def create_shortcut():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    target_bat = os.path.join(project_dir, "launch.bat")
    icon_path = os.path.join(project_dir, "assets", "icon.ico")

    # Get desktop folder path
    desktop_folder = os.path.expanduser(r"~\Desktop")
    if not os.path.exists(desktop_folder):
        desktop_folder = r"C:\Users\ardab\Desktop"

    shortcut_path = os.path.join(desktop_folder, "6-Haneli Kod Simulatoru.lnk")

    # PowerShell script to create Windows shortcut via WScript.Shell
    ps_command = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_bat}"
$Shortcut.WorkingDirectory = "{project_dir}"
$Shortcut.IconLocation = "{icon_path}, 0"
$Shortcut.Description = "6 Haneli Kod Istatistiksel Anomali ve Periyot Simulatoru"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "Masaustu kisayolu basariyla olusturuldu: $Shortcut.FullName"
"""

    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True, check=True)
        print(proc.stdout.strip())
        print(f"[OK] Kısayol oluşturuldu: {shortcut_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[HATA] Kısayol oluşturulamadı: {e.stderr}")
        return False


if __name__ == "__main__":
    create_shortcut()
