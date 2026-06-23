"""Testes para o strip de display matrix residual (caminho seletivo + rotação).

O filter_complex seletivo (multi-input) faz o autorotate dos pixels mas propaga
o display matrix do input 0 para o output → players re-rotacionam o frame já em pé.
O -vf global não sofre disso. A correção remuxa com -display_rotation 0 (stream-copy).

Empiricamente: -metadata rotate=0 e -map_metadata -1 NÃO removem o side data;
só o override -display_rotation 0 (opção de INPUT) funciona.
"""
import importlib

R = importlib.import_module("Reels_Encoder_v2_FINAL")


def test_derotate_cmd_uses_display_rotation_before_input():
    cmd = R._build_derotate_cmd("in.mp4", "in.mp4.tmp.mp4")
    assert "-display_rotation" in cmd
    dr = cmd.index("-display_rotation")
    assert cmd[dr + 1] == "0"
    # -display_rotation é opção de INPUT → precede o -i
    assert dr < cmd.index("-i")


def test_derotate_cmd_is_stream_copy():
    cmd = R._build_derotate_cmd("in.mp4", "tmp.mp4")
    c = cmd.index("-c")
    assert cmd[c + 1] == "copy"          # nada de reencode
    assert "-map" in cmd and cmd[cmd.index("-map") + 1] == "0"  # vídeo + áudio


def test_derotate_cmd_io_paths():
    cmd = R._build_derotate_cmd("in.mp4", "out.tmp.mp4")
    assert cmd[cmd.index("-i") + 1] == "in.mp4"
    assert cmd[-1] == "out.tmp.mp4"      # tmp é o destino


def test_derotate_cmd_faststart():
    cmd = R._build_derotate_cmd("in.mp4", "tmp.mp4")
    assert "+faststart" in cmd
