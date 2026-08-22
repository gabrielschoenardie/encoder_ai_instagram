"""Testes do registro dos ffmpeg de fase de análise (ADF1, ciclo AI).

`terminate_active_ffmpeg()` só encerra o processo em `_ACTIVE_FFMPEG`. Os ffmpeg
de análise (de-rotação, loudnorm pass 1, remux do átomo `colr`) subiam por
`subprocess.run()` e nunca eram registrados — sobreviviam ao exit=130.

O ponto crítico: `_ACTIVE_FFMPEG` é um único global. O remux do `colr` roda
enquanto o processo principal do encode ainda está registrado; zerar o registro
ao sair deixaria o principal não-matável. Por isso `_run_ffmpeg_tracked` salva e
restaura o valor anterior num `finally`, nunca zera.
"""
import importlib
import inspect
import subprocess
import types

import pytest

R = importlib.import_module("Reels_Encoder_v2_FINAL")


def _fake_proc(returncode=0, out="", err="", on_communicate=None):
    """Processo falso: `communicate()` opcionalmente observa o estado global."""
    proc = types.SimpleNamespace(returncode=returncode, terminated=False, waited=False)

    def communicate():
        if on_communicate is not None:
            on_communicate(proc)
        return out, err

    def terminate():
        proc.terminated = True

    def wait(timeout=None):
        proc.waited = True
        return proc.returncode

    proc.communicate = communicate
    proc.terminate = terminate
    proc.wait = wait
    proc.poll = lambda: None
    return proc


def _fake_popen(proc, seen):
    def popen(cmd, **kwargs):
        seen.append((cmd, kwargs))
        return proc

    return popen


# --- AI2: _swap_active_ffmpeg -------------------------------------------------


def test_swap_returns_previous_and_installs_new():
    a, b = _fake_proc(), _fake_proc()
    R._register_ffmpeg(a)
    try:
        prev = R._swap_active_ffmpeg(b)
        assert prev is a
        assert R._ACTIVE_FFMPEG is b
    finally:
        R._register_ffmpeg(None)


def test_register_ffmpeg_contract_unchanged():
    a = _fake_proc()
    try:
        assert R._register_ffmpeg(a) is None
        assert R._ACTIVE_FFMPEG is a
        R._register_ffmpeg(None)
        assert R._ACTIVE_FFMPEG is None
    finally:
        R._register_ffmpeg(None)


# --- Critério 1: registrado durante a execução --------------------------------


def test_process_is_registered_during_communicate():
    observed = []
    proc = _fake_proc(on_communicate=lambda p: observed.append(R._ACTIVE_FFMPEG))
    R._run_ffmpeg_tracked(["ffmpeg"], popen=_fake_popen(proc, []))
    assert observed == [proc]


# --- Critério 2: restaura o anterior (assert central do ciclo) ----------------


def test_restores_previous_process_not_none():
    main_encode = _fake_proc()
    R._register_ffmpeg(main_encode)
    try:
        R._run_ffmpeg_tracked(["ffmpeg"], popen=_fake_popen(_fake_proc(), []))
        assert R._ACTIVE_FFMPEG is main_encode
    finally:
        R._register_ffmpeg(None)


def test_restores_none_when_nothing_was_registered():
    R._register_ffmpeg(None)
    R._run_ffmpeg_tracked(["ffmpeg"], popen=_fake_popen(_fake_proc(), []))
    assert R._ACTIVE_FFMPEG is None


# --- Critério 3: restaura também em falha e em check --------------------------


def test_restores_previous_when_command_fails():
    main_encode = _fake_proc()
    R._register_ffmpeg(main_encode)
    try:
        R._run_ffmpeg_tracked(["ffmpeg"], popen=_fake_popen(_fake_proc(returncode=1), []))
        assert R._ACTIVE_FFMPEG is main_encode
    finally:
        R._register_ffmpeg(None)


def test_restores_previous_when_check_raises():
    main_encode = _fake_proc()
    R._register_ffmpeg(main_encode)
    try:
        with pytest.raises(subprocess.CalledProcessError):
            R._run_ffmpeg_tracked(
                ["ffmpeg"], check=True, popen=_fake_popen(_fake_proc(returncode=1), [])
            )
        assert R._ACTIVE_FFMPEG is main_encode
    finally:
        R._register_ffmpeg(None)


def test_restores_previous_when_communicate_raises():
    main_encode = _fake_proc()

    def boom(_proc):
        raise OSError("communicate falhou")

    R._register_ffmpeg(main_encode)
    try:
        with pytest.raises(OSError):
            R._run_ffmpeg_tracked(
                ["ffmpeg"], popen=_fake_popen(_fake_proc(on_communicate=boom), [])
            )
        assert R._ACTIVE_FFMPEG is main_encode
    finally:
        R._register_ffmpeg(None)


# --- Critério 4: CompletedProcess coerente ------------------------------------


def test_completed_process_fields():
    proc = _fake_proc(returncode=3, out="saida", err="erro")
    result = R._run_ffmpeg_tracked(["ffmpeg", "-i", "a.mp4"], popen=_fake_popen(proc, []))
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 3
    assert result.stdout == "saida"
    assert result.stderr == "erro"
    assert result.args == ["ffmpeg", "-i", "a.mp4"]


# --- Critério 5: semântica de check ------------------------------------------


def test_check_raises_called_process_error_with_output():
    proc = _fake_proc(returncode=1, out="o", err="e")
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        R._run_ffmpeg_tracked(["ffmpeg"], check=True, popen=_fake_popen(proc, []))
    assert excinfo.value.returncode == 1
    assert excinfo.value.stdout == "o"
    assert excinfo.value.stderr == "e"


def test_check_does_not_raise_on_zero():
    proc = _fake_proc(returncode=0)
    assert R._run_ffmpeg_tracked(["ffmpeg"], check=True, popen=_fake_popen(proc, [])).returncode == 0


# --- kwargs dos 3 call sites --------------------------------------------------


def test_capture_output_becomes_two_pipes():
    seen = []
    R._run_ffmpeg_tracked(
        ["ffmpeg"], capture_output=True, popen=_fake_popen(_fake_proc(), seen)
    )
    _cmd, kwargs = seen[0]
    assert kwargs["stdout"] is subprocess.PIPE
    assert kwargs["stderr"] is subprocess.PIPE


def test_explicit_stdout_stderr_are_forwarded():
    seen = []
    R._run_ffmpeg_tracked(
        ["ffmpeg"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        popen=_fake_popen(_fake_proc(), seen),
    )
    _cmd, kwargs = seen[0]
    assert kwargs["stdout"] is subprocess.DEVNULL
    assert kwargs["stderr"] is subprocess.PIPE


def test_text_encoding_errors_and_cwd_are_forwarded():
    seen = []
    R._run_ffmpeg_tracked(
        ["ffmpeg"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        cwd="/tmp/x",
        popen=_fake_popen(_fake_proc(), seen),
    )
    cmd, kwargs = seen[0]
    assert cmd == ["ffmpeg"]
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "ignore"
    assert kwargs["cwd"] == "/tmp/x"


# --- Critério 6: matável enquanto roda ---------------------------------------


def test_terminate_active_ffmpeg_reaches_process_registered_by_helper():
    killed = []
    proc = _fake_proc(on_communicate=lambda p: killed.append(R.terminate_active_ffmpeg()))
    R._run_ffmpeg_tracked(["ffmpeg"], popen=_fake_popen(proc, []))
    assert killed == [True]
    assert proc.terminated is True


# --- Critério 7: os 3 call sites migraram, os 3 probes não --------------------


def test_derotate_site_uses_tracked_helper():
    src = inspect.getsource(R._strip_residual_rotation)
    assert "subprocess.run(" not in src
    assert "_run_ffmpeg_tracked(" in src


def test_loudnorm_pass1_site_uses_tracked_helper():
    src = inspect.getsource(R.analyze_audio_loudness)
    assert "subprocess.run(" not in src
    assert "_run_ffmpeg_tracked(" in src


def test_colr_remux_site_uses_tracked_helper_and_ffprobe_site_does_not():
    src = inspect.getsource(R.run_ffmpeg_with_cineon)
    assert "_run_ffmpeg_tracked(" in src
    # o único subprocess.run que sobra nesta função é o ffprobe de verificação
    assert src.count("subprocess.run(") == 1
    assert "probe_result = subprocess.run(" in src


def test_probe_sites_keep_subprocess_run():
    assert "subprocess.run(" in inspect.getsource(R.detect_hardware)
    assert "subprocess.run(" in inspect.getsource(R.detect_hdr_metadata)
