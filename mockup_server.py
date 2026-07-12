#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动化遮罩 & 贴图系统 —— 本地 Web 服务。

提供两个核心按钮对应的后端接口：
  1) /api/generate_mask   生成遮罩 + _tpl 扭曲素材（点击「生成遮罩」）
  2) /api/apply_mockup    读取已生成的遮罩与扭曲数据，精准贴图（点击「贴图」）

两个环节通过“模板名(preset)”这个唯一键衔接：
  生成步骤写入 D:\Semems\1胚衣\_tpl\<款名>\{mask,disp,shadow,highlight}.png
  贴图步骤由 white_t_mockup 自动探测同一个目录并读取
中间无需任何手动拷贝，数据传递由文件系统保证一致。

纯标准库实现，离线可跑（仅需 cv2/numpy 在 PYTHONPATH 中）。
"""

from __future__ import annotations

import cgi
import io
import json
import os
import subprocess
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ---- 路径配置（与 tpl_generator / white_t_mockup 完全一致）----
HERE = Path(__file__).resolve().parent
TPL_ROOT = Path(r"D:\Semems\1胚衣\_tpl")
PRESETS = Path(r"E:\Kimi Code\white_t_mockup\presets.json")
RESULTS = HERE / "mockup_output"
PY = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
PYTHONPATH = r"E:/python_packages;E:/Kimi Code"
INDEX = HERE / "index.html"

# 让本服务能 import 同目录的 tpl_generator
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from tpl_generator import (  # noqa: E402
    generate_for_preset,
    preset_stem,
    DEFAULT_TPL_ROOT,
)

RESULTS.mkdir(parents=True, exist_ok=True)

LOGFILE = HERE / "mockup_server.log"


def _log(msg: str):
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S") + " " + msg + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 业务逻辑
# ---------------------------------------------------------------------------
def list_templates() -> dict:
    presets = json.loads(PRESETS.read_text(encoding="utf-8"))
    out = []
    for name in sorted(presets["templates"].keys()):
        stem = Path(presets["templates"][name]["path"]).stem
        tpldir = TPL_ROOT / stem
        has_tpl = (tpldir / "mask.png").exists()
        cov = None
        color = None
        if has_tpl and (tpldir / "metadata.json").exists():
            try:
                meta = json.loads((tpldir / "metadata.json").read_text(encoding="utf-8"))
                cov = meta.get("mask_coverage")
                color = meta.get("color_hint")
            except Exception:
                pass
        out.append(
            {
                "name": name,
                "stem": stem,
                "has_tpl": has_tpl,
                "coverage": cov,
                "color_hint": color,
            }
        )
    return {"templates": out}


def api_generate_mask(template: str) -> dict:
    try:
        out, cov, hint = generate_for_preset(template)
        return {
            "ok": True,
            "template": template,
            "stem": out.name,
            "coverage": round(cov, 3),
            "color_hint": hint,
            "preview": "/api/preview?tpl=" + urllib.parse.quote(out.name),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def _remove_bg_simple(design_bytes: bytes):
    """极简白底去背：从四角 floodfill 得到背景区域，置透明并轻度羽化。"""
    import cv2
    import numpy as np
    from PIL import Image

    img = Image.open(io.BytesIO(design_bytes)).convert("RGB")
    arr = np.array(img).astype(np.int16)
    h, w = arr.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    # 在副本上从 (0,0) 漫水，容差 18
    cv2.floodFill(arr, mask, (0, 0), (0, 0, 0),
                  (18, 18, 18), (18, 18, 18), flags=cv2.FLOODFILL_FIXED_RANGE)
    bg = mask[1:-1, 1:-1] == 1
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
    out = np.dstack([np.array(img), alpha]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def api_apply_mockup(form: cgi.FieldStorage) -> dict:
    try:
        template = form.getvalue("template") or ""
        for_black = (form.getvalue("for_black_shirt") or "false") == "true"
        autoremove = (form.getvalue("autoremove") or "false") == "true"
        disp = float(form.getvalue("disp_strength") or 12)
        sh = float(form.getvalue("shadow_opacity") or 0.35)
        hi = float(form.getvalue("highlight_opacity") or 0.25)

        if "design" not in form or not hasattr(form["design"], "file"):
            return {"ok": False, "error": "缺少上传的贴图文件"}
        design_bytes = form["design"].file.read()
        if not design_bytes:
            return {"ok": False, "error": "贴图文件为空"}

        stem = preset_stem(template)

        # 关键衔接：贴图前确认遮罩已存在，否则自动补生成（保证一键可达）
        tpl_dir = TPL_ROOT / stem
        auto_generated = False
        if not (tpl_dir / "mask.png").exists():
            generate_for_preset(template)
            auto_generated = True

        # 保存上传的贴图
        ts = int(time.time() * 1000)
        design_path = RESULTS / f"_up_{ts}.png"
        if autoremove:
            _remove_bg_simple(design_bytes).save(str(design_path))
        else:
            design_path.write_bytes(design_bytes)

        out_path = RESULTS / f"result_{stem}_{ts}.jpg"

        cmd = [
            PY, "-m", "white_t_mockup",
            str(design_path), str(out_path),
            "--preset", template,
            "--disp-strength", str(disp),
            "--shadow-opacity", str(sh),
            "--highlight-opacity", str(hi),
        ]
        if for_black:
            cmd.append("--for-black-shirt")

        env = dict(os.environ)
        env["PYTHONPATH"] = PYTHONPATH
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "贴图失败:\n" + (proc.stderr or proc.stdout)[-1500:],
            }

        return {
            "ok": True,
            "template": template,
            "stem": stem,
            "auto_generated_mask": auto_generated,
            "url": "/api/result/" + urllib.parse.quote(out_path.name),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默日志
        pass

    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, ctype: str):
        if not path.exists():
            self.send_error(404, "not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        _log(f"GET {path!r}")
        if path in ("/", "/index.html"):
            self._send_file(INDEX, "text/html; charset=utf-8")
        elif path == "/api/templates":
            self._send_json(list_templates())
        elif path == "/api/preview":
            q = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            tpl = q.get("tpl", [""])[0]
            self._send_file(TPL_ROOT / tpl / "_preview" / "mask_overlay.jpg", "image/jpeg")
        elif path.startswith("/api/result/"):
            fn = urllib.parse.unquote(path.split("/api/result/", 1)[1])
            # 只允许访问结果目录内的文件，防目录穿越
            safe = RESULTS / fn
            try:
                safe.resolve().relative_to(RESULTS.resolve())
            except Exception:
                self.send_error(403)
                return
            self._send_file(safe, "image/jpeg")
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        _log(f"POST {path!r}")
        if path == "/api/generate_mask":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads((self.rfile.read(length) or b"{}").decode("utf-8"))
            self._send_json(api_generate_mask(body.get("template", "")))
        elif path == "/api/apply_mockup":
            environ = {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            }
            form = cgi.FieldStorage(fp=self.rfile, environ=environ, headers=self.headers)
            self._send_json(api_apply_mockup(form))
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


def main():
    port = int(os.environ.get("MOCKUP_PORT", "8765"))
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"自动化遮罩&贴图系统已启动: http://127.0.0.1:{port}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
