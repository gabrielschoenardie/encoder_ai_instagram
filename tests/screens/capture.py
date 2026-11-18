"""Captura a TUI real (python -m ui.tui) via ConPTY + emulador VT.

Ferramenta manual de desenvolvimento, só Windows. Dependências de dev, fora do
requirements: `pip install pyte pywinpty` no venv do projeto. Não é coletada
pelo pytest (nome não começa com test_).

Uso: python tests/screens/capture.py WxH out.txt [passos...]
passos: down up left right enter esc tab space bs
        ctrlc              CTRL_C_EVENT no console do filho (AttachConsole)
        text:<str>         digita literalmente
        wait:<s>           espera s segundos
        until:<texto>[@s]  espera o texto aparecer na tela (padrão 120 s)
        resize:WxH         redimensiona o terminal
        snap:<nome>        grava a tela em <out sem .txt>__<nome>.txt
"""
import os
import sys
import time

try:
    import pyte
    from winpty import PtyProcess
except ImportError:
    sys.exit("capture.py requer pyte e pywinpty (pip install pyte pywinpty) — só dev, Windows")

KEYS = {"down": "\x1b[B", "up": "\x1b[A", "right": "\x1b[C", "left": "\x1b[D",
        "enter": "\r", "esc": "\x1b", "tab": "\t", "space": " ", "bs": "\x7f", "ctrlc": "\x03"}
CTRL_C_HELPER = (
    "import ctypes,sys;k=ctypes.windll.kernel32;k.FreeConsole();"
    "ok=k.AttachConsole(int(sys.argv[1]));k.SetConsoleCtrlHandler(None,1);"
    "r=k.GenerateConsoleCtrlEvent(0,0);sys.exit(0 if ok and r else 1)"
)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    w, h = map(int, sys.argv[1].split("x"))
    out = sys.argv[2]
    stem = out[:-4] if out.endswith(".txt") else out
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8")
    py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
    proc = PtyProcess.spawn([py, "-m", "ui.tui"], cwd=ROOT, env=env, dimensions=(h, w))
    screen = pyte.Screen(w, h)
    stream = pyte.Stream(screen)
    steps = []

    def pump(sec, until=None):
        end = time.time() + sec
        while time.time() < end:
            if until is not None and until in "\n".join(screen.display):
                return True
            try:
                data = proc.read(65536) if proc.isalive() else ""
            except EOFError:
                return until is None
            if data:
                stream.feed(data)
                continue
            if not proc.isalive():
                return until is None or until in "\n".join(screen.display)
            time.sleep(0.05)
        return until is None

    def write(path, note=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {screen.columns}x{screen.lines} steps={' '.join(steps)} alive={proc.isalive()}{note}\n")
            f.write("\n".join(line.rstrip() for line in screen.display).rstrip("\n") + "\n")

    pump(4)
    for k in sys.argv[3:]:
        steps.append(k)
        if k.startswith("wait:"):
            pump(float(k[5:]))
        elif k.startswith("until:"):
            text, _, sec = k[6:].partition("@")
            if not pump(float(sec or 120), until=text):
                write(f"{stem}__TIMEOUT.txt", f" timeout={text!r}")
                print(f"TIMEOUT esperando {text!r}", file=sys.stderr)
                break
        elif k.startswith("resize:"):
            nw, nh = map(int, k[7:].split("x"))
            proc.setwinsize(nh, nw)
            screen.resize(nh, nw)
            pump(1.5)
        elif k == "ctrlc":
            import subprocess
            rc = subprocess.call([sys.executable, "-c", CTRL_C_HELPER, str(proc.pid)],
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            steps[-1] = f"ctrlc(rc={rc})"
            pump(0.8)
        elif k.startswith("snap:"):
            pump(0.3)
            write(f"{stem}__{k[5:]}.txt")
        elif k.startswith("text:"):
            if proc.isalive():
                proc.write(k[5:])
            pump(0.5)
        else:
            if not proc.isalive():
                break
            proc.write(KEYS[k])
            pump(0.8)
    pump(1)
    write(out)
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(screen.display))
    if proc.isalive():
        proc.terminate(force=True)


if __name__ == "__main__":
    main()
