"""
ebu_meter.py
============
Post-encode EBU R128 quality-control mode.

Inspired by NapoleonWils0n/ffmpeg-rust-scripts `ebu-meter.rs`, whose whole
mechanism is a single FFplay `lavfi` graph driving the `ebur128` filter's
built-in video meter.

This module does two things, *after* an encode finishes:

  1. **Audit (always):** measure the final file's loudness with the canonical
     `ebur128` filter (Integrated LUFS-I, True Peak dBTP, Loudness Range LU) and
     report codec + sample rate, side by side with the original (ANTES/DEPOIS).
  2. **Visualize (opt-out):** open graphical FFplay EBU R128 meter windows for
     visual QC — one for the original, one for the final.

It never alters audio: loudnorm 2-pass remains the sole normalization path.
Every failure mode (no audio, unparseable summary, missing ffplay) degrades
gracefully and never fails the encode.

Pure builders/parsers (`build_*`, `parse_*`) are unit-tested in
`enhance/test_ebu_meter.py` without any subprocess.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Pure builders / parsers
# ──────────────────────────────────────────────────────────────────────────────

def build_ebur128_measure_cmd(input_file: str) -> list:
    """Pass de medição EBU R128 (não-destrutivo, sem encode).

    `ebur128=peak=true` garante que o True Peak apareça no bloco `Summary:`
    impresso no stderr ao final.
    """
    return [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i", input_file,
        "-af", "ebur128=peak=true",
        "-f", "null",
        "-",
    ]


def _to_float(raw: Optional[str]) -> Optional[float]:
    """Converte string numérica do summary para float, rejeitando inf/nan.

    Áudio silencioso reporta `-inf` — tratado como medição inutilizável (None).
    """
    if raw is None:
        return None
    try:
        val = float(raw)
    except (ValueError, TypeError):
        return None
    if math.isinf(val) or math.isnan(val):
        return None
    return val


# Aceita número decimal OU inf (com sinal). O inf é capturado para então ser
# rejeitado por _to_float — distingue "campo ausente" de "áudio silencioso".
_NUM = r"(-?inf|-?\d+(?:\.\d+)?)"

_RE_I = re.compile(r"\bI:\s*" + _NUM + r"\s*LUFS")
_RE_LRA = re.compile(r"\bLRA:\s*" + _NUM + r"\s*LU\b")
_RE_TP = re.compile(r"\bPeak:\s*" + _NUM + r"\s*dBFS")


def parse_ebur128_summary(stderr: str) -> Optional[dict]:
    """Extrai {'I', 'TP', 'LRA'} do bloco `Summary:` do filtro ebur128.

    Retorna None se faltar qualquer campo ou se a medição for inutilizável
    (silêncio → -inf). `LRA:` casa apenas o range global (não `LRA low/high:`),
    e `Peak:` casa o True Peak (a linha de cabeçalho é `True peak:`, minúscula).

    IMPORTANTE: o ebur128 emite linhas de progresso por frame
    (`... I: -70.0 LUFS ... LRA: 0.0 LU ...`) que `-nostats` NÃO suprime — no
    início (silêncio/intro) elas reportam o piso -70.0/0.0. Parseamos APENAS a
    partir do último `Summary:`, ignorando essas linhas; caso contrário um
    `.search` casaria o primeiro frame (t≈0) em vez do valor final.
    """
    if not stderr:
        return None

    sidx = stderr.rfind("Summary:")
    if sidx == -1:
        return None
    block = stderr[sidx:]

    m_i = _RE_I.search(block)
    m_lra = _RE_LRA.search(block)
    m_tp = _RE_TP.search(block)
    if not (m_i and m_lra and m_tp):
        return None

    i = _to_float(m_i.group(1))
    lra = _to_float(m_lra.group(1))
    tp = _to_float(m_tp.group(1))
    if i is None or lra is None or tp is None:
        return None

    return {"I": i, "TP": tp, "LRA": lra}


def _escape_lavfi_path(path: str) -> str:
    """Escapa um path para uso dentro de `amovie='...'` num filtergraph lavfi.

    Mesma regra do ebu-meter.rs: barra invertida dobrada, depois dois-pontos
    escapado (ordem importa). Ex.: `C:\\v\\a.mp4` → `C\\:\\\\v\\\\a.mp4`.
    """
    return path.replace("\\", "\\\\").replace(":", "\\:")


def build_ffplay_meter_args(
    input_file: str,
    target_i: float,
    title: str,
    geometry: Optional[dict] = None,
) -> list:
    """Argumentos do FFplay para o medidor EBU R128 gráfico (janela de QC).

    Reproduz o grafo do ebu-meter.rs:
        amovie='<path>',ebur128=video=1:meter=18:dualmono=true:target=<I>[out0][out1]
    `video=1` desenha o medidor broadcast; `meter=18` é a escala +18 LU.

    Se `geometry` for fornecido (dict com chaves opcionais `width`/`height`/
    `left`/`top`), as flags `-x`/`-y`/`-left`/`-top` do FFplay posicionam e
    dimensionam a janela — permitindo abrir as duas janelas lado a lado.
    """
    esc = _escape_lavfi_path(input_file)
    graph = (
        f"amovie='{esc}',"
        f"ebur128=video=1:meter=18:dualmono=true:target={target_i:g}"
        f"[out0][out1]"
    )
    geom_args: list = []
    if geometry:
        if geometry.get("width") is not None:
            geom_args += ["-x", str(int(geometry["width"]))]
        if geometry.get("height") is not None:
            geom_args += ["-y", str(int(geometry["height"]))]
        if geometry.get("left") is not None:
            geom_args += ["-left", str(int(geometry["left"]))]
        if geometry.get("top") is not None:
            geom_args += ["-top", str(int(geometry["top"]))]
    return [
        "ffplay",
        "-hide_banner",
        "-v", "error",
        "-window_title", title,
        *geom_args,
        "-f", "lavfi",
        "-i", graph,
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Impure runners
# ──────────────────────────────────────────────────────────────────────────────

def probe_audio_codec(input_file: str):
    """(codec_name, sample_rate) do primeiro stream de áudio, ou (None, None)."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,sample_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file,
            ],
            stderr=subprocess.PIPE,
        )
        lines = out.decode("utf-8", "ignore").strip().splitlines()
        codec = lines[0].strip() if len(lines) >= 1 and lines[0].strip() else None
        rate = lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None
        return codec, rate
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, IndexError):
        return None, None


def probe_video_info(input_file: str) -> dict:
    """Metadados de vídeo + container do primeiro stream de vídeo via ffprobe.

    Retorna um dict normalizado (chaves consumidas por ``build_video_checks``),
    ou ``{}`` se o ffprobe falhar / não houver stream de vídeo.
    """
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries",
                "stream=codec_name,profile,level,width,height,pix_fmt,"
                "color_primaries,color_transfer,color_space,r_frame_rate",
                "-show_entries", "format=format_name",
                "-of", "json",
                input_file,
            ],
            stderr=subprocess.PIPE,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return {}

    import json
    try:
        data = json.loads(out.decode("utf-8", "ignore") or "{}")
    except ValueError:
        return {}

    streams = data.get("streams") or []
    st = streams[0] if streams else {}
    fmt = data.get("format") or {}
    return {
        "container": fmt.get("format_name"),
        "codec": st.get("codec_name"),
        "profile": st.get("profile"),
        "level": st.get("level"),
        "width": st.get("width"),
        "height": st.get("height"),
        "pix_fmt": st.get("pix_fmt"),
        "color_primaries": st.get("color_primaries"),
        "color_transfer": st.get("color_transfer"),
        "color_space": st.get("color_space"),
        "fps": _parse_fps(st.get("r_frame_rate")),
    }


def measure_loudness(input_file: str) -> Optional[dict]:
    """Mede loudness EBU R128 do arquivo. Retorna {'I','TP','LRA'} ou None."""
    try:
        result = subprocess.run(
            build_ebur128_measure_cmd(input_file),
            capture_output=True, text=True, encoding="utf-8", errors="ignore",
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return parse_ebur128_summary(result.stderr or "")


def _get_screen_size() -> Optional[tuple]:
    """(largura, altura) da tela primária em px, ou None se indeterminável."""
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
            w, h = int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        if w > 0 and h > 0:
            return int(w), int(h)
    except Exception:
        pass
    return None


def compute_side_by_side_layout(n: int = 2, screen: Optional[tuple] = None) -> list:
    """Geometrias para `n` janelas lado a lado, centradas na tela.

    Retorna uma lista de dicts `{width,height,left,top}` (uma por janela). Se a
    resolução da tela não puder ser determinada, assume 1920×1080.
    """
    sw, sh = screen if screen else (_get_screen_size() or (1920, 1080))
    gap = 24
    # Cada janela ocupa metade da largura útil (92% da tela), com aspecto ~4:3,
    # limitada a 85% da altura da tela.
    win_w = max(320, (int(sw * 0.92) - gap * (n - 1)) // n)
    win_h = min(int(sh * 0.85), int(win_w * 3 / 4))
    total_w = win_w * n + gap * (n - 1)
    left0 = max(0, (sw - total_w) // 2)
    top = max(0, (sh - win_h) // 2)
    return [
        {"width": win_w, "height": win_h, "left": left0 + i * (win_w + gap), "top": top}
        for i in range(n)
    ]


def launch_meter_window(
    input_file: str,
    target_i: float,
    title: str,
    geometry: Optional[dict] = None,
) -> Optional[subprocess.Popen]:
    """Abre a janela FFplay do medidor (detached, não-bloqueante).

    Retorna o Popen, ou None se o ffplay não estiver disponível / falhar ao abrir.
    """
    if shutil.which("ffplay") is None:
        return None
    args = build_ffplay_meter_args(input_file, target_i, title, geometry=geometry)
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Desacopla o ffplay do processo pai para não bloquear o terminal.
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        return subprocess.Popen(args, **kwargs)
    except (FileNotFoundError, OSError):
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Orchestration + report
# ──────────────────────────────────────────────────────────────────────────────

def _fmt(value: Optional[float], suffix: str = "") -> str:
    return "—" if value is None else f"{value:.1f}{suffix}"


def _flag_integrated(measured: Optional[float], target_i: float, tol: float = 1.0) -> str:
    if measured is None:
        return ""
    return " ✓" if abs(measured - target_i) <= tol else " ⚠"


def _flag_true_peak(measured: Optional[float], target_tp: float) -> str:
    if measured is None:
        return ""
    return " ✓" if measured <= target_tp + 1e-9 else " ⚠"


def build_delivery_checks(aI, aTP, a_codec, a_rate, tgt_i, tgt_tp):
    """Return list[(label, value_str, passed|None)] certifying the final audio.

    Pure (rich-free): turns the post-encode audit's final-file metrics into the
    conformance rows the ``ui.components.delivery_seal`` card renders. ``passed``
    is ``None`` when its source metric is unavailable.
    """
    loud_val = f"{_fmt(aI)} LUFS" if aI is not None else "—"
    loud_pass = None if aI is None else abs(aI - tgt_i) <= 1.0

    tp_val = f"{_fmt(aTP)} dBTP" if aTP is not None else "—"
    tp_pass = None if aTP is None else aTP <= tgt_tp + 1e-9

    codec_val = a_codec or "—"
    codec_pass = None if not a_codec else a_codec.lower().startswith("aac")

    rate_val = str(a_rate) if a_rate else "—"
    rate_pass = None if not a_rate else str(a_rate) == "48000"

    return [
        ("Loudness", loud_val, loud_pass),
        ("True Peak", tp_val, tp_pass),
        ("Codec", codec_val, codec_pass),
        ("Sample Rate", rate_val, rate_pass),
    ]


def _parse_fps(raw: Optional[str]) -> Optional[float]:
    """Converte um frame rate do ffprobe ('30000/1001' ou '30') para float.

    Retorna None para entradas vazias, divisão por zero ou não-numéricas.
    """
    if not raw:
        return None
    try:
        if "/" in raw:
            num, den = raw.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else None
        return float(raw)
    except (ValueError, ZeroDivisionError):
        return None


def _bit_depth(pix_fmt: Optional[str]) -> Optional[int]:
    """Profundidade de bits inferida do pix_fmt (yuv420p→8, yuv420p10le→10)."""
    if not pix_fmt:
        return None
    p = pix_fmt.lower()
    if "10" in p:
        return 10
    if "12" in p:
        return 12
    return 8


# Map de codec_name (ffprobe) → rótulo de exibição.
_VCODEC_DISPLAY = {"h264": "H.264", "hevc": "HEVC", "vp9": "VP9", "av1": "AV1"}


def build_video_checks(info: dict) -> list:
    """Return list[(label, value_str, passed|None)] certifying CONTAINER + VIDEO.

    Pure (rich-free): turns the probed video/container metadata of the final
    file into the conformance rows the ``ui.components.delivery_seal`` card
    renders alongside the audio rows. ``passed`` is ``None`` when a field is
    unavailable or merely informational (e.g. a non-1080×1920 size produced by
    ``--fit contain`` is reported but not failed).
    """
    info = info or {}

    # CONTAINER
    container = info.get("container") or ""
    if not container:
        cont_val, cont_pass = "—", None
    else:
        cont_pass = "mp4" in container.lower()
        cont_val = "MP4" if cont_pass else container

    # VIDEO codec / profile / level
    codec = info.get("codec")
    if not codec:
        vid_val, vid_pass = "—", None
    else:
        disp = _VCODEC_DISPLAY.get(codec.lower(), codec.upper())
        profile = info.get("profile")
        level = info.get("level")
        label = disp
        if profile:
            label += f" {profile}"
        try:
            if level and int(level) > 0:
                label += f"@{int(level) / 10:.1f}"
        except (ValueError, TypeError):
            pass
        vid_val = label
        vid_pass = codec.lower() == "h264" and bool(profile) and "high" in profile.lower()

    # RESOLUTION (target 1080×1920; other sizes are informational, not failures)
    w, h = info.get("width"), info.get("height")
    if not (w and h):
        res_val, res_pass = "—", None
    else:
        res_val = f"{w}x{h}"
        res_pass = True if (int(w), int(h)) == (1080, 1920) else None

    # BIT DEPTH (Instagram delivery is 8-bit)
    bits = _bit_depth(info.get("pix_fmt"))
    if bits is None:
        bd_val, bd_pass = "—", None
    else:
        bd_val, bd_pass = f"{bits}-bit", (bits == 8)

    # COLOR (BT.709 across primaries / transfer / matrix)
    triplet = [
        info.get("color_primaries"),
        info.get("color_transfer"),
        info.get("color_space"),
    ]
    present = [v.lower() for v in triplet if v and v.lower() not in ("unknown", "reserved", "")]
    if not present:
        col_val, col_pass = "—", None
    elif all(v == "bt709" for v in present):
        col_val, col_pass = "BT.709", True
    else:
        col_pass = False
        col_val = next((v for v in triplet if v and v.lower() != "bt709"), "—")

    # FPS (broadcast-plausible 24–60)
    fps = info.get("fps")
    if fps is None:
        fps_val, fps_pass = "—", None
    else:
        fps_val = f"{fps:g} fps"
        fps_pass = 23.0 <= fps <= 60.5

    return [
        ("Container", cont_val, cont_pass),
        ("Video", vid_val, vid_pass),
        ("Resolution", res_val, res_pass),
        ("Bit Depth", bd_val, bd_pass),
        ("Color", col_val, col_pass),
        ("FPS", fps_val, fps_pass),
    ]


def run_post_encode_qc(
    original_file: str,
    output_file: str,
    target: str = "instagram",
    show_meter: bool = True,
    targets: Optional[dict] = None,
    console=None,
) -> None:
    """Auditoria EBU R128 pós-encode (sempre) + janelas FFplay (opcional).

    Args:
        original_file: entrada original (coluna ANTES).
        output_file:   arquivo final encodado (coluna DEPOIS).
        target:        chave de loudness ('instagram').
        show_meter:    abre as janelas FFplay de QC (forçado False em batch).
        targets:       dict de alvos {target: {'I','TP','LRA'}}; se None, importa
                       LOUDNORM_TARGETS do encoder.
        console:       Rich Console; se None, cria um.
    """
    # Console + tabela (import tardio p/ manter os builders puros sem rich)
    if console is None:
        from rich.console import Console
        console = Console()
    from rich.table import Table
    from rich import box

    if targets is None:
        try:
            from Reels_Encoder_v2_FINAL import LOUDNORM_TARGETS
            targets = LOUDNORM_TARGETS
        except Exception:
            targets = {"instagram": {"I": -14, "TP": -1.5, "LRA": 11}}
    t = targets.get(target, targets.get("instagram", {"I": -14, "TP": -1.5, "LRA": 11}))
    tgt_i = float(t.get("I", -14))
    tgt_tp = float(t.get("TP", -1.5))
    tgt_lra = t.get("LRA", 11)

    console.rule("[bold cyan]🎧 EBU R128 — Auditoria pós-encode")

    before = measure_loudness(original_file)
    after = measure_loudness(output_file)
    b_codec, b_rate = probe_audio_codec(original_file)
    a_codec, a_rate = probe_audio_codec(output_file)

    bI = before["I"] if before else None
    bTP = before["TP"] if before else None
    bLRA = before["LRA"] if before else None
    aI = after["I"] if after else None
    aTP = after["TP"] if after else None
    aLRA = after["LRA"] if after else None

    table = Table(box=box.ROUNDED, show_lines=False)
    table.add_column("Métrica", style="bold")
    table.add_column("ANTES (original)", justify="right")
    table.add_column("DEPOIS (final)", justify="right")
    table.add_column("Alvo", justify="right", style="dim")

    table.add_row(
        "Integrated (LUFS-I)",
        _fmt(bI) + _flag_integrated(bI, tgt_i),
        _fmt(aI) + _flag_integrated(aI, tgt_i),
        f"{tgt_i:g}",
    )
    table.add_row(
        "True Peak (dBTP)",
        _fmt(bTP) + _flag_true_peak(bTP, tgt_tp),
        _fmt(aTP) + _flag_true_peak(aTP, tgt_tp),
        f"≤ {tgt_tp:g}",
    )
    table.add_row(
        "Loudness Range (LU)",
        _fmt(bLRA), _fmt(aLRA), f"~{tgt_lra}",
    )
    table.add_row("Codec", b_codec or "—", a_codec or "—", "AAC-LC")
    table.add_row("Sample Rate (Hz)", b_rate or "—", a_rate or "—", "48000")

    console.print(table)

    # ── Delivery seal (Premiere-style QC certificate) ─────────────────────────
    # O selo certifica o master completo: CONTAINER/VIDEO (do arquivo final) +
    # ÁUDIO (loudness/codec da auditoria EBU acima).
    try:
        from ui.components import delivery_seal
        video_checks = build_video_checks(probe_video_info(output_file))
        audio_checks = build_delivery_checks(aI, aTP, a_codec, a_rate, tgt_i, tgt_tp)
        console.print(delivery_seal(video_checks + audio_checks, console=console))
    except Exception:
        pass

    if after is None:
        console.print(
            "[yellow]⚠ Não foi possível medir o áudio final "
            "(sem stream de áudio ou formato não suportado).[/yellow]"
        )

    # ── Janelas FFplay (QC visual) ────────────────────────────────────────────
    if not show_meter:
        return
    if shutil.which("ffplay") is None:
        console.print(
            "[yellow]⚠ ffplay não encontrado no PATH — pulando o monitor EBU R128 visual.[/yellow]"
        )
        return

    name = os.path.basename(output_file)
    has_original = os.path.exists(original_file)
    # Layout lado a lado, centrado na tela: ANTES à esquerda, DEPOIS à direita.
    layout = compute_side_by_side_layout(n=2 if has_original else 1)
    opened = 0
    if has_original:
        if launch_meter_window(
            original_file, tgt_i, f"EBU R128 — ANTES (original): {os.path.basename(original_file)}",
            geometry=layout[0],
        ):
            opened += 1
    if launch_meter_window(
        output_file, tgt_i, f"EBU R128 — DEPOIS (final): {name}",
        geometry=layout[-1],
    ):
        opened += 1

    if opened:
        console.print(
            f"[green]🎧 Monitor EBU R128 aberto ({opened} janela(s)) — "
            f"feche-as quando terminar a inspeção. (--ebu-meter off para desativar)[/green]"
        )
    else:
        console.print("[yellow]⚠ Não foi possível abrir as janelas do monitor EBU R128.[/yellow]")
