"""C-UAS webcam application entry point."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2

from cuas_engine.main_hmi import TacticalHMI
from cuas_engine.stream_engine import UniversalVideoStream, discover_cameras, normalize_source_url

WINDOW_NAME = "C-UAS Tactical Display"


def parse_source(value: str):
    return int(value) if value.isdigit() else value


def configured_stream(config_path: Path) -> tuple[str, str]:
    """Read an optional local stream URL; an empty configuration keeps USB mode."""
    if not config_path.exists():
        return "", "tcp"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        url = str(payload.get("active_stream_url", "")).strip()
        if url and not url.lower().startswith(("rtsp://", "rtsps://", "http://", "https://", "udp://")):
            url = normalize_source_url(url)
        transport = str(payload.get("rtsp_transport", "tcp")).lower()
        return url, transport if transport in {"tcp", "udp"} else "tcp"
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid stream configuration {config_path}: {exc}") from exc


def main() -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Local C-UAS real-time detector (webcam default: 0).")
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--stream-url", default="", help="RTSP/HTTP/HLS/UDP URL. Overrides --source and stream config.")
    parser.add_argument("--stream-config", type=Path, default=root / "config" / "stream_sources.json",
                        help="JSON config containing active_stream_url.")
    parser.add_argument("--rtsp-transport", choices=("tcp", "udp"), default="",
                        help="RTSP transport; overrides the stream config.")
    parser.add_argument("--weights", type=Path, default=root / "models" / "drone_v3.1.pt")
    parser.add_argument("--conf", type=float, default=.25)
    parser.add_argument("--imgsz", type=int, default=960, help="Inference resolution; 960 improves small/far targets but is slower.")
    parser.add_argument("--camera-width", type=int, default=1280, help="Resolucion solicitada a la webcam (0 conserva la nativa).")
    parser.add_argument("--camera-height", type=int, default=720, help="Resolucion solicitada a la webcam (0 conserva la nativa).")
    parser.add_argument("--camera-fps", type=int, default=30, help="FPS solicitados a la webcam.")
    parser.add_argument("--camera-scan-max", type=int, default=8, help="Indices USB a explorar para el selector de camara.")
    parser.add_argument("--window-width", type=int, default=1280, help="Ancho de la ventana HMI (0 usa el ajuste de OpenCV).")
    parser.add_argument("--window-height", type=int, default=720, help="Alto de la ventana HMI (0 usa el ajuste de OpenCV).")
    parser.add_argument("--device", default="", help="YOLO device, e.g. 0, cpu")
    parser.add_argument("--airborne-only", action="store_true", help="Muestra solo bird/airplane/kite/drone/uav.")
    parser.add_argument("--all-classes", action="store_true", help="Compatibilidad: todas las clases ya son el modo predeterminado.")
    parser.add_argument("--maritime", "--multi-domain", dest="maritime", action="store_true", help="Activa detectores secundarios naval y aéreo; no modifica el detector UAV.")
    parser.add_argument("--maritime-weights", type=Path, default=root / "models" / "argus_maritime_yolov8s.pt", help="Peso naval especializado compatible con Ultralytics.")
    parser.add_argument("--maritime-conf", type=float, default=.30, help="Umbral independiente para embarcaciones.")
    parser.add_argument("--maritime-interval", type=int, default=3, help="Ejecuta el detector maritimo cada N fotogramas.")
    parser.add_argument("--aircraft-weights", type=Path, default=root / "models" / "yolo11n.pt", help="Peso general para aeronaves.")
    parser.add_argument("--aircraft-conf", type=float, default=.30, help="Umbral independiente para aeronaves.")
    args = parser.parse_args()
    configured_url, configured_transport = configured_stream(args.stream_config)
    stream_url = (args.stream_url.strip() or configured_url).strip()
    if stream_url and not stream_url.lower().startswith(("rtsp://", "rtsps://", "http://", "https://", "udp://")):
        stream_url = normalize_source_url(stream_url)
    stream_transport = args.rtsp_transport or configured_transport
    if not args.weights.exists():
        print(f"Weights not found: {args.weights}. Run: py -3 setup_environment.py --install", file=sys.stderr)
        return 2
    if args.maritime and not args.maritime_weights.exists():
        print(f"Maritime weights not found: {args.maritime_weights}. Run: py -3 setup_environment.py --maritime-model", file=sys.stderr)
        return 2
    if args.maritime and not args.aircraft_weights.exists():
        print(f"Aircraft weights not found: {args.aircraft_weights}. Run: py -3 setup_environment.py --weights yolo11n.pt", file=sys.stderr)
        return 2
    stream = None
    try:
        hmi = TacticalHMI(args.weights, args.conf, args.imgsz, args.device, not args.airborne_only,
                          args.maritime_weights if args.maritime else None, args.maritime_conf, args.maritime_interval,
                          args.aircraft_weights if args.maritime else None, args.aircraft_conf, args.maritime_interval)
        # Numeric local sources support live switching from the HMI. File and
        # RTSP sources preserve the source supplied on the command line.
        active_source = stream_url if stream_url else parse_source(args.source)
        camera_indexes = discover_cameras(args.camera_scan_max) if isinstance(active_source, int) else []
        if isinstance(active_source, int) and active_source not in camera_indexes:
            camera_indexes.insert(0, active_source)
        requested_source = [active_source]

        def request_camera(position: int) -> None:
            """Trackbar callback; the main loop safely opens the selected camera."""
            if camera_indexes:
                requested_source[0] = camera_indexes[max(0, min(position, len(camera_indexes) - 1))]

        stream = UniversalVideoStream(active_source, args.camera_width or None,
                                      args.camera_height or None, args.camera_fps, rtsp_transport=stream_transport).start()
        hmi.set_camera_source("STREAM" if stream_url else active_source)
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        if args.window_width and args.window_height:
            cv2.resizeWindow(WINDOW_NAME, args.window_width, args.window_height)
        # These are live controls: changing either takes effect in the next inference frame.
        cv2.createTrackbar("UMBRAL confianza (%)", WINDOW_NAME, round(args.conf * 100), 95, hmi.set_confidence)
        cv2.createTrackbar("MISION: 0 Combinado 1 UAV 2 Aereo 3 Mar", WINDOW_NAME, hmi.filter_mode, 3, hmi.set_filter_mode)
        if len(camera_indexes) > 1:
            initial_position = camera_indexes.index(active_source)
            cv2.createTrackbar("CAMARA USB", WINDOW_NAME, initial_position, len(camera_indexes) - 1, request_camera)
        if args.maritime:
            cv2.createTrackbar("UMBRAL maritimo (%)", WINDOW_NAME, round(args.maritime_conf * 100), 95, hmi.set_maritime_confidence)
            cv2.createTrackbar("UMBRAL aereo (%)", WINDOW_NAME, round(args.aircraft_conf * 100), 95, hmi.set_aircraft_confidence)
        while True:
            # Do not stop the live feed until the requested source opens
            # successfully; this makes an invalid USB selection recoverable.
            if requested_source[0] != active_source:
                candidate = None
                try:
                    candidate = UniversalVideoStream(requested_source[0], args.camera_width or None,
                                                     args.camera_height or None, args.camera_fps,
                                                     rtsp_transport=stream_transport).start()
                    stream.stop()
                    stream, active_source = candidate, requested_source[0]
                    hmi.set_camera_source(active_source)
                except RuntimeError as exc:
                    if candidate:
                        candidate.stop()
                    print(f"Camera change rejected: {exc}", file=sys.stderr)
                    requested_source[0] = active_source
                    if len(camera_indexes) > 1:
                        cv2.setTrackbarPos("CAMARA USB", WINDOW_NAME, camera_indexes.index(active_source))
            frame = stream.read()
            if stream.failed: raise RuntimeError("Video device lost or video stream ended.")
            if frame is None:
                time.sleep(.005); continue
            display, tracks = hmi.process(frame)
            cv2.imshow(WINDOW_NAME, display)
            if not hmi.handle_key(cv2.waitKey(1) & 0xFF, tracks): break
            # Keep the visible selector synchronized when the F keyboard shortcut is used.
            cv2.setTrackbarPos("MISION: 0 Combinado 1 UAV 2 Aereo 3 Mar", WINDOW_NAME, hmi.filter_mode)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Application error: {exc}", file=sys.stderr)
        return 1
    finally:
        if stream: stream.stop()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
