#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DE INSTALAÇÃO - Instagram Reels Encoder v2.0.0
Verifica se todas as dependências estão instaladas e o sistema está pronto
"""

import sys
import os
import subprocess
import platform
from pathlib import Path
from typing import Tuple, List, Dict

# ============================================================================
# CORES E SÍMBOLOS PARA TERMINAL (sem dependências externas)
# ============================================================================

class Colors:
    """Cores ANSI para terminal"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

CHECKMARK = f"{Colors.GREEN}✓{Colors.RESET}"
CROSS = f"{Colors.RED}✗{Colors.RESET}"
WARNING = f"{Colors.YELLOW}⚠{Colors.RESET}"
INFO = f"{Colors.CYAN}ℹ{Colors.RESET}"

# ============================================================================
# CLASSE VERIFICADORA
# ============================================================================

class VerificadorInstalacao:
    """Verifica se o ambiente está pronto para usar o Reels Encoder"""

    def __init__(self):
        self.project_path = Path.cwd()
        self.results = {
            "python": {},
            "modules": {},
            "ffmpeg": {},
            "files": {},
            "hardware": {},
            "summary": {}
        }
        self.errors = []
        self.warnings = []

    # ────────────────────────────────────────────────────────────────────────
    # VERIFICAÇÃO DE PYTHON
    # ────────────────────────────────────────────────────────────────────────

    def verificar_python(self):
        """Verifica versão do Python"""
        print(f"\n{Colors.BOLD}═══ PYTHON {Colors.RESET}")

        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"{CROSS} Python {version_str} - VERSÃO INSUFICIENTE (requer 3.8+)")
            self.errors.append(f"Python {version_str} é menor que 3.8")
            return False

        print(f"{CHECKMARK} Python {version_str}")
        print(f"   Executável: {sys.executable}")
        print(f"   Sistema: {platform.system()} {platform.release()}")
        self.results["python"]["version"] = version_str
        self.results["python"]["status"] = "OK"
        return True

    # ────────────────────────────────────────────────────────────────────────
    # VERIFICAÇÃO DE MÓDULOS PYTHON
    # ────────────────────────────────────────────────────────────────────────

    def verificar_modulos(self):
        """Verifica módulos Python necessários"""
        print(f"\n{Colors.BOLD}═══ MÓDULOS PYTHON {Colors.RESET}")

        modulos_obrigatorios = {
            "pymediainfo": "Leitura de metadados de vídeo",
            "av": "PyAV - Decodificação/Codificação",
            "numpy": "Cálculos numéricos",
            "PIL": "Processamento de imagens (Pillow)",
            "rich": "Interface de terminal colorida",
        }

        modulos_opcionais = {
            "psutil": "Monitoramento de hardware",
            "colour": "Colour Science (Cineon pipeline)",
            "cv2": "OpenCV - Análise de imagem",
        }

        self.results["modules"]["obrigatorios"] = {}
        self.results["modules"]["opcionais"] = {}

        # Verificar módulos obrigatórios
        print(f"\n{Colors.CYAN}Obrigatórios:{Colors.RESET}")
        for modulo, descricao in modulos_obrigatorios.items():
            if self._verificar_modulo(modulo):
                print(f"  {CHECKMARK} {modulo:20} - {descricao}")
                self.results["modules"]["obrigatorios"][modulo] = "OK"
            else:
                print(f"  {CROSS} {modulo:20} - {descricao} {Colors.RED}[INSTALAR]{Colors.RESET}")
                self.results["modules"]["obrigatorios"][modulo] = "FALTANDO"
                self.errors.append(f"Módulo '{modulo}' não instalado")

        # Verificar módulos opcionais
        print(f"\n{Colors.CYAN}Opcionais:{Colors.RESET}")
        for modulo, descricao in modulos_opcionais.items():
            if self._verificar_modulo(modulo):
                print(f"  {CHECKMARK} {modulo:20} - {descricao}")
                self.results["modules"]["opcionais"][modulo] = "OK"
            else:
                print(f"  {WARNING} {modulo:20} - {descricao} {Colors.YELLOW}[Opcional]{Colors.RESET}")
                self.results["modules"]["opcionais"][modulo] = "FALTANDO"
                self.warnings.append(f"Módulo opcional '{modulo}' não instalado")

    @staticmethod
    def _verificar_modulo(modulo: str) -> bool:
        """Tenta importar um módulo"""
        try:
            __import__(modulo)
            return True
        except ImportError:
            return False

    # ────────────────────────────────────────────────────────────────────────
    # VERIFICAÇÃO DO FFMPEG
    # ────────────────────────────────────────────────────────────────────────

    def verificar_ffmpeg(self):
        """Verifica se FFmpeg está instalado e disponível"""
        print(f"\n{Colors.BOLD}═══ FFMPEG {Colors.RESET}")

        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Extrair versão da primeira linha
                primeira_linha = result.stdout.split('\n')[0]
                print(f"{CHECKMARK} FFmpeg instalado")
                print(f"   {primeira_linha}")
                self.results["ffmpeg"]["status"] = "OK"
                return True
            else:
                print(f"{CROSS} FFmpeg encontrado mas com erro")
                self.errors.append("FFmpeg encontrado mas retornou erro")
                return False

        except FileNotFoundError:
            print(f"{CROSS} FFmpeg não encontrado no PATH")
            print(f"   {Colors.YELLOW}Solução: Instale FFmpeg de https://ffmpeg.org/download.html{Colors.RESET}")
            self.errors.append("FFmpeg não instalado ou não no PATH")
            self.results["ffmpeg"]["status"] = "FALTANDO"
            return False

        except subprocess.TimeoutExpired:
            print(f"{CROSS} FFmpeg timeout")
            self.errors.append("FFmpeg timeout")
            return False

    # ────────────────────────────────────────────────────────────────────────
    # VERIFICAÇÃO DE ARQUIVOS DO PROJETO
    # ────────────────────────────────────────────────────────────────────────

    def verificar_arquivos(self):
        """Verifica arquivos necessários do projeto"""
        print(f"\n{Colors.BOLD}═══ ARQUIVOS DO PROJETO {Colors.RESET}")

        arquivos_obrigatorios = [
            "Reels_Encoder_v2_FINAL.py",
            "cineon_pipeline.py",
            "requirements.txt",
            "enhance/",
            "enhance/__init__.py",
            "enhance/processor.py",
            "enhance/profile.py",
            "enhance/ffmpeg_filters.py",
        ]

        arquivos_opcionais = [
            "FilmLook_Portra400_SkinPriority_D65.cube",
            "HollywoodCinema_Ultimate_v6.7B_1.5IRE_Instagram8bit_NeutralShadows.cube",
            "MANUAL_INSTALACAO.txt",
            "compare_frames.py",
            "clean_cache.py",
        ]

        self.results["files"]["obrigatorios"] = {}
        self.results["files"]["opcionais"] = {}

        print(f"\n{Colors.CYAN}Obrigatórios:{Colors.RESET}")
        for arquivo in arquivos_obrigatorios:
            caminho = self.project_path / arquivo
            if caminho.exists():
                tipo = "[DIR]" if caminho.is_dir() else "[FILE]"
                print(f"  {CHECKMARK} {arquivo:50} {tipo}")
                self.results["files"]["obrigatorios"][arquivo] = "OK"
            else:
                print(f"  {CROSS} {arquivo:50} {Colors.RED}[FALTANDO]{Colors.RESET}")
                self.results["files"]["obrigatorios"][arquivo] = "FALTANDO"
                self.errors.append(f"Arquivo obrigatório '{arquivo}' não encontrado")

        print(f"\n{Colors.CYAN}Opcionais:{Colors.RESET}")
        for arquivo in arquivos_opcionais:
            caminho = self.project_path / arquivo
            if caminho.exists():
                print(f"  {CHECKMARK} {arquivo}")
                self.results["files"]["opcionais"][arquivo] = "OK"
            else:
                print(f"  {WARNING} {arquivo:50} {Colors.YELLOW}[Opcional]{Colors.RESET}")
                self.results["files"]["opcionais"][arquivo] = "FALTANDO"

    # ────────────────────────────────────────────────────────────────────────
    # VERIFICAÇÃO DE HARDWARE
    # ────────────────────────────────────────────────────────────────────────

    def verificar_hardware(self):
        """Verifica recursos de hardware"""
        print(f"\n{Colors.BOLD}═══ HARDWARE {Colors.RESET}")

        try:
            import psutil

            # CPU
            cpu_count = psutil.cpu_count(logical=False)
            cpu_threads = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()

            print(f"\n{Colors.CYAN}CPU:{Colors.RESET}")
            print(f"  Cores: {cpu_count}")
            print(f"  Threads: {cpu_threads}")
            if cpu_freq:
                print(f"  Frequência: {cpu_freq.current:.0f} MHz")

            self.results["hardware"]["cpu_cores"] = cpu_count
            self.results["hardware"]["cpu_threads"] = cpu_threads

            # RAM
            mem = psutil.virtual_memory()
            mem_total_gb = mem.total / (1024 ** 3)
            mem_available_gb = mem.available / (1024 ** 3)
            mem_percent = mem.percent

            print(f"\n{Colors.CYAN}MEMÓRIA:{Colors.RESET}")
            print(f"  Total: {mem_total_gb:.2f} GB")
            print(f"  Disponível: {mem_available_gb:.2f} GB")
            print(f"  Uso: {mem_percent:.1f}%")

            self.results["hardware"]["ram_total_gb"] = mem_total_gb
            self.results["hardware"]["ram_available_gb"] = mem_available_gb
            self.results["hardware"]["ram_percent"] = mem_percent

            # Recomendações
            print(f"\n{Colors.CYAN}RECOMENDAÇÕES:{Colors.RESET}")
            if cpu_count >= 4 and mem_total_gb >= 8:
                print(f"  {CHECKMARK} Hardware adequado para uso do encoder")
                self.results["hardware"]["status"] = "ADEQUADO"
            elif cpu_count >= 2 and mem_total_gb >= 4:
                print(f"  {WARNING} Hardware mínimo - use --preset fast")
                self.results["hardware"]["status"] = "MÍNIMO"
            else:
                print(f"  {CROSS} Hardware insuficiente")
                self.results["hardware"]["status"] = "INSUFICIENTE"
                self.warnings.append("Hardware abaixo do recomendado")

        except ImportError:
            print(f"{WARNING} psutil não instalado - não foi possível verificar hardware")
            print(f"   Instale com: pip install psutil")
            self.warnings.append("psutil não instalado para verificar hardware")

    # ────────────────────────────────────────────────────────────────────────
    # TESTE DE IMPORTAÇÃO DO PROJETO
    # ────────────────────────────────────────────────────────────────────────

    def testar_import_projeto(self):
        """Tenta importar o módulo do projeto"""
        print(f"\n{Colors.BOLD}═══ TESTE DE IMPORTAÇÃO DO PROJETO {Colors.RESET}")

        try:
            import Reels_Encoder_v2_FINAL
            print(f"{CHECKMARK} Projeto importado com sucesso")
            self.results["summary"]["projeto_import"] = "OK"
            return True
        except Exception as e:
            print(f"{CROSS} Erro ao importar projeto: {str(e)}")
            self.results["summary"]["projeto_import"] = "ERRO"
            self.errors.append(f"Erro de importação do projeto: {str(e)}")
            return False

    # ────────────────────────────────────────────────────────────────────────
    # RESUMO FINAL
    # ────────────────────────────────────────────────────────────────────────

    def gerar_resumo(self):
        """Gera relatório de resumo final"""
        print(f"\n{Colors.BOLD}{'═' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}═══ RESUMO FINAL {Colors.RESET}")
        print(f"{Colors.BOLD}{'═' * 80}{Colors.RESET}\n")

        # Status geral
        if not self.errors:
            status = f"{Colors.GREEN}{Colors.BOLD}✓ TUDO PRONTO!{Colors.RESET}"
            print(f"{status}")
            print(f"\n{Colors.GREEN}Você pode usar o encoder agora!{Colors.RESET}")
            print(f"\nComande para começar:")
            print(f"  {Colors.CYAN}python Reels_Encoder_v2_FINAL.py seu_video.mp4{Colors.RESET}")
            self.results["summary"]["status_geral"] = "PRONTO"
            return True
        else:
            status = f"{Colors.RED}{Colors.BOLD}✗ PROBLEMAS ENCONTRADOS{Colors.RESET}"
            print(f"{status}\n")

            if self.errors:
                print(f"{Colors.RED}Erros (CRÍTICO):{Colors.RESET}")
                for i, erro in enumerate(self.errors, 1):
                    print(f"  {i}. {erro}")

            if self.warnings:
                print(f"\n{Colors.YELLOW}Avisos (opcional):{Colors.RESET}")
                for i, aviso in enumerate(self.warnings, 1):
                    print(f"  {i}. {aviso}")

            print(f"\n{Colors.YELLOW}Ações recomendadas:{Colors.RESET}")
            print(f"  1. Instale todas as dependências: pip install -r requirements.txt")
            print(f"  2. Instale FFmpeg: https://ffmpeg.org/download.html")
            print(f"  3. Reinicie seu PC")
            print(f"  4. Execute este verificador novamente")

            self.results["summary"]["status_geral"] = "PROBLEMAS"
            return False

    # ────────────────────────────────────────────────────────────────────────
    # EXECUTAR TODAS AS VERIFICAÇÕES
    # ────────────────────────────────────────────────────────────────────────

    def executar(self) -> bool:
        """Executa todas as verificações"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}")
        print("╔════════════════════════════════════════════════════════════════════════════════╗")
        print("║     VERIFICADOR DE INSTALAÇÃO - Instagram Reels Encoder v2.0.0                 ║")
        print("║     Verifica se todas as dependências estão instaladas                         ║")
        print("╚════════════════════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")

        print(f"Projeto localizado em: {self.project_path}\n")

        # Executar verificações
        self.verificar_python()
        self.verificar_modulos()
        self.verificar_ffmpeg()
        self.verificar_arquivos()
        self.verificar_hardware()
        self.testar_import_projeto()

        # Gerar resumo
        resultado_final = self.gerar_resumo()

        print(f"\n{Colors.BOLD}{'═' * 80}{Colors.RESET}\n")

        return resultado_final


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    verificador = VerificadorInstalacao()
    sucesso = verificador.executar()

    # Sair com código apropriado
    sys.exit(0 if sucesso else 1)
