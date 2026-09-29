"""Provision the local runtime assets for the C-UAS webcam demonstrator.

Run ``python setup_environment.py --install`` on a new machine.  The default
YOLO11n weight is a small COCO baseline; pass --weights with a licensed drone
detector weight file/URL for operational drone-class detection.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "ultralytics": "ultralytics",
    "cv2": "opencv-python",
    "filterpy": "filterpy",
    "numpy": "numpy",
    "torch": "torch",
}
DRONE_MODEL_NAME = "drone_v3.1.pt"
# Public checkpoint from the Anti-UAV project. Verify its license/suitability before
# operational deployment; it is intended as a local evaluation baseline.
DRONE_MODEL_URL = "https://github.com/Coco-Spot/Anti-UAV/raw/refs/heads/main/models/drone_v3.1.pt"
MARITIME_MODEL_NAME = "argus_maritime_yolov8s.pt"
MARITIME_MODEL_URL = "https://huggingface.co/alimkacar/argus-maritime-yolov8s/resolve/main/best.pt"


def ensure_directories() -> None:
    for directory in (ROOT / "models", ROOT / "data" / "test_videos", ROOT / "logs"):
        directory.mkdir(parents=True, exist_ok=True)


def check_dependencies(install: bool) -> None:
    missing = [package for module, package in REQUIRED.items() if importlib.util.find_spec(module) is None]
    if missing and install:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
        missing = [package for module, package in REQUIRED.items() if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError("Missing packages: " + ", ".join(missing) + ". Re-run with --install.")


def validate_opencv() -> None:
    import cv2

    info = cv2.getBuildInformation()
    available = [name for name, flag in (("DirectShow", cv2.CAP_DSHOW), ("V4L2", cv2.CAP_V4L2)) if flag is not None]
    print(f"OpenCV {cv2.__version__}; camera APIs available: {', '.join(available)}")
    print("FFMPEG enabled:" , "FFMPEG:" in info)


def download_public_weights(destination: Path, url: str, description: str) -> Path:
    """Fetch a public checkpoint atomically, avoiding partial weights."""
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {description} to {destination} ...")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "cuas-project/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if temporary.stat().st_size < 1_000_000:
            raise RuntimeError("Downloaded checkpoint is unexpectedly small.")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print(f"Saved weights: {destination}")
    return destination


def download_weights(weights: str) -> Path:
    """Download through Ultralytics' official asset resolver into models/."""
    from ultralytics import YOLO

    requested = Path(weights)
    destination = ROOT / "models" / requested.name
    if destination.exists():
        print(f"Weights already present: {destination}")
        return destination
    if requested.name == DRONE_MODEL_NAME:
        return download_public_weights(destination, DRONE_MODEL_URL, "specialized Anti-UAV detector")
    if requested.name == MARITIME_MODEL_NAME:
        return download_public_weights(destination, MARITIME_MODEL_URL, "specialized maritime detector")
    print(f"Resolving model weights: {weights}")
    model = YOLO(weights)  # Ultralytics downloads recognized public assets if needed.
    source = Path(str(model.ckpt_path or weights))
    if source.exists() and source.resolve() != destination.resolve():
        destination.write_bytes(source.read_bytes())
    if not destination.exists():
        raise RuntimeError(f"Could not locate downloaded weights for {weights}")
    print(f"Saved weights: {destination}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision C-UAS project prerequisites.")
    parser.add_argument("--install", action="store_true", help="Install missing Python dependencies.")
    parser.add_argument("--weights", default=DRONE_MODEL_NAME, help="Weight file. Default: specialized Anti-UAV drone detector.")
    parser.add_argument("--maritime-model", action="store_true", help="Download the optional maritime vessel detector as well.")
    parser.add_argument("--no-download", action="store_true", help="Only validate the environment.")
    args = parser.parse_args()
    ensure_directories()
    check_dependencies(args.install)
    validate_opencv()
    if not args.no_download:
        download_weights(args.weights)
        if args.maritime_model:
            download_weights(MARITIME_MODEL_NAME)
    print("Environment ready.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
