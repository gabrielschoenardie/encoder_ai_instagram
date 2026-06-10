# pylint: disable=invalid-name
"""Busca o frame mais próximo de um timestamp em um vídeo via ffprobe."""
import subprocess
import sys

VIDEO = "VideobythecBEFORE_2PassS.mp4"
TARGET_TIME = float(sys.argv[1]) if len(sys.argv) > 1 else 4.000

cmd = [
    "ffprobe",
    "-v", "error",
    "-select_streams", "v:0",
    "-show_packets",
    VIDEO
]

best_frame = None
best_diff = None
best_time = None

frame_index = 0

with subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
    errors="ignore"
) as process:
    for line in process.stdout:
        line = line.strip()

        # procuramos SOMENTE linhas com pts_time
        if not line.startswith("pts_time="):
            continue

        try:
            ts = float(line.split("=", 1)[1])
        except ValueError:
            continue

        diff = abs(ts - TARGET_TIME)

        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_frame = frame_index
            best_time = ts

        frame_index += 1

if best_frame is not None:
    print(
        f"Tempo {TARGET_TIME:.3f}s → "
        f"Frame {best_frame} "
        f"(timestamp real {best_time:.6f}s)"
    )
else:
    print("Nenhum frame válido encontrado.")
