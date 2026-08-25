# -*- coding: utf-8 -*-
"""AG4 — cobre AEF1 (--output-dir sem --batch) e AFF1 (pipeline_tag derivado
da LUT em uso, ver .claude/memory/FINDINGS.md § AEF1 e § AFF1).
"""

import contextlib
import io
import re
import sys

import Reels_Encoder_v2_FINAL as R  # noqa: E402


def _run_main_with_argv(args):
    old_argv = sys.argv
    sys.argv = ["Reels_Encoder_v2_FINAL.py"] + args
    try:
        R.main()
    finally:
        sys.argv = old_argv


def test_output_dir_without_batch_exits_with_usage_error(tmp_path):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            _run_main_with_argv(
                ["input.mp4", "--output-dir", str(tmp_path)]
            )
            raised = False
            code = None
        except SystemExit as exc:
            raised = True
            code = exc.code

    assert raised
    assert code == 2
    assert "--batch" in stderr.getvalue()


def test_output_dir_with_batch_does_not_trigger_usage_error(tmp_path, monkeypatch):
    # AIF1: main() checa ffmpeg/ffprobe antes de chegar na logica de parser
    # que este teste valida. O teste e sobre argparse, nao sobre ffmpeg —
    # neutraliza a checagem de dependencia em vez de exigir o binario real.
    monkeypatch.setattr(
        "ui.preflight.missing_ffmpeg_binaries", lambda *a, **kw: []
    )
    try:
        _run_main_with_argv(
            ["--batch", str(tmp_path), "--output-dir", str(tmp_path / "out")]
        )
        code = None
    except SystemExit as exc:
        code = exc.code

    # Pasta de batch vazia: segue até "Nenhum vídeo encontrado" (exit 0),
    # não até o parser.error() novo (exit 2).
    assert code == 0


def test_batch_without_output_dir_does_not_trigger_usage_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ui.preflight.missing_ffmpeg_binaries", lambda *a, **kw: []
    )
    try:
        _run_main_with_argv(["--batch", str(tmp_path)])
        code = None
    except SystemExit as exc:
        code = exc.code

    assert code == 0


def test_pipeline_tag_derives_from_hollywood_lut_filename():
    match = re.search(r"_v(\d+\.\d+[\w-]*)_", R._HOLLYWOOD_LUT_FILENAME)
    assert match is not None
    expected_tag = f"HollywoodLUT_v{match.group(1)}"

    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=False
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == expected_tag


def test_pipeline_tag_cineon_mode_untouched():
    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=True
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == "Cineon+Portra400"


def _extract_comment(metadata_args):
    for item in metadata_args:
        if item.startswith("comment="):
            return item[len("comment="):]
    raise AssertionError("comment= não encontrado em metadata_args")


def test_pipeline_tag_is_nolut_when_lut_disabled():
    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=False,
        lut_enabled=False,
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == "NoLUT"


def test_pipeline_tag_derives_from_lut_filename_when_lut_enabled_true():
    match = re.search(r"_v(\d+\.\d+[\w-]*)_", R._HOLLYWOOD_LUT_FILENAME)
    assert match is not None
    expected_tag = f"HollywoodLUT_v{match.group(1)}"

    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=False,
        lut_enabled=True,
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == expected_tag


def test_pipeline_tag_default_lut_enabled_matches_derived_tag():
    match = re.search(r"_v(\d+\.\d+[\w-]*)_", R._HOLLYWOOD_LUT_FILENAME)
    assert match is not None
    expected_tag = f"HollywoodLUT_v{match.group(1)}"

    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=False,
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == expected_tag


def test_pipeline_tag_cineon_mode_ignores_lut_enabled_false():
    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=True,
        lut_enabled=False,
    )
    comment = _extract_comment(metadata_args)
    actual_tag = comment.split(" VBV:")[0]

    assert actual_tag == "Cineon+Portra400"


def test_comment_format_crf_mode_with_nolut_tag():
    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="crf", cineon_mode=False,
        lut_enabled=False, vbv_maxrate_override=8000, vbv_bufsize_override=16000,
    )
    comment = _extract_comment(metadata_args)

    assert comment.startswith("NoLUT VBV:")
    assert " crf:18 " in comment
    assert "max:8000k" in comment
    assert "buf:16000k" in comment


def test_comment_format_2pass_mode_with_nolut_tag():
    metadata_args = R._build_metadata_args(
        duration=10.0, video_bitrate=5000, mode="2pass", cineon_mode=False,
        lut_enabled=False, vbv_maxrate_override=8000, vbv_bufsize_override=16000,
    )
    comment = _extract_comment(metadata_args)

    assert comment.startswith("NoLUT VBV:")
    assert "target:5000k" in comment
    assert "max:8000k" in comment
    assert "buf:16000k" in comment
