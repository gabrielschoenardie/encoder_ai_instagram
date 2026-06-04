# ── enhance/sampler.py — Intelligent Frame Sampling ───────────────────
# FASE 27A: SampledFrame dataclass + sample_frames implementation
#
# Diferença do deband/frame_sampler.py:
#   - deband/ usa FFmpeg subprocess → PNG → disco
#   - enhance/ usa PyAV seek → float32 numpy → memória
#   - Retorna frames prontos para análise (float32 [0.0-1.0] RGB)
#   - Evita I/O de disco — mais eficiente para análise per-frame
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

try:
    import av
    _AV_AVAILABLE = True
except ImportError:
    _AV_AVAILABLE = False


@dataclass
class SampledFrame:
    """Frame amostrado com metadados para análise.

    Atributos:
        index:     Posição (número do frame) no vídeo.
        timestamp: Posição em segundos.
        data:      Pixels float32 [0.0-1.0] RGB, shape (H, W, 3).
        shape:     Tupla (H, W, C) por conveniência.
    """

    index: int
    timestamp: float
    data: np.ndarray        # float32 [0.0-1.0] RGB
    shape: Tuple[int, int, int]


def sample_frames(
    input_file: str,
    n_frames: int = 5,
    skip_edges: float = 0.05,
) -> List[SampledFrame]:
    """Amostra N frames representativos do vídeo via PyAV seek.

    Frames são distribuídos uniformemente entre *skip_edges* e
    (1 - skip_edges) da duração total, evitando artefatos de
    início/fim (fades, black frames, slates).

    Args:
        input_file:  Caminho do vídeo fonte.
        n_frames:    Número de frames a amostrar (default: 5).
        skip_edges:  Fração do início/fim a pular (default: 5%).

    Returns:
        Lista de SampledFrame em ordem temporal.

    Raises:
        RuntimeError: Se PyAV não estiver disponível ou a leitura falhar.
    """
    if not _AV_AVAILABLE:
        raise RuntimeError(
            "PyAV não disponível. Instale com: pip install av"
        )

    container = av.open(input_file)
    stream = container.streams.video[0]

    # ── Calcular duração ─────────────────────────────────────────────
    if stream.duration and stream.time_base:
        duration = float(stream.duration * stream.time_base)
    elif container.duration:
        duration = float(container.duration) / av.time_base
    else:
        raise RuntimeError(
            f"Não foi possível determinar duração de: {input_file}"
        )

    if duration <= 0.0:
        raise RuntimeError(
            f"Duração inválida ({duration:.2f}s) para: {input_file}"
        )

    # ── Calcular posições de amostragem ──────────────────────────────
    t_start = duration * skip_edges
    t_end = duration * (1.0 - skip_edges)
    if n_frames == 1:
        positions = [duration * 0.5]
    else:
        step = (t_end - t_start) / (n_frames - 1)
        positions = [t_start + i * step for i in range(n_frames)]

    # ── Seek + decode cada posição ───────────────────────────────────
    sampled: List[SampledFrame] = []

    for target_ts in positions:
        # PyAV seek em microsegundos no container
        seek_ts = int(target_ts / stream.time_base)
        container.seek(seek_ts, stream=stream)

        frame_decoded = None
        for frame in container.decode(video=0):
            frame_decoded = frame
            break  # Primeiro frame após seek

        if frame_decoded is None:
            continue  # Pular se seek falhou (edge case raro)

        # Converter para RGB float32 [0.0-1.0]
        rgb = frame_decoded.to_ndarray(format="rgb24")
        rgb_float = rgb.astype(np.float32) / 255.0

        actual_ts = float(frame_decoded.pts * stream.time_base) if frame_decoded.pts is not None else target_ts

        sampled.append(
            SampledFrame(
                index=len(sampled),
                timestamp=actual_ts,
                data=rgb_float,
                shape=rgb_float.shape,
            )
        )

    container.close()

    if not sampled:
        raise RuntimeError(
            f"Nenhum frame amostrado de: {input_file}"
        )

    return sampled
