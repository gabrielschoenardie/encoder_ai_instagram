from __future__ import annotations

import os
import subprocess
import sys

from rich.prompt import Prompt

from ui.prompts import ask_choice

TOOLS = [
    ("Verificador de instalação", [sys.executable, "tools/verificador_instalacao.py"]),
    ("Comparar frames (interativo)", [sys.executable, "tools/compare_frames_interactive.py"]),
    ("Timestamp → frame (interativo)", [sys.executable, "tools/time_to_frame_interactive.py"]),
    ("Limpar cache", [sys.executable, "tools/clean_cache.py"]),
]

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _flow_tools(con) -> None:
    labels = [name for name, _ in TOOLS] + ["Voltar"]
    while True:
        choice = ask_choice(con, "Ferramentas", labels, default=len(labels))
        if choice == len(labels):
            return
        name, cmd = TOOLS[choice - 1]
        con.print(f"[primary]Executando:[/primary] {name}…")
        try:
            subprocess.run(cmd, cwd=_REPO_ROOT)
        except Exception as exc:
            con.print(f"[err]Falha ao executar {name}:[/err] {exc}")
        Prompt.ask("[dim]Pressione Enter para continuar[/dim]", default="", console=con,
                   show_default=False)
