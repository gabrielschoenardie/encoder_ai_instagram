#!/usr/bin/env python3
# pylint: disable=duplicate-code
"""
Wrapper interativo para compare_frames.py
Uso: python compare_frames_interactive.py
"""

import os
import sys
import subprocess
from pathlib import Path


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    try:
        val = input(f"{prompt}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")
        sys.exit(0)
    return val if val else default


def ask_file(prompt):
    while True:
        path = ask(prompt)
        if not path:
            print("  ⚠️  Campo obrigatório.")
            continue
        if os.path.exists(path):
            return path
        print(f"  ❌ Arquivo não encontrado: {path}")


def ask_choice(prompt, options, default=None):
    labels = " / ".join(
        f"[{o}]" if o == default else o for o in options
    )
    while True:
        val = ask(f"{prompt} ({labels})", default)
        if val in options:
            return val
        print(f"  ⚠️  Escolha uma das opções: {', '.join(options)}")


def ask_numbers(prompt, type_=int):
    while True:
        raw = ask(prompt)
        if not raw:
            print("  ⚠️  Informe ao menos um valor.")
            continue
        try:
            return [type_(x) for x in raw.split()]
        except ValueError:
            print("  ⚠️  Números inválidos. Separe por espaço (ex: 121 261)")


def main():
    print("\n🎬  Frame Comparison — Modo Interativo")
    print("=" * 45)
    print("Pressione Enter para usar o valor padrão.\n")

    # --- Arquivos ---
    original = ask_file("📁 Vídeo ORIGINAL")
    encoded  = ask_file("📁 Vídeo ENCODADO")

    # --- Frames ou timestamps ---
    mode = ask_choice("⏱️  Usar frames ou timestamps?", ["frames", "timestamps"], "frames")

    if mode == "frames":
        values = ask_numbers("🖼️  Números dos frames (ex: 121 261)", int)
        frame_args = ["--frames"] + [str(v) for v in values]
    else:
        values = ask_numbers("⏱️  Timestamps em segundos (ex: 4.0 8.68)", float)
        frame_args = ["--timestamps"] + [str(v) for v in values]

    output_dir = "compare_encodes"

    # --- Comparações extras ---
    print()
    do_diff   = True
    do_triple = True
    do_zoom   = ask_choice("🔎 Gerar zoom?",               ["s", "n"], "n") == "s"

    zoom_region = None
    if do_zoom:
        zoom_raw = ask("   Região de zoom x,y,w,h", "0,400,500,700")
        zoom_region = zoom_raw

    do_all    = ask_choice("✨ Gerar TUDO de uma vez?",    ["s", "n"], "n") == "s"

    # --- Montar comando ---
    script = Path(__file__).parent / "compare_frames.py"
    cmd = [sys.executable, str(script), original, encoded] + frame_args
    cmd += ["-o", output_dir]

    if do_all:
        cmd += ["--all"]
    else:
        if do_diff:   cmd += ["--diff"]
        if do_triple: cmd += ["--triple"]
        if do_zoom:   cmd += ["--zoom", zoom_region]

    # --- Confirmação ---
    print("\n" + "=" * 45)
    print("🚀 Comando que será executado:")
    print("   " + " ".join(cmd))
    print("=" * 45)

    go = ask_choice("Confirmar e executar?", ["s", "n"], "s")
    if go != "s":
        print("Cancelado.")
        sys.exit(0)

    print()
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
