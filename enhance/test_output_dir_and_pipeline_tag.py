# -*- coding: utf-8 -*-
"""AG4 — cobre AEF1 (--output-dir sem --batch) e AFF1 (pipeline_tag derivado
da LUT em uso, ver .claude/memory/FINDINGS.md § AEF1 e § AFF1).

AT2 — cobre ALF1: caminho da UI passa pela mesma validação de args
(ver .claude/memory/PLAN.md § Ciclo AT).
"""

import contextlib
import io
import re

import Reels_Encoder_v2_FINAL as R  # noqa: E402
from ui.config import EncodeConfig  # noqa: E402


def test_output_dir_without_batch_exits_with_usage_error(tmp_path):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            R.parse_cli(["input.mp4", "--output-dir", str(tmp_path)])
            raised = False
            code = None
        except SystemExit as exc:
            raised = True
            code = exc.code

    assert raised
    assert code == 2
    assert "--batch" in stderr.getvalue()


def test_output_dir_with_batch_does_not_trigger_usage_error(tmp_path):
    out_dir = tmp_path / "out"

    args = R.parse_cli(
        ["--batch", str(tmp_path), "--output-dir", str(out_dir)]
    )

    assert args.batch == str(tmp_path)
    assert args.output_dir == str(out_dir)


def test_batch_without_output_dir_does_not_trigger_usage_error(tmp_path):
    args = R.parse_cli(["--batch", str(tmp_path)])

    assert args.batch == str(tmp_path)
    assert args.output_dir is None


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


# ─── AT2(a) — _validate_args_consistency devolve None para combinações válidas ──

def test_validate_args_consistency_none_for_input_only():
    args = R.parse_cli(["input.mp4"])
    assert R._validate_args_consistency(args) is None


def test_validate_args_consistency_none_for_batch_only(tmp_path):
    args = R.parse_cli(["--batch", str(tmp_path)])
    assert R._validate_args_consistency(args) is None


def test_validate_args_consistency_none_for_batch_with_output_dir(tmp_path):
    out_dir = tmp_path / "out"
    args = R.parse_cli(["--batch", str(tmp_path), "--output-dir", str(out_dir)])
    assert R._validate_args_consistency(args) is None


# ─── AT2(b) — _validate_args_consistency devolve msg para output_dir sem batch ──

def test_validate_args_consistency_msg_for_output_dir_without_batch(tmp_path):
    ns = EncodeConfig(input="x.mp4", output_dir=str(tmp_path), batch=None).to_namespace()
    msg = R._validate_args_consistency(ns)
    assert msg is not None
    assert "--batch" in msg


# ─── AT2(c) — teste-ponte: Namespace do launcher sujeito à mesma validação ──────

def test_validate_args_consistency_catches_launcher_namespace(tmp_path):
    ns = EncodeConfig(
        input="x.mp4", output_dir=str(tmp_path), batch=None
    ).to_namespace()

    msg = R._validate_args_consistency(ns)

    assert msg is not None
    assert "--batch" in msg


# ─── AT2(d) — teste de wiring: main() valida o Namespace vindo da UI ───────────

def test_main_exits_2_when_ui_namespace_is_inconsistent(monkeypatch):
    cli_ns = EncodeConfig(ui=True).to_namespace()
    monkeypatch.setattr(R, "parse_cli", lambda: cli_ns)

    import ui.preflight
    monkeypatch.setattr(ui.preflight, "missing_ffmpeg_binaries", lambda: [])

    invalid_ns = EncodeConfig(
        input="x.mp4", output_dir="/d", batch=None
    ).to_namespace()

    import ui.launcher
    monkeypatch.setattr(ui.launcher, "run_launcher", lambda console=None: invalid_ns)

    raised = False
    code = None
    try:
        R.main()
    except SystemExit as exc:
        raised = True
        code = exc.code

    assert raised
    assert code == 2
