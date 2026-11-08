"""Optional JavaScript-rendering fallback for a few Windows-only retailer pages.

Uses the user's already installed Chrome or Edge binary; requires no Python
browser package, browser download, user profile, credentials or API key.
Never use this for arbitrary domains, never capture cookies or save HTML.
"""
import os
import platform
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse

_ALLOWED_HOSTS = ("pccomponentes.pt", "chip7.pt", "pcdiga.com",
                  "chipman.pt", "castroelectronica.pt")
_MAX_HTML_CHARS = 5_000_000


def _browser_path():
    if platform.system() != "Windows":
        return None
    roots = [os.environ.get("PROGRAMFILES", ""),
             os.environ.get("PROGRAMFILES(X86)", ""),
             os.environ.get("LOCALAPPDATA", "")]
    relative = [
        ("Google", "Chrome", "Application", "chrome.exe"),
        ("Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for root in roots:
        if not root:
            continue
        for segments in relative:
            exe = Path(root).joinpath(*segments)
            if exe.is_file():
                return str(exe)
    return None


def render_dom(url, timeout_seconds=24):
    """Return rendered HTML or None, only for authorized retailer domains.

    Chrome --dump-dom executes page scripts first. A separate temporary
    browser profile prevents access to the user's existing browser cookies.
    """
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or
            not any(hostname == domain or hostname.endswith("." + domain)
                    for domain in _ALLOWED_HOSTS)):
        return None
    executable = _browser_path()
    if not executable:
        return None
    try:
        with tempfile.TemporaryDirectory(prefix="ram-hunter-browser-") as profile:
            command = [
                executable, "--headless=new", "--disable-gpu",
                "--disable-extensions", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking",
                "--window-size=1440,900", "--virtual-time-budget=5000",
                "--dump-dom", "--user-data-dir=" + profile, url
            ]
            result = subprocess.run(
                command, capture_output=True, check=False, timeout=timeout_seconds,
                text=True, encoding="utf-8", errors="replace"
            )
            body = result.stdout or ""
            if (result.returncode != 0 or
                    len(body) > _MAX_HTML_CHARS or
                    "<html" not in body.lower() or
                    "<h1" not in body.lower()):
                return None
            return body
    except (OSError, subprocess.TimeoutExpired):
        return None
