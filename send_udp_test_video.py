#!/usr/bin/env python3
"""Send a local test video by UDP H.264 to the configured destination.

This is meant to work from the dron_detect project and to be cross-platform
(Windows and Ubuntu/Linux). It streams the file to the UDP endpoint used by the
project's test receiver: UDP 37511.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_PORT = 37511
DEFAULT_IP = "127.0.0.1"


def find_video_path(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())

    repo_root = Path(__file__).resolve().parent
    candidates.extend(
        [
            repo_root / "Video_prueba.mp4",
            repo_root / "data" / "test_videos" / "Video_prueba.mp4",
            repo_root / "data" / "test_videos" / "video_prueba.mp4",
            repo_root.parent / "EMISOR VIDEO STREAMING H264" / "Video_prueba.mp4",
            Path("Video_prueba.mp4").expanduser(),
        ]
    )

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        "No se encontró Video_prueba.mp4. Usa --video con la ruta exacta del archivo."
    )


def ffmpeg_binary() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"

    local = Path(__file__).resolve().parent
    for candidate in [
        local / "ffmpeg",
        local / "ffmpeg.exe",
        Path.cwd() / "ffmpeg",
        Path.cwd() / "ffmpeg.exe",
    ]:
        if candidate.exists():
            return str(candidate)
    return "ffmpeg"


def build_command(video_path: Path, ip: str, port: int, width: int, height: int, fps: int, loop: bool) -> list[str]:
    cmd = [
        ffmpeg_binary(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-re",
    ]
    if loop:
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i",
        str(video_path),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        f"scale={width}:{height},fps={fps}",
        "-b:v",
        "1200k",
        "-maxrate",
        "1500k",
        "-bufsize",
        "3000k",
        "-g",
        "30",
        "-mpegts_flags",
        "+resend_headers",
        "-f",
        "mpegts",
        f"udp://{ip}:{port}?pkt_size=1316",
    ]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Emite un video local por UDP H.264 al puerto 37511.")
    parser.add_argument("--video", default=None, help="Ruta del video a transmitir. Si no se indica, busca Video_prueba.mp4.")
    parser.add_argument("--ip", default=DEFAULT_IP, help="IP del receptor (127.0.0.1 para pruebas locales).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Puerto UDP del receptor (por defecto: 37511).")
    parser.add_argument("--width", type=int, default=1280, help="Ancho del flujo emitido.")
    parser.add_argument("--height", type=int, default=720, help="Alto del flujo emitido.")
    parser.add_argument("--fps", type=int, default=30, help="FPS del flujo emitido.")
    parser.add_argument("--loop", action="store_true", help="Repite el video indefinidamente.")
    parser.add_argument("--duration", type=float, default=None, help="Duración máxima de transmisión en segundos para pruebas. Si no se indica, transmite hasta pulsar Ctrl+C.")
    args = parser.parse_args()

    try:
        video_path = find_video_path(args.video)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if shutil.which("ffmpeg") is None and not any(Path(p).exists() for p in [
        Path(__file__).resolve().parent / "ffmpeg",
        Path(__file__).resolve().parent / "ffmpeg.exe",
        Path.cwd() / "ffmpeg",
        Path.cwd() / "ffmpeg.exe",
    ]):
        print("[ERROR] FFmpeg no está instalado ni en PATH ni junto al proyecto.", file=sys.stderr)
        print("        Ubuntu: sudo apt install ffmpeg", file=sys.stderr)
        print("        Windows: añade ffmpeg.exe a la carpeta del proyecto o a PATH.", file=sys.stderr)
        return 3

    cmd = build_command(video_path, args.ip, args.port, args.width, args.height, args.fps, args.loop)
    if args.duration is not None:
        cmd = [
            *cmd[:4],
            "-t",
            str(args.duration),
            *cmd[4:],
        ]

    print(f"[INFO] Enviando {video_path} a udp://{args.ip}:{args.port}")
    print(f"[INFO] Comando FFmpeg: {' '.join(cmd)}")

    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\n[INFO] Transmisión detenida por el usuario.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
