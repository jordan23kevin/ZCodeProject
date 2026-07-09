# -*- coding: utf-8 -*-
"""模板预设与 CLI 参数加载回归测试。"""

import sys

from white_t_mockup import cli
from white_t_mockup.config import get_preset, list_presets


def test_list_presets_contains_configured_templates():
    presets = list_presets()

    assert "W3.psd" in presets
    assert "1B.png" in presets
    assert "3B.png" in presets
    assert "4B.png" in presets


def test_get_preset_accepts_name_and_full_path():
    by_name = get_preset("1B.png")
    by_path = get_preset(r"D:\Semems\1胚衣\白\1B.png")

    assert by_name is not None
    assert by_path == by_name
    assert by_name["method"] == "transform"
    assert by_name["scale"] == 0.40
    assert by_name["rotation_degrees"] == 0.0
    assert by_name["effective_top_y"] == 725
    assert by_name["effective_center_x"] == 649
    assert by_name["blend_mode"] == "multiply"


def test_get_preset_3b_png():
    preset = get_preset("3B.png")

    assert preset is not None
    assert preset["method"] == "transform"
    assert preset["scale"] == 0.32
    assert preset["rotation_degrees"] == -3.0
    assert preset["effective_top_y"] == 700
    assert preset["effective_center_x"] == 777
    assert preset["blend_mode"] == "multiply"


def test_get_preset_4b_png():
    preset = get_preset("4B.png")

    assert preset is not None
    assert preset["method"] == "transform"
    assert preset["scale"] == 0.28
    assert preset["rotation_degrees"] == 2.0
    assert preset["effective_top_y"] == 1011
    assert preset["effective_center_x"] == 576
    assert preset["blend_mode"] == "multiply"


def _fake_transform_result(kwargs):
    return {
        "output_size": (10, 10),
        "blend_mode": kwargs.get("blend_mode") or "normal",
        "scale": kwargs["scale"],
        "rotation_degrees": kwargs["rotation_degrees"],
        "effective_top": kwargs["effective_top_y"],
        "effective_center_x": kwargs["effective_center_x"],
    }


def _fake_legacy_result(kwargs):
    return {
        "output_size": (10, 10),
        "blend_mode": kwargs.get("blend_mode") or "normal",
        "design_size": (1, 1),
        "design_left": 0,
        "design_top": kwargs["top_y"],
        "design_center": kwargs["center_x"],
    }


def test_cli_preset_loads_transform_params(monkeypatch, tmp_path):
    calls = []

    def fake_apply_mockup_transform(**kwargs):
        calls.append(kwargs)
        return _fake_transform_result(kwargs)

    monkeypatch.setattr(cli, "apply_mockup_transform", fake_apply_mockup_transform)
    monkeypatch.setattr(
        sys,
        "argv",
        ["white_t_mockup", "design.png", str(tmp_path / "out.jpg"), "--preset", "1B.png"],
    )

    cli.main()

    assert len(calls) == 1
    assert calls[0]["template_path"] == r"D:\Semems\1胚衣\白\1B.png"
    assert calls[0]["scale"] == 0.40
    assert calls[0]["rotation_degrees"] == 0.0
    assert calls[0]["effective_top_y"] == 725
    assert calls[0]["effective_center_x"] == 649
    assert calls[0]["blend_mode"] == "multiply"


def test_cli_template_filename_auto_matches_preset(monkeypatch, tmp_path):
    calls = []

    def fake_apply_mockup_transform(**kwargs):
        calls.append(kwargs)
        return _fake_transform_result(kwargs)

    monkeypatch.setattr(cli, "apply_mockup_transform", fake_apply_mockup_transform)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "white_t_mockup",
            "design.png",
            str(tmp_path / "out.jpg"),
            "--template",
            r"D:\Semems\1胚衣\白\1B.png",
        ],
    )

    cli.main()

    assert len(calls) == 1
    assert calls[0]["scale"] == 0.40
    assert calls[0]["rotation_degrees"] == 0.0
    assert calls[0]["effective_top_y"] == 725
    assert calls[0]["effective_center_x"] == 649


def test_cli_preset_loads_legacy_params(monkeypatch, tmp_path):
    calls = []

    def fake_apply_mockup(**kwargs):
        calls.append(kwargs)
        return _fake_legacy_result(kwargs)

    monkeypatch.setattr(cli, "apply_mockup", fake_apply_mockup)
    monkeypatch.setattr(
        sys,
        "argv",
        ["white_t_mockup", "design.png", str(tmp_path / "out.jpg"), "--preset", "W3.psd"],
    )

    cli.main()

    assert len(calls) == 1
    assert calls[0]["template_path"] == r"D:\Semems\1胚衣\白\W3.psd"
    assert calls[0]["target_height"] == 677
    assert calls[0]["top_y"] == 449
    assert calls[0]["center_x"] == 735
    assert calls[0]["blend_mode"] == "multiply"


def test_cli_list_presets(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["white_t_mockup", "--list-presets"])

    cli.main()

    output = capsys.readouterr().out
    assert "W3.psd" in output
    assert "1B.png" in output
    assert "3B.png" in output
    assert "4B.png" in output
