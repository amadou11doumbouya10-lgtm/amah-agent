import subprocess
import tempfile
import os
import logging

log = logging.getLogger("amah.computer_settings")


def _run_ps(cmd: str) -> tuple:
    """Exécute une commande PowerShell (une ligne), retourne (succès, sortie)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return r.returncode == 0, (r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        return False, str(e)


def _run_ps_file(script: str) -> tuple:
    """Écrit un script .ps1 dans un fichier temp et l'exécute (pour les here-strings)."""
    fname = None
    try:
        fd, fname = tempfile.mkstemp(suffix='.ps1')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", fname],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return r.returncode == 0, (r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        return False, str(e)
    finally:
        if fname:
            try:
                os.unlink(fname)
            except Exception as e:
                log.debug(f"Suppression du fichier temporaire {fname} ignoree : {e}")


# Définition C# commune pour le contrôle audio Windows (WinMM + keybd_event)
_AUDIO_CS = """\
using System;
using System.Runtime.InteropServices;
public class WinAudio {
    [DllImport("winmm.dll")] static extern int waveOutSetVolume(IntPtr h, uint v);
    [DllImport("winmm.dll")] static extern int waveOutGetVolume(IntPtr h, out uint v);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
    public static void SetVol(int pct) {
        uint val = (uint)(0xFFFF * pct / 100);
        waveOutSetVolume(IntPtr.Zero, (val & 0xFFFF) | (val << 16));
    }
    public static int GetVol() {
        uint val; waveOutGetVolume(IntPtr.Zero, out val);
        return (int)((val & 0xFFFF) * 100 / 0xFFFF);
    }
    public static void SendKey(byte vk) {
        keybd_event(vk, 0, 0, IntPtr.Zero);
        keybd_event(vk, 0, 2, IntPtr.Zero);
    }
}
"""


def _audio_script(action_line: str) -> str:
    """Génère un script PS1 complet avec le type WinAudio + une action."""
    return (
        "if (-not ([System.Management.Automation.PSTypeName]'WinAudio').Type) {\n"
        "    Add-Type -TypeDefinition @'\n"
        + _AUDIO_CS +
        "'@\n"
        "}\n"
        + action_line + "\n"
    )


def set_volume(level: int) -> dict:
    """Règle le volume système entre 0 et 100."""
    level = max(0, min(100, int(level)))
    ok, out = _run_ps_file(_audio_script(f"[WinAudio]::SetVol({level})"))
    return {"success": True, "volume": f"{level}%"} if ok else {"error": f"Volume: {out}"}


def get_audio_level() -> dict:
    """Retourne le niveau de volume actuel (0-100)."""
    ok, out = _run_ps_file(_audio_script("[WinAudio]::GetVol()"))
    if ok and out:
        val = out.split()[0]
        return {"success": True, "volume": f"{val}%"}
    return {"error": f"Lecture volume: {out}"}


def mute_audio() -> dict:
    """Bascule le son système (muet / non-muet) via la touche Volume Mute."""
    ok, out = _run_ps_file(_audio_script("[WinAudio]::SendKey(0xAD)"))
    return {"success": True, "action": "son bascule (muet/non-muet)"} if ok else {"error": out}


def set_brightness(level: int) -> dict:
    """Règle la luminosité de l'écran (0-100). Fonctionne sur les écrans internes (laptops)."""
    level = max(0, min(100, int(level)))
    ok, out = _run_ps(
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1, {level})"
    )
    return {"success": True, "luminosite": f"{level}%"} if ok else {
        "error": f"Luminosite indisponible (ecran externe ou WMI non supporte): {out}"
    }


def get_brightness() -> dict:
    """Retourne la luminosité actuelle de l'écran."""
    ok, out = _run_ps(
        "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
    )
    return {"success": True, "luminosite": f"{out}%"} if (ok and out) else {
        "error": f"Impossible de lire la luminosite: {out}"
    }


def wifi_toggle(enable: bool = True) -> dict:
    """Active ou désactive le WiFi Windows (netsh)."""
    action    = "enable" if enable else "disable"
    action_fr = "active" if enable else "desactive"
    for name in ["Wi-Fi", "WiFi", "Wireless", "WLAN"]:
        ok, out = _run_ps(f'netsh interface set interface "{name}" {action}')
        if ok or out == "" or "successfully" in out.lower():
            return {"success": True, "wifi": action_fr, "interface": name}
    return {"error": f"Interface WiFi introuvable ou commande echouee: {out}"}
