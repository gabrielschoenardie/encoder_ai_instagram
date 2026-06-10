#!/usr/bin/env python3
# pylint: disable=bare-except,multiple-statements,too-many-branches,too-many-statements,unused-import
"""
🎬 Frame Comparison Tool v2 - Windows Compatible

Gera comparações side-by-side entre vídeo original e encodado.
Versão corrigida: sem drawtext (evita erro Fontconfig no Windows)

Uso:
    python compare_frames_v2.py original.mp4 encoded.mp4 --frames 121 261
    python compare_frames_v2.py original.mp4 encoded.mp4 --timestamps 4.0 8.68 --fps 30
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    _PILLOW = True
except ImportError:
    _PILLOW = False


def add_label_bar(img_path: str, label: str, color: tuple) -> None:
    """Sobrepõe um badge semitransparente no canto inferior-esquerdo da imagem."""
    if not _PILLOW:
        return

    img = Image.open(img_path).convert("RGBA")
    w, h = img.size

    font_size = max(16, h // 30)
    font = None
    for font_path in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                pass

    # Medir texto
    dummy = ImageDraw.Draw(img)
    if font:
        bbox = dummy.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        tw, th = len(label) * 7, 12

    pad = int(font_size * 0.55)
    accent = 5                          # largura da barra colorida à esquerda
    badge_w = tw + pad * 2 + accent
    badge_h = th + pad * 2
    margin = int(h * 0.025)            # distância da borda

    bx = margin
    by = h - badge_h - margin

    # Camada do badge (fundo escuro semitransparente)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Fundo arredondado escuro
    od.rounded_rectangle(
        [bx, by, bx + badge_w, by + badge_h],
        radius=6,
        fill=(10, 10, 10, 175),
    )
    # Acento colorido à esquerda
    od.rounded_rectangle(
        [bx, by, bx + accent, by + badge_h],
        radius=4,
        fill=(*color, 230),
    )

    img = Image.alpha_composite(img, overlay)
    td = ImageDraw.Draw(img)

    # Sombra sutil do texto
    td.text((bx + accent + pad + 1, by + pad + 1), label,
            fill=(0, 0, 0, 120), font=font)
    # Texto branco
    td.text((bx + accent + pad, by + pad), label,
            fill=(255, 255, 255, 245), font=font)

    img.convert("RGB").save(img_path)


def run_ffmpeg(cmd: list, description: str = "") -> bool:
    """Executa comando FFmpeg com tratamento de erro."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode != 0:
            print(f"  ❌ Erro: {description}")
            # Mostrar apenas últimas linhas do erro
            if result.stderr:
                lines = result.stderr.strip().split('\n')
                for line in lines[-3:]:
                    if line.strip():
                        print(f"     {line}")
            return False
        return True
    except Exception as e:
        print(f"  ❌ Exceção: {e}")
        return False


def extract_frame_by_number(video_path: str, frame_num: int, output_path: str) -> bool:
    """Extrai frame específico por número."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"select=eq(n\\,{frame_num})",
        "-frames:v", "1",
        "-q:v", "1",
        output_path
    ]
    return run_ffmpeg(cmd, f"extrair frame {frame_num}")


def extract_frame_by_timestamp(video_path: str, timestamp: float, output_path: str) -> bool:
    """Extrai frame por timestamp (seek rápido)."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "1",
        output_path
    ]
    return run_ffmpeg(cmd, f"extrair frame @ {timestamp}s")


def create_hstack(img1: str, img2: str, output: str) -> bool:
    """Cria imagem side-by-side horizontal, normalizando alturas se necessário."""
    filter_str = "[0:v][1:v]hstack=inputs=2"
    if _PILLOW:
        try:
            with Image.open(img1) as a, Image.open(img2) as b:
                if a.height != b.height:
                    h = max(a.height, b.height)
                    filter_str = (
                        f"[0:v]scale=-2:{h}[v0];"
                        f"[1:v]scale=-2:{h}[v1];"
                        f"[v0][v1]hstack=inputs=2"
                    )
        except Exception:
            pass
    cmd = [
        "ffmpeg", "-y",
        "-i", img1,
        "-i", img2,
        "-filter_complex", filter_str,
        "-q:v", "1",
        output
    ]
    return run_ffmpeg(cmd, "criar hstack")


def create_vstack(img1: str, img2: str, output: str) -> bool:
    """Cria imagem empilhada vertical."""
    cmd = [
        "ffmpeg", "-y",
        "-i", img1,
        "-i", img2,
        "-filter_complex", "[0:v][1:v]vstack=inputs=2",
        "-q:v", "1",
        output
    ]
    return run_ffmpeg(cmd, "criar vstack")


def create_difference(img1: str, img2: str, output: str) -> bool:
    """Cria mapa de diferenças, normalizando dimensões se necessário."""
    blend = "blend=all_mode=difference,eq=brightness=0.15:contrast=2.5"
    filter_str = f"[0:v][1:v]{blend}"
    if _PILLOW:
        try:
            with Image.open(img1) as a, Image.open(img2) as b:
                if a.size != b.size:
                    w, h = max(a.width, b.width), max(a.height, b.height)
                    filter_str = (
                        f"[0:v]scale={w}:{h}[v0];"
                        f"[1:v]scale={w}:{h}[v1];"
                        f"[v0][v1]{blend}"
                    )
        except Exception:
            pass
    cmd = [
        "ffmpeg", "-y",
        "-i", img1,
        "-i", img2,
        "-filter_complex", filter_str,
        "-q:v", "1",
        output
    ]
    return run_ffmpeg(cmd, "criar difference map")


def create_triple(img_orig: str, img_enc: str, img_diff: str, output: str) -> bool:
    """Cria comparação tripla: Original | Encoded | Difference."""
    cmd = [
        "ffmpeg", "-y",
        "-i", img_orig,
        "-i", img_enc,
        "-i", img_diff,
        "-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3",
        "-q:v", "1",
        output
    ]
    return run_ffmpeg(cmd, "criar triple comparison")


def create_zoom_crop(video_path: str, frame_num: int, output: str,
                     crop_x: int, crop_y: int, crop_w: int, crop_h: int,
                     zoom: int = 2) -> bool:
    """Extrai frame com crop e zoom."""
    # neighbor = nearest neighbor (preserva pixels sem interpolação)
    vf = f"select=eq(n\\,{frame_num}),crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=iw*{zoom}:ih*{zoom}:flags=neighbor"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "1",
        output
    ]
    return run_ffmpeg(cmd, f"extrair zoom frame {frame_num}")


def get_video_info(video_path: str) -> dict:
    """Obtém informações do vídeo (fps, frames, duração)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,r_frame_rate,duration",
        "-of", "csv=p=0",
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        parts = result.stdout.strip().split(',')

        # Parse frame rate (pode ser "30/1" ou "30000/1001")
        fps_str = parts[0] if len(parts) > 0 else "30/1"
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)

        nb_frames = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        duration = float(parts[2]) if len(parts) > 2 else 0

        return {"fps": fps, "frames": nb_frames, "duration": duration}
    except:
        return {"fps": 30.0, "frames": 0, "duration": 0}


def timestamp_to_frame(timestamp: float, fps: float) -> int:
    """Converte timestamp para número de frame."""
    return int(round(timestamp * fps))


def frame_to_timestamp(frame: int, fps: float) -> float:
    """Converte número de frame para timestamp."""
    return frame / fps


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Comparação Frame-by-Frame (Windows Compatible)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Por número de frame
  python compare_frames_v2.py original.mp4 encoded.mp4 --frames 121 261

  # Por timestamp (converte para frame automaticamente)
  python compare_frames_v2.py original.mp4 encoded.mp4 --timestamps 4.0 8.68

  # Com zoom na região lateral esquerda
  python compare_frames_v2.py original.mp4 encoded.mp4 --frames 121 --zoom 0,400,500,700

  # Todas as comparações
  python compare_frames_v2.py original.mp4 encoded.mp4 --frames 121 261 --all
        """
    )

    parser.add_argument("original", help="Vídeo original")
    parser.add_argument("encoded", help="Vídeo encodado")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--frames", "-f", nargs="+", type=int,
                       help="Números dos frames (ex: 121 261)")
    group.add_argument("--timestamps", "-t", nargs="+", type=float,
                       help="Timestamps em segundos (ex: 4.0 8.68)")

    parser.add_argument("-o", "--output-dir", default="compare_encodes",
                        help="Diretório de saída (default: compare_encodes)")
    parser.add_argument("--layout", choices=["horizontal", "vertical"],
                        default="horizontal", help="Layout da comparação")
    parser.add_argument("--diff", action="store_true",
                        help="Gerar mapa de diferenças")
    parser.add_argument("--triple", action="store_true",
                        help="Gerar comparação tripla")
    parser.add_argument("--zoom", type=str, default=None,
                        help="Região para zoom: x,y,w,h (ex: 0,400,500,700)")
    parser.add_argument("--all", action="store_true",
                        help="Gerar todas as comparações")
    parser.add_argument("--fps", type=float, default=None,
                        help="FPS do vídeo (auto-detecta se não especificado)")

    args = parser.parse_args()

    # Validar arquivos
    if not os.path.exists(args.original):
        print(f"❌ Arquivo não encontrado: {args.original}")
        sys.exit(1)
    if not os.path.exists(args.encoded):
        print(f"❌ Arquivo não encontrado: {args.encoded}")
        sys.exit(1)

    # Criar diretório de saída
    os.makedirs(args.output_dir, exist_ok=True)

    # Obter info do vídeo
    info = get_video_info(args.original)
    fps = args.fps if args.fps else info["fps"]

    print(f"\n🎬 Frame Comparison Tool v2")
    print(f"{'='*50}")
    print(f"📁 Original: {args.original}")
    print(f"📁 Encoded:  {args.encoded}")
    print(f"🎞️  FPS: {fps:.3f}")

    # Determinar frames a processar
    if args.frames:
        frames = args.frames
        print(f"🖼️  Frames: {frames}")
    else:
        frames = [timestamp_to_frame(ts, fps) for ts in args.timestamps]
        print(f"⏱️  Timestamps: {args.timestamps}")
        print(f"🖼️  Frames (calculados): {frames}")

    print(f"📂 Output: {args.output_dir}/")
    print(f"{'='*50}")

    # Processar cada frame
    for frame_num in frames:
        ts = frame_to_timestamp(frame_num, fps)
        print(f"\n⏱️  Frame {frame_num} ({ts:.3f}s)...")

        # Nomes dos arquivos
        prefix = f"f{frame_num}"
        orig_png = os.path.join(args.output_dir, f"_orig_{prefix}.png")
        enc_png = os.path.join(args.output_dir, f"_enc_{prefix}.png")

        # Extrair frames
        print(f"  📸 Extraindo frames...")
        if not extract_frame_by_number(args.original, frame_num, orig_png):
            print(f"  ⚠️  Falha ao extrair original, tentando por timestamp...")
            extract_frame_by_timestamp(args.original, ts, orig_png)

        if not extract_frame_by_number(args.encoded, frame_num, enc_png):
            print(f"  ⚠️  Falha ao extrair encoded, tentando por timestamp...")
            extract_frame_by_timestamp(args.encoded, ts, enc_png)

        # Verificar se extraiu
        if not os.path.exists(orig_png) or not os.path.exists(enc_png):
            print(f"  ❌ Falha ao extrair frames, pulando...")
            continue

        # Adicionar labels ANTES / DEPOIS
        if _PILLOW:
            print(f"  🏷️  Adicionando labels...")
            add_label_bar(orig_png, "ANTES",  color=(34, 139, 60))
            add_label_bar(enc_png,  "DEPOIS", color=(210, 90, 20))
        else:
            print(f"  ⚠️  Pillow não instalado — labels ignorados (pip install pillow)")

        # Comparação básica
        output_compare = os.path.join(args.output_dir, f"compare_{prefix}.png")
        print(f"  🖼️  Criando comparação...")
        if args.layout == "horizontal":
            create_hstack(orig_png, enc_png, output_compare)
        else:
            create_vstack(orig_png, enc_png, output_compare)

        if os.path.exists(output_compare):
            size = os.path.getsize(output_compare) // 1024
            print(f"  ✅ {output_compare} ({size} KB)")

        # Mapa de diferenças
        if args.diff or args.triple or args.all:
            diff_png = os.path.join(args.output_dir, f"_diff_{prefix}.png")
            output_diff = os.path.join(args.output_dir, f"diff_{prefix}.png")
            print(f"  🔍 Criando mapa de diferenças...")
            create_difference(orig_png, enc_png, diff_png)

            if os.path.exists(diff_png):
                # Copiar como jpg
                subprocess.run([
                    "ffmpeg", "-y", "-i", diff_png, "-q:v", "1", output_diff
                ], capture_output=True)
                print(f"  ✅ {output_diff}")

        # Comparação tripla
        if args.triple or args.all:
            diff_png = os.path.join(args.output_dir, f"_diff_{prefix}.png")
            if not os.path.exists(diff_png):
                create_difference(orig_png, enc_png, diff_png)

            output_triple = os.path.join(args.output_dir, f"triple_{prefix}.png")
            print(f"  🔎 Criando comparação tripla...")
            create_triple(orig_png, enc_png, diff_png, output_triple)

            if os.path.exists(output_triple):
                print(f"  ✅ {output_triple}")

        # Zoom comparison
        if args.zoom or args.all:
            if args.zoom:
                try:
                    crop = tuple(map(int, args.zoom.split(",")))
                    cx, cy, cw, ch = crop
                except:
                    print(f"  ⚠️  Formato de zoom inválido, usando padrão")
                    cx, cy, cw, ch = 0, 400, 500, 700
            else:
                # Default: região lateral esquerda
                cx, cy, cw, ch = 0, 400, 500, 700

            zoom_orig = os.path.join(args.output_dir, f"_zoom_orig_{prefix}.png")
            zoom_enc = os.path.join(args.output_dir, f"_zoom_enc_{prefix}.png")
            output_zoom = os.path.join(args.output_dir, f"zoom_{prefix}.png")

            print(f"  🔎 Criando zoom (região {cx},{cy},{cw},{ch})...")
            create_zoom_crop(args.original, frame_num, zoom_orig, cx, cy, cw, ch, 2)
            create_zoom_crop(args.encoded, frame_num, zoom_enc, cx, cy, cw, ch, 2)

            if os.path.exists(zoom_orig) and os.path.exists(zoom_enc):
                create_hstack(zoom_orig, zoom_enc, output_zoom)
                if os.path.exists(output_zoom):
                    print(f"  ✅ {output_zoom}")

                # Limpar temporários de zoom
                for f in [zoom_orig, zoom_enc]:
                    try: os.remove(f)
                    except: pass

        # Limpar temporários principais
        for f in [orig_png, enc_png]:
            try: os.remove(f)
            except: pass

        # Limpar diff temporário
        diff_png = os.path.join(args.output_dir, f"_diff_{prefix}.png")
        try: os.remove(diff_png)
        except: pass

    # Resumo
    print(f"\n{'='*50}")
    print(f"✅ Comparações geradas em: {args.output_dir}/")

    # Listar arquivos gerados
    generated = [f for f in os.listdir(args.output_dir) if f.endswith('.png') and not f.startswith('_')]
    if generated:
        print(f"📊 Arquivos gerados ({len(generated)}):")
        for f in sorted(generated):
            size = os.path.getsize(os.path.join(args.output_dir, f)) // 1024
            print(f"   • {f} ({size} KB)")


if __name__ == "__main__":
    main()