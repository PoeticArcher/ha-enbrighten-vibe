"""Build a complete manual-install archive from the integration tree."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/enbrighten_vibe"
DOCUMENTS = (
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "UPSTREAM_REPORT.md",
    "VALIDATION.md",
    "hacs.json",
)


def build_release() -> tuple[str, Path]:
    """Return the manifest version and the verified install archive."""
    version = json.loads((COMPONENT / "manifest.json").read_text())["version"]
    output_dir = ROOT / "dist"
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / f"enbrighten-vibe-v{version}.zip"
    paths = [
        path
        for path in sorted(COMPONENT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    ]
    paths.extend(ROOT / name for name in DOCUMENTS)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT))
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP verification failed")
    return version, destination


if __name__ == "__main__":
    version, destination = build_release()
    print(f"Built {destination.name} for version {version}")
