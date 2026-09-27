"""Copy the minimum of an installed Tesseract needed to run OCR.

A full Tesseract install is ~110 MB, mostly model-training tools and their
libraries. The app only runs tesseract.exe, so this copies that, the DLLs
it actually loads (found by walking the import tables), and the English
and orientation-detection models.

Usage: python collect_tesseract.py <tesseract install dir> <output dir>
"""

import shutil
import sys
from pathlib import Path

import pefile

MODELS = ("eng.traineddata", "osd.traineddata")


def dll_closure(install: Path) -> set[str]:
    local = {p.name.lower(): p for p in install.glob("*.dll")}
    needed: set[str] = set()
    queue = ["tesseract.exe"]
    while queue:
        pe = pefile.PE(str(install / queue.pop()), fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
        )
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            name = entry.dll.decode().lower()
            if name in local and name not in needed:
                needed.add(name)
                queue.append(local[name].name)
        pe.close()
    return {local[name].name for name in needed}


def main(install: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    (output / "tessdata").mkdir(parents=True)
    shutil.copy2(install / "tesseract.exe", output)
    for dll in sorted(dll_closure(install)):
        shutil.copy2(install / dll, output)
    for model in MODELS:
        shutil.copy2(install / "tessdata" / model, output / "tessdata")
    # Tesseract is Apache-2.0; its licence ships with it.
    for notice in ("LICENSE", "LICENSE.txt", "COPYING"):
        if (install / notice).exists():
            shutil.copy2(install / notice, output / "LICENSE.txt")
            break
    size = sum(f.stat().st_size for f in output.rglob("*") if f.is_file()) / 2**20
    print(f"Tesseract collected into {output} ({size:.0f} MB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
