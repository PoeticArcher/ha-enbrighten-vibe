"""Publish one GitHub release after the workflow's validation jobs succeed."""

import os
import subprocess

from build_release import ROOT, build_release


def main() -> None:
    version, archive = build_release()
    notes = ROOT / "dist/release-notes.md"
    notes.write_text(
        "# Enbrighten VIBE Cloud " + version + "\n\n"
        "Developed and maintained by **Viking Mann**.\n\n"
        "Adds RGB color, brightness and on/off control for Enbrighten Eternity "
        "Landscape Lights, product wagmuetuwhn4lgr7, using Tuya developer OpenAPI.\n\n"
        "The device owner has confirmed that the implemented controls work. "
        "HACS validation, hassfest, and automated tests passed for this release.\n\n"
        "See the README for HACS installation, developer-project credentials, "
        "supported devices and configurable polling.\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            f"v{version}",
            str(archive),
            "--repo",
            os.environ["GH_REPO"],
            "--target",
            os.environ["GITHUB_SHA"],
            "--title",
            f"Enbrighten VIBE Cloud {version}",
            "--notes-file",
            str(notes),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
