import time
from pathlib import Path

import cv2

from cuas_engine.main_hmi import TacticalHMI


def main():
    source = "udp://127.0.0.1:37511"
    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    print(f"[INFO] Capture opened: {cap.isOpened()}")
    if not cap.isOpened():
        return 1

    frames = 0
    while frames < 5:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("[WARN] No frame available yet...")
            time.sleep(0.5)
            continue
        print(f"[INFO] Frame {frames + 1}: shape={frame.shape}, dtype={frame.dtype}")
        frames += 1

    cap.release()
    print("[INFO] Releasing capture; testing HMI detection on first valid frame...")
    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        print("[ERROR] No frames decoded from UDP stream.")
        return 2

    weights = Path(__file__).resolve().parent / "models" / "drone_v3.1.pt"
    hmi = TacticalHMI(weights, confidence=0.25, imgsz=960, device="cpu")
    detections = hmi.detect(frame)
    print(f"[INFO] Detections: {len(detections)}")
    for d in detections[:5]:
        print(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
