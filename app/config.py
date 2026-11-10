"""Application constants and resource paths."""
import sys
from pathlib import Path


PROJECT_FILTER = "MontaSpace Linked (*.mspace);;MontaSpace Portable (*.mspacepack)"
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PREVIEW_MAX_EDGE = 1600
APP_VERSION = "0.8.1"
PUBLISHER = "BC Shin Studio"
COPYRIGHT = "© 2026 BC Shin Studio. All rights reserved."
WEBSITE = "https://www.bcshinstudio.com"


def asset_path(relative_path):
    """Locate assets from both source runs and a PyInstaller bundle."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return root / relative_path
