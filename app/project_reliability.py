"""Qt-free staged project validation for original MontaSpace files."""
import json
import zipfile
from pathlib import Path


def verify_staged_project(path, expected_count, portable):
    """Reject incomplete output before replacing an existing user project."""
    path = Path(path)
    if portable:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [entry.filename for entry in members]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate portable archive entries")
            data = json.loads(archive.read("project.json").decode("utf-8"))
            images = data.get("images", [])
            available = set(names)
            if any(image.get("source") not in available for image in images):
                raise ValueError("Missing embedded image")
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        images = data.get("images", [])
    if (data.get("format") != "MontaSpace" or data.get("version") != 1
            or len(images) != expected_count
            or (portable and data.get("portable") is not True)):
        raise ValueError("Project verification failed; existing file was preserved")
