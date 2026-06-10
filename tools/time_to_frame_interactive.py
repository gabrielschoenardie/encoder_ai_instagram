#!/usr/bin/env python3
# pylint: disable=duplicate-code,missing-function-docstring,unnecessary-lambda-assignment,invalid-name,consider-using-with
"""
Conversor interativo: Timestamp → Frame Number
Uso: python time_to_frame_interactive.py
"""

import os
import subprocess
import sys


# ── terminal helpers ──────────────────────────────────────────────────────────

def clr(code, text):
    return f"\033[{code}m{text}\033[0m"

CYAN   = lambda t: clr("96", t)
GREEN  = lambda t: clr("92", t)
YELLOW = lambda t: clr("93", t)
RED    = lambda t: clr("91", t)
BOLD   = lambda t: clr("1",  t)
DIM    = lambda t: clr("2",  t)


def header():
    print()
    print(BOLD("┌─────────────────────────────────────────┐"))
    print(BOLD("│") + CYAN("  🎞️  Timestamp → Frame  ") + DIM("(time_to_frame)") + BOLD("  │"))
    print(BOLD("└─────────────────────────────────────────┘"))
    print()


def ask(prompt, default=None):
    suffix = DIM(f" [{default}]") if default is not None else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n  {YELLOW('Saindo.')} ")
        sys.exit(0)
    return val if val else default


def ask_file(prompt):
    while True:
        path = ask(prompt)
        if not path:
            print(f"  {RED('Campo obrigatório.')}")
            continue
        if os.path.exists(path):
            return path
        print(f"  {RED(f'Arquivo não encontrado: {path}')}")


def parse_timestamps(raw: str) -> list[float]:
    """Aceita '4.0', '4.0 8.68', '4:05', '1:02:03.5' etc."""
    tokens = raw.replace(",", " ").split()
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        # formato hh:mm:ss.ms ou mm:ss.ms
        if ":" in t:
            parts = t.split(":")
            secs = 0.0
            for p in parts:
                secs = secs * 60 + float(p)
            result.append(secs)
        else:
            result.append(float(t))
    return result


# ── core logic ────────────────────────────────────────────────────────────────

def find_frame(video: str, target: float) -> tuple[int | None, float | None]:
    """Retorna (frame_index, real_timestamp) mais próximo de target."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_packets",
        video
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="ignore"
        )
    except FileNotFoundError:
        print(f"  {RED('ffprobe não encontrado. Instale o FFmpeg.')}")
        sys.exit(1)

    best_frame = None
    best_diff  = None
    best_time  = None
    frame_index = 0

    for line in proc.stdout:
        line = line.strip()
        if not line.startswith("pts_time="):
            continue
        try:
            ts = float(line.split("=", 1)[1])
        except ValueError:
            continue
        diff = abs(ts - target)
        if best_diff is None or diff < best_diff:
            best_diff  = diff
            best_frame = frame_index
            best_time  = ts
        frame_index += 1

    proc.wait()
    return best_frame, best_time


def show_results(rows: list[tuple[float, int | None, float | None]]):
    print()
    print(BOLD("  ┌──────────────┬─────────────┬──────────────────────┐"))
    print(BOLD("  │") + CYAN("  Timestamp   ") +
          BOLD("│") + CYAN("    Frame    ") +
          BOLD("│") + CYAN("  Timestamp real      ") + BOLD("│"))
    print(BOLD("  ├──────────────┼─────────────┼──────────────────────┤"))
    for target, frame, real_ts in rows:
        if frame is None:
            row_frame = RED("   não encontrado")
            row_ts    = RED("  —                  ")
        else:
            row_frame = GREEN(f"   {frame:<10}")
            diff_ms   = abs(real_ts - target) * 1000
            row_ts    = f"  {real_ts:.6f}s  " + DIM(f"(Δ {diff_ms:.2f} ms)")
        row_target = f"  {target:.3f}s      "
        print(BOLD("  │") + row_target + BOLD("│") + row_frame + BOLD("│") + row_ts + BOLD("│"))
    print(BOLD("  └──────────────┴─────────────┴──────────────────────┘"))
    print()


# ── main loop ─────────────────────────────────────────────────────────────────

def main():
    header()

    video = ask_file(f"{BOLD('Vídeo')} (arraste o arquivo ou cole o caminho)")
    print(f"  {DIM('─' * 43)}")

    while True:
        raw = ask(
            f"{BOLD('Timestamps')} "
            + DIM("(ex: 4.0  8.68  1:05.3 — vários separados por espaço)")
        )
        if not raw:
            print(f"  {YELLOW('Informe ao menos um timestamp.')}")
            continue

        try:
            timestamps = parse_timestamps(raw)
        except ValueError:
            print(f"  {RED('Formato inválido. Use segundos (4.0) ou mm:ss (1:05).')}")
            continue

        if not timestamps:
            print(f"  {YELLOW('Nenhum timestamp reconhecido.')}")
            continue

        print(f"\n  {DIM('Consultando ffprobe...')}")
        rows = []
        for ts in timestamps:
            frame, real_ts = find_frame(video, ts)
            rows.append((ts, frame, real_ts))

        show_results(rows)

        again = ask(f"Consultar mais timestamps no mesmo vídeo? {DIM('(s/n)')}", "s")
        if again.lower() != "s":
            break

    print(f"  {GREEN('Pronto.')}\n")


if __name__ == "__main__":
    main()
