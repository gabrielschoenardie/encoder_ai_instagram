# pylint: disable=duplicate-code
"""
enhance_visualizer.py
=====================
Diagnóstico visual do pipeline enhance-ai.

Gera heatmaps JET mostrando ONDE cada operação foi aplicada em cada frame:

  frame_N_deband.png   — risco de banding  (onde deband age)
  frame_N_noise.png    — energia de ruído  (onde denoise age)
  frame_N_sharpen.png  — detalhe/contraste (onde sharpen age)
  frame_N_panel.png    — panel 2×2: original | deband | noise | sharpen

Legenda JET:
  🔵 Azul  → operação inativa (área limpa / sem artefato)
  🟢 Verde → intensidade moderada
  🔴 Verm. → operação ativa (área problemática / com detalhe)

Uso:
  python enhance_visualizer.py
  (edite VIDEO e SAMPLES abaixo)
"""

import os
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

# ── Configuração ──────────────────────────────────────────────────────────────
VIDEO   = "input.mp4"   # vídeo a analisar
SAMPLES = 5             # frames amostrados
OUT_DIR = "enhance_maps"  # pasta de saída

# ── Importa heatmap de banding do pipeline (sem duplicação) ──────────────────
try:
    from enhance.processor import _banding_heatmap
    _BANDING_FROM_PIPELINE = True
except ImportError:
    _BANDING_FROM_PIPELINE = False

# Kernel Laplaciano 3×3 (mesma que processor.py)
_LAPLACIAN_K = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)


# ── Amostragem de frames ──────────────────────────────────────────────────────

_SAMPLE_PCTS = (0.10, 0.25, 0.50, 0.75, 0.90)  # posições fixas na timeline

def sample_frames(video_path: str, samples: int = 5):
    """
    Extrai exatamente 5 frames representativos nas posições fixas da timeline:
    10% / 25% / 50% / 75% / 90% da duração total.
    O parâmetro 'samples' é ignorado — sempre usa os 5 percentis acima.
    Retorna lista de (posição_frame, frame_bgr).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total == 0:
        raise RuntimeError("Vídeo sem frames.")
    positions = [max(0, min(total - 1, int(total * pct))) for pct in _SAMPLE_PCTS]
    frames = []
    for p in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(p))
        ret, frame = cap.read()
        if ret:
            frames.append((int(p), frame))
    cap.release()
    return frames


# ── Conversão para luma float32 ───────────────────────────────────────────────

def to_luma(frame_bgr: np.ndarray) -> np.ndarray:
    """uint8 BGR → float32 [0,1] luma Rec.709."""
    rgb = frame_bgr[:, :, ::-1].astype(np.float32) / 255.0
    return (0.2126 * rgb[..., 0]
            + 0.7152 * rgb[..., 1]
            + 0.0722 * rgb[..., 2])


# ── Spatial maps ──────────────────────────────────────────────────────────────

def make_deband_map(luma: np.ndarray) -> np.ndarray:
    """
    Risco de banding por pixel — float32 [0,1].
    HIGH (vermelho) = zona com banding, deband age aqui.
    Reutiliza _banding_heatmap() do pipeline (mesma lógica usada no enhance).
    """
    if _BANDING_FROM_PIPELINE:
        return _banding_heatmap(luma)

    # Fallback caso import falhe
    luma_sm = gaussian_filter(luma, sigma=1.0)
    from scipy.ndimage import sobel, uniform_filter
    gx = sobel(luma_sm, axis=1)
    gy = sobel(luma_sm, axis=0)
    grad = np.hypot(gx, gy)
    luma_sq   = uniform_filter(luma_sm ** 2, size=7)
    luma_m    = uniform_filter(luma_sm,      size=7)
    local_std = np.sqrt(np.clip(luma_sq - luma_m ** 2, 0.0, None))
    p99_g = float(np.percentile(grad,      99)) + 1e-10
    p99_s = float(np.percentile(local_std, 99)) + 1e-10
    grad_n = np.clip(grad      / p99_g, 0.0, 1.0)
    std_n  = np.clip(local_std / p99_s, 0.0, 1.0)
    return (1.0 - np.clip(0.6 * grad_n + 0.4 * std_n, 0.0, 1.0)).astype(np.float32)


def make_noise_map(luma: np.ndarray) -> np.ndarray:
    """
    Energia de ruído por pixel — float32 [0,1].
    HIGH (vermelho) = zona ruidosa, denoise age aqui.
    Mesma abordagem do noise.py: |luma − LP(σ=1)| captura ruído + detalhe fino.
    """
    highpass = luma - gaussian_filter(luma, sigma=1.0)
    noise_e = np.abs(highpass)
    p99 = float(np.percentile(noise_e, 99)) + 1e-10
    return np.clip(noise_e / p99, 0.0, 1.0).astype(np.float32)


def make_sharpen_map(luma: np.ndarray) -> np.ndarray:
    """
    Contraste local / gate de sharpen por pixel — float32 [0,1].
    HIGH (vermelho) = zona com detalhe/borda, sharpen age aqui.
    Mesma lógica do contrast_gate em _apply_perceptual_sharpen().
    """
    blurred = gaussian_filter(luma, sigma=2.0)
    detail = luma - blurred
    contrast_gate = np.clip(np.abs(detail) / 0.02, 0.0, 1.0)
    return contrast_gate.astype(np.float32)


# ── Heatmap visual ────────────────────────────────────────────────────────────

def to_jet(arr: np.ndarray) -> np.ndarray:
    """float32 [0,1] → BGR uint8 com COLORMAP_JET (idêntico ao codec_lab_analyzer)."""
    u8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(u8, cv2.COLORMAP_JET)


def _save_gray_mask(arr: np.ndarray, path: str) -> None:
    """float32 [0,1] → grayscale uint8 PNG para uso direto no pipeline FFmpeg."""
    u8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(path, u8)


def compute_consensus_masks(
    video_path: str,
    samples: int = 5,
    out_dir: str = "enhance_maps",
    frames=None,
) -> dict:
    """
    Computa máscara espacial consenso (média temporal de N frames) para
    deband e sharpen. Salva como PNG grayscale para uso direto no
    filter_complex do FFmpeg via maskedmerge/alphamerge.

    Args:
        frames: lista de (pos, frame_bgr) já amostrados (opcional).
                Se None, amostra o vídeo internamente — útil para
                chamadas standalone. Passar frames evita a releitura
                do vídeo quando já amostrado em run_preflight().

    Retorna dict com paths das máscaras:
        {"deband": "/path/consensus_deband_mask.png",
         "sharpen": "/path/consensus_sharpen_mask.png"}
    ou {} se falhar.
    """
    try:
        os.makedirs(out_dir, exist_ok=True)
        if frames is None:
            frames = sample_frames(video_path, samples)
        if not frames:
            return {}

        deband_acc  = None
        sharpen_acc = None
        n = 0

        for _pos, frame_bgr in frames:
            luma = to_luma(frame_bgr)
            dm = make_deband_map(luma)
            sm = make_sharpen_map(luma)
            if deband_acc is None:
                deband_acc  = dm.astype(np.float64)
                sharpen_acc = sm.astype(np.float64)
            else:
                deband_acc  += dm
                sharpen_acc += sm
            n += 1

        if n == 0:
            return {}

        deband_avg  = (deband_acc  / n).astype(np.float32)
        sharpen_avg = (sharpen_acc / n).astype(np.float32)

        # Paths absolutos — FFmpeg roda com cwd=script_dir, caminhos relativos
        # poderiam não resolver dependendo de onde o script Python foi invocado.
        deband_path  = os.path.abspath(os.path.join(out_dir, "consensus_deband_mask.png"))
        sharpen_path = os.path.abspath(os.path.join(out_dir, "consensus_sharpen_mask.png"))

        _save_gray_mask(deband_avg,  deband_path)
        _save_gray_mask(sharpen_avg, sharpen_path)

        return {"deband": deband_path, "sharpen": sharpen_path}

    except Exception:
        return {}


# ── Panel 2×2 ─────────────────────────────────────────────────────────────────

def make_panel(
    frame_bgr: np.ndarray,
    deband_h: np.ndarray,
    noise_h: np.ndarray,
    sharpen_h: np.ndarray,
    frame_idx: int,
    frame_pos: int,
) -> np.ndarray:
    """
    Gera panel 2×2:
      ┌──────────┬──────────┐
      │ Original │  Deband  │
      ├──────────┼──────────┤
      │  Noise   │ Sharpen  │
      └──────────┴──────────┘
    """
    H, W = frame_bgr.shape[:2]
    # Normaliza tamanho de todos para (H, W)
    def _resize(img):
        return cv2.resize(img, (W, H), interpolation=cv2.INTER_LINEAR)

    orig   = _resize(frame_bgr)
    deb    = _resize(deband_h)
    noi    = _resize(noise_h)
    sha    = _resize(sharpen_h)

    font     = cv2.FONT_HERSHEY_SIMPLEX
    fs       = max(0.5, W / 1200)
    thick    = max(1, int(fs * 2))
    pad      = max(4, int(H * 0.025))
    txt_col  = (255, 255, 255)
    shd_col  = (0, 0, 0)

    def _label(img, text):
        out = img.copy()
        # sombra
        cv2.putText(out, text, (pad + 1, pad + 1 + int(fs * 22)),
                    font, fs, shd_col, thick + 1, cv2.LINE_AA)
        cv2.putText(out, text, (pad, pad + int(fs * 22)),
                    font, fs, txt_col, thick, cv2.LINE_AA)
        return out

    orig  = _label(orig,  f"Frame {frame_pos}  [original]")
    deb   = _label(deb,   "DEBAND  (vermelho = banding)")
    noi   = _label(noi,   "NOISE   (vermelho = ruidoso)")
    sha   = _label(sha,   "SHARPEN (vermelho = detalhe)")

    top    = np.hstack([orig, deb])
    bottom = np.hstack([noi, sha])
    return np.vstack([top, bottom])


# ── Preflight API (chamada pelo encoder) ──────────────────────────────────────

def run_preflight(
    video_path: str,
    samples: int = 3,
    out_dir: str = "enhance_maps",
) -> dict:
    """
    Gera heatmaps diagnósticos de deband/noise/sharpen para preflight visual
    e computa máscaras grayscale consenso para uso no pipeline FFmpeg seletivo.

    Chamada automaticamente pelo encoder quando --enhance-ai on é detectado.

    Retorna dict:
        {
            "out_dir": str,               # pasta com os panels JET
            "masks": {                    # máscaras grayscale para filter_complex
                "deband":  "/path/consensus_deband_mask.png",
                "sharpen": "/path/consensus_sharpen_mask.png",
            }
        }
    """
    os.makedirs(out_dir, exist_ok=True)
    frames = sample_frames(video_path, samples)
    for i, (pos, frame_bgr) in enumerate(frames):
        luma      = to_luma(frame_bgr)
        deband_h  = to_jet(make_deband_map(luma))
        noise_h   = to_jet(make_noise_map(luma))
        sharpen_h = to_jet(make_sharpen_map(luma))
        panel     = make_panel(frame_bgr, deband_h, noise_h, sharpen_h,
                               frame_idx=i + 1, frame_pos=pos)
        prefix = os.path.join(out_dir, f"frame_{i+1}")
        cv2.imwrite(f"{prefix}_deband.png",  deband_h)
        cv2.imwrite(f"{prefix}_noise.png",   noise_h)
        cv2.imwrite(f"{prefix}_sharpen.png", sharpen_h)
        cv2.imwrite(f"{prefix}_panel.png",   panel)

    masks = compute_consensus_masks(video_path, samples=samples, out_dir=out_dir,
                                    frames=frames)
    return {"out_dir": out_dir, "masks": masks}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Aceita vídeo opcionalmente como argumento CLI: python enhance_visualizer.py video.mp4
    video   = sys.argv[1] if len(sys.argv) > 1 else VIDEO
    out_dir = OUT_DIR

    os.makedirs(out_dir, exist_ok=True)

    print("=" * 60)
    print("  enhance_visualizer — Diagnóstico espacial do pipeline")
    print("=" * 60)
    print(f"  Vídeo   : {video}")
    print(f"  Samples : {SAMPLES}")
    print(f"  Saída   : {out_dir}/")
    print(f"  Banding : {'pipeline (enhance.processor)' if _BANDING_FROM_PIPELINE else 'fallback interno'}")
    print()

    frames = sample_frames(video, SAMPLES)
    print(f"  {len(frames)} frames amostrados\n")

    for i, (pos, frame_bgr) in enumerate(frames):
        luma = to_luma(frame_bgr)
        H, W = luma.shape

        deband_map  = make_deband_map(luma)
        noise_map   = make_noise_map(luma)
        sharpen_map = make_sharpen_map(luma)

        deband_h  = to_jet(deband_map)
        noise_h   = to_jet(noise_map)
        sharpen_h = to_jet(sharpen_map)

        panel = make_panel(frame_bgr, deband_h, noise_h, sharpen_h,
                           frame_idx=i + 1, frame_pos=pos)

        prefix = os.path.join(out_dir, f"frame_{i+1}")
        cv2.imwrite(f"{prefix}_deband.png",  deband_h)
        cv2.imwrite(f"{prefix}_noise.png",   noise_h)
        cv2.imwrite(f"{prefix}_sharpen.png", sharpen_h)
        cv2.imwrite(f"{prefix}_panel.png",   panel)

        avg_deband  = float(np.mean(deband_map))
        avg_noise   = float(np.mean(noise_map))
        avg_sharpen = float(np.mean(sharpen_map))

        # Diagnóstico
        if avg_deband > 0.55:
            deb_diag = "RISCO ALTO de banding"
        elif avg_deband > 0.35:
            deb_diag = "banding moderado"
        else:
            deb_diag = "limpo"

        if avg_noise > 0.45:
            noi_diag = "RUIDOSO"
        elif avg_noise > 0.25:
            noi_diag = "ruído leve"
        else:
            noi_diag = "limpo"

        if avg_sharpen > 0.40:
            sha_diag = "MUITO DETALHE — sharpen forte"
        elif avg_sharpen > 0.20:
            sha_diag = "detalhe moderado"
        else:
            sha_diag = "area plana — sharpen suave"

        print(f"Frame {pos}  [{W}x{H}]")
        print(f"  Deband  avg={avg_deband:.3f}  -> {deb_diag}")
        print(f"  Noise   avg={avg_noise:.3f}  -> {noi_diag}")
        print(f"  Sharpen avg={avg_sharpen:.3f}  -> {sha_diag}")
        print(f"  Salvo   : {prefix}_[deband|noise|sharpen|panel].png")
        print()

    print("=" * 60)
    print(f"  {len(frames) * 4} arquivos gerados em {out_dir}/")
    print()
    print("  Legenda JET:")
    print("  AZUL   = operação inativa (sem artefato)")
    print("  VERDE  = intensidade moderada")
    print("  VERM.  = operação ativa (problema / detalhe)")
    print("=" * 60)


# ── MCTF mask video generation (FASE 29A) ────────────────────────────────────

_MCTF_EMA_ALPHA      = 0.60   # peso do frame atual na blenda MCTF (α)
_MCTF_FLOW_SCALE     = 0.25   # optical flow a 1/4 resolução (performance)
_MCTF_SCENE_FLOW_THR = 2.0    # magnitude média de flow (px a 1/4 res) → scene cut
                               # equivale a ~8px na resolução original


def generate_mctf_mask_video(
    video_path: str,
    out_dir: str = "enhance_maps",
) -> dict:
    """
    Pré-processamento MCTF: gera vídeos de máscara temporalmente suavizados.

    Para cada frame do vídeo:
      1. Computa make_deband_map() (deband) e make_sharpen_map() (CAS)
      2. Calcula optical flow Farneback a 1/4 de resolução (performance)
      3. Se não é scene cut: warpa máscara anterior + blenda (MCTF)
      4. Escreve frame de máscara no vídeo de saída via FFmpeg pipe

    Cada vídeo de máscara de saída é H.264 lossless (-crf 0 -preset ultrafast)
    em yuv420p, sincronizado frame-a-frame com o vídeo de entrada — sem
    necessidade de -stream_loop no filter_complex FFmpeg.

    Args:
        video_path: Caminho para o vídeo de entrada.
        out_dir:    Diretório de saída para os vídeos de máscara (criado se necessário).

    Returns:
        {
            "deband":  "/path/mctf_deband_mask.mp4",
            "sharpen": "/path/mctf_sharpen_mask.mp4",
            "fps":     float,
            "frames":  int,
        }
        Retorna dict vazio {} se o vídeo não pôde ser aberto.
    """
    import subprocess
    from typing import Optional
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TimeRemainingColumn, TextColumn,
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {}

    fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w_s   = max(1, int(w * _MCTF_FLOW_SCALE))
    h_s   = max(1, int(h * _MCTF_FLOW_SCALE))

    os.makedirs(out_dir, exist_ok=True)
    deband_path  = os.path.abspath(os.path.join(out_dir, "mctf_deband_mask.mp4"))
    sharpen_path = os.path.abspath(os.path.join(out_dir, "mctf_sharpen_mask.mp4"))

    def _open_ffmpeg_writer(out_path: str) -> subprocess.Popen:
        """Abre subprocess FFmpeg para receber frames raw grayscale via stdin."""
        return subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-pix_fmt", "gray",
                "-video_size", f"{w}x{h}",
                "-r", str(fps),
                "-i", "pipe:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "0",
                "-preset", "ultrafast",
                out_path,
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    proc_d = _open_ffmpeg_writer(deband_path)
    proc_s = _open_ffmpeg_writer(sharpen_path)

    # Estado MCTF entre frames
    prev_luma_small: Optional[np.ndarray] = None  # (h_s, w_s) uint8
    prev_deband:     Optional[np.ndarray] = None  # (h, w) float32
    prev_sharpen:    Optional[np.ndarray] = None  # (h, w) float32

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]MCTF masks:[/cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} frames"),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("", total=total or None)

            while True:
                ret, frame_bgr = cap.read()
                if not ret:
                    break

                luma = to_luma(frame_bgr)            # float32 [0,1]

                # 1. Máscaras do frame atual (resolução original)
                curr_d = make_deband_map(luma)       # float32 [0,1]
                curr_s = make_sharpen_map(luma)      # float32 [0,1]

                # 2. Optical flow a 1/4 de resolução
                luma_u8    = (luma * 255.0).clip(0, 255).astype(np.uint8)
                luma_small = cv2.resize(luma_u8, (w_s, h_s), interpolation=cv2.INTER_AREA)

                if prev_luma_small is not None and prev_deband is not None:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_luma_small, luma_small, None,
                        pyr_scale=0.5, levels=3, winsize=13,
                        iterations=3, poly_n=5, poly_sigma=1.2,
                        flags=0,
                    )
                    flow_mag = float(np.mean(np.abs(flow)))

                    if flow_mag <= _MCTF_SCENE_FLOW_THR:
                        # Escala flow de 1/4 resolução para resolução original
                        flow_full  = cv2.resize(flow, (w, h), interpolation=cv2.INTER_LINEAR)
                        flow_full *= (1.0 / _MCTF_FLOW_SCALE)

                        # Mapa de coordenadas para cv2.remap
                        gx = np.arange(w, dtype=np.float32)
                        gy = np.arange(h, dtype=np.float32)
                        grid_x, grid_y = np.meshgrid(gx, gy)
                        map_x = np.clip(grid_x + flow_full[..., 0], 0.0, float(w - 1))
                        map_y = np.clip(grid_y + flow_full[..., 1], 0.0, float(h - 1))

                        # Warp da máscara anterior + blend MCTF
                        warped_d = cv2.remap(
                            prev_deband, map_x, map_y,
                            cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
                        )
                        warped_s = cv2.remap(
                            prev_sharpen, map_x, map_y,
                            cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE,
                        )
                        alpha = _MCTF_EMA_ALPHA
                        curr_d = np.clip(
                            alpha * curr_d + (1.0 - alpha) * warped_d, 0.0, 1.0,
                        ).astype(np.float32)
                        curr_s = np.clip(
                            alpha * curr_s + (1.0 - alpha) * warped_s, 0.0, 1.0,
                        ).astype(np.float32)
                    # else: scene cut → usa curr_d/curr_s sem blend

                # 3. Escreve frames no pipe FFmpeg (uint8 grayscale)
                proc_d.stdin.write((curr_d * 255.0).clip(0, 255).astype(np.uint8).tobytes())
                proc_s.stdin.write((curr_s * 255.0).clip(0, 255).astype(np.uint8).tobytes())

                # 4. Atualiza estado MCTF
                prev_luma_small = luma_small
                prev_deband     = curr_d
                prev_sharpen    = curr_s

                progress.update(task, advance=1)

    finally:
        cap.release()
        proc_d.stdin.close()
        proc_d.wait()
        proc_s.stdin.close()
        proc_s.wait()

    return {
        "deband":  deband_path,
        "sharpen": sharpen_path,
        "fps":     fps,
        "frames":  total,
    }


if __name__ == "__main__":
    main()