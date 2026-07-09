import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))

from check_rem import _has_missing


def _pair(stem, ai_file, rem_file):
    return {
        "stem": stem,
        "ai_file": ai_file,
        "rem_file": rem_file,
        "group_id": "",
        "ai_uid": None,
        "rem_uid": None,
        "ai_stage": "ai",
        "rem_stage": "rembg" if rem_file else None,
        "role": "B" if stem.endswith("_B") else "W" if stem.endswith("_W") else "BW",
    }


def test_has_missing_single_b_is_not_missing():
    proj = {
        "dx": "DX0001",
        "pairs": [_pair("DX0001_B", "DX0001_B.png", "DX0001_B_cut.png")],
    }
    assert _has_missing(proj) is False


def test_has_missing_single_w_is_not_missing():
    proj = {
        "dx": "DX0001",
        "pairs": [_pair("DX0001_W", "DX0001_W.png", "DX0001_W_cut.png")],
    }
    assert _has_missing(proj) is False


def test_has_missing_missing_ai_is_missing():
    proj = {
        "dx": "DX0001",
        "pairs": [_pair("DX0001_B", None, "DX0001_B_cut.png")],
    }
    assert _has_missing(proj) is True


def test_has_missing_missing_rem_is_missing():
    proj = {
        "dx": "DX0001",
        "pairs": [_pair("DX0001_B", "DX0001_B.png", None)],
    }
    assert _has_missing(proj) is True


def test_has_missing_both_b_and_w_complete_is_not_missing():
    proj = {
        "dx": "DX0001",
        "pairs": [
            _pair("DX0001_B", "DX0001_B.png", "DX0001_B_cut.png"),
            _pair("DX0001_W", "DX0001_W.png", "DX0001_W_cut.png"),
        ],
    }
    assert _has_missing(proj) is False
