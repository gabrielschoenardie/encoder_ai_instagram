import os
import shutil
import subprocess
from pathlib import Path


def remove_path(path: Path):
    if path.exists():
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                print(f"🧹 Removido diretório: {path}")
            else:
                path.unlink(missing_ok=True)
                print(f"🧹 Removido arquivo: {path}")
        except Exception as e:
            print(f"⚠️ Erro ao remover {path}: {e}")


def clean_vscode_cache():
    print("\n🔹 Limpando cache do VS Code...")
    base = Path.home() / "AppData" / "Roaming" / "Code"

    for folder in ["Cache", "CachedData", "GPUCache"]:
        remove_path(base / folder)


def clean_vscode_workspace_storage():
    print("\n🔹 Limpando workspaceStorage do VS Code...")
    workspace = (
        Path.home()
        / "AppData"
        / "Roaming"
        / "Code"
        / "User"
        / "workspaceStorage"
    )
    remove_path(workspace)


def clean_pip_cache():
    print("\n🔹 Limpando cache do pip...")
    try:
        subprocess.run(
            ["pip", "cache", "purge"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("🧹 Cache do pip limpo")
    except Exception as e:
        print(f"⚠️ Erro ao limpar cache do pip: {e}")


def clean_python_bytecode(project_root: Path):
    print("\n🔹 Limpando __pycache__ e arquivos .pyc...")
    for path in project_root.rglob("__pycache__"):
        remove_path(path)

    for pyc in project_root.rglob("*.pyc"):
        remove_path(pyc)


def main():
    print("🚀 Iniciando limpeza de cache...\n")

    clean_vscode_cache()
    clean_vscode_workspace_storage()
    clean_pip_cache()
    clean_python_bytecode(Path.cwd())

    print("\n✅ Limpeza concluída com sucesso.")
    print("💡 Dica: Abra o VS Code e selecione novamente o interpretador Python.")


if __name__ == "__main__":
    main()
