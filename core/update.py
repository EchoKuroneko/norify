import requests
from packaging.version import Version
from config import APP_NAME


def check_for_update(current_version):
    """
    Checks GitHub for the latest release.

    Returns:
        latest_version (str) if a newer version exists, else None
    """
    try:
        url = f"https://api.github.com/repos/EchoKuroneko/{APP_NAME.lower()}/releases/latest"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        latest_version = data["tag_name"].lstrip("v")
        download_url = data["html_url"]

        if Version(latest_version) > Version(current_version):
            return latest_version, download_url
    except Exception:
        # Fail silently
        return None
