#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PETDESK → Lovart 单张生图脚本
复用 lovart-official 的 agent_skill.py 调用链：
  create-project → upload(每张图) → chat(prompt + attachments) → (必要时轮询 status/result) → 下载成品图
输出：最后一行打印 JSON {"ok":bool, "image":..., "url":..., "error":...}，供 server.js 解析。
进度行以 [petdesk] 开头打印到 stdout。
"""
import argparse
import json
import os
import random
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

LOVART_DIR = Path("E:/Claude code/lovart-official")
AGENT = LOVART_DIR / "skills" / "lovart-skill" / "agent_skill.py"
KEYS_FILE = LOVART_DIR / "keys.json"

# 与 POD 管线一致：锁定图像模型，避免 agent 自行挑选
PREFER_MODELS = '{"IMAGE":["generate_image_gpt_image_2_high"]}'


def log(msg):
    print(f"[petdesk] {msg}", flush=True)


def run_agent(ak, sk, home, *args, timeout=300):
    """执行 agent_skill.py 命令（独立 HOME，避免 state.json 冲突）"""
    cmd = [sys.executable, str(AGENT)] + list(args)
    env = os.environ.copy()
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["LOVART_ACCESS_KEY"] = ak
    env["LOVART_SECRET_KEY"] = sk
    env["LOVART_INSECURE_SSL"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                            encoding="utf-8", errors="replace", env=env)
    if result.returncode != 0:
        raise RuntimeError(((result.stderr or "") + (result.stdout or ""))[-300:])
    out = (result.stdout or "").strip()
    start = out.find("{")
    end = out.rfind("}")
    if start >= 0 and end > start:
        return json.loads(out[start:end + 1])
    raise RuntimeError(f"解析失败: {out[-200:]}")


def extract_img_url(data):
    """从 chat/result 返回中提取图片 URL（artifacts / markdown / 纯链接）"""
    for item in data.get("items", []):
        for art in item.get("artifacts", []):
            if art.get("type") == "image" and art.get("content"):
                return art["content"]
    for item in data.get("items", []):
        text = item.get("text", "")
        for u in re.findall(r'!\[[^\]]*\]\((https?://[^\s"\')]+)\)', text):
            return u
    for item in data.get("items", []):
        text = item.get("text", "")
        for u in re.findall(r'https?://[^\s"\']+\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s"\']*)?', text, re.IGNORECASE):
            return u
    return ""


def extract_agent_text(data):
    texts = []
    for item in data.get("items", []):
        if item.get("type") == "assistant" and item.get("text"):
            texts.append(item["text"].strip())
    return "\n".join(texts)[:300]


def download_image(url, path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
        data = resp.read()
    tmp = str(path) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return len(data)


def load_keys():
    return json.loads(KEYS_FILE.read_text(encoding="utf-8"))


def disable_key(idx):
    """与 Bridge 一致：风控 key 持久化禁用，后续不再使用"""
    try:
        data = load_keys()
        k = data["keys"][idx]
        if len(k) >= 3:
            k[2]["disabled"] = True
            KEYS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"key #{idx + 1} 风控，已写入禁用")
    except Exception as e:
        log(f"WARN: 禁用 key #{idx + 1} 失败: {e}")


def pick_keys(limit=5, first=-1):
    """随机选取最多 limit 个未禁用 key，返回 [(idx, ak, sk), ...]
    first >= 0 时把该 key 排在最前（并发任务各自锁定不同 key，故障转移仍可换其他 key）"""
    data = load_keys()
    avail = [(i, k) for i, k in enumerate(data["keys"]) if not (len(k) >= 3 and k[2].get("disabled"))]
    if not avail:
        raise RuntimeError("keys.json 中没有可用 key")
    random.shuffle(avail)
    if first >= 0:
        avail.sort(key=lambda t: 0 if t[0] == first else 1)
    return [(i, k[0], k[1]) for i, k in avail[:limit]]


def attempt(prompt, images, out_path, ak, sk):
    """用指定 key 跑完整生图流程，成功返回 dict，失败抛异常"""
    home = tempfile.mkdtemp(prefix="petdesk_lovart_home_")

    log("创建 Lovart 项目…")
    pid = run_agent(ak, sk, home, "create-project").get("project_id", "")
    if not pid:
        raise RuntimeError("创建项目失败")

    cdn_urls = []
    for p in images:
        log(f"上传参考图 {p.name}…")
        url = run_agent(ak, sk, home, "upload", "--file", str(p)).get("url", "")
        if not url:
            raise RuntimeError(f"上传失败: {p.name}")
        cdn_urls.append(url)

    log("提交生图请求（Lovart 生成中，约 1-3 分钟）…")
    chat = run_agent(ak, sk, home, "--timeout", "600", "chat",
                     "--project-id", pid, "--prompt", prompt,
                     "--attachments", *cdn_urls,
                     "--prefer-models", PREFER_MODELS, "--json",
                     timeout=660)
    tid = chat.get("thread_id", "")
    img_url = extract_img_url(chat)

    if not img_url and tid:
        log(f"未立即返回图片，轮询任务状态（tid={tid}）…")
        final = None
        for i in range(20):
            time.sleep(30)
            s = run_agent(ak, sk, home, "status", "--thread-id", tid, timeout=60).get("status", "")
            log(f"轮询 {i + 1}/20：status={s}")
            if s == "done":
                final = run_agent(ak, sk, home, "result", "--thread-id", tid, timeout=60)
                break
            if s in ("failed", "error", "canceled"):
                raise RuntimeError(f"生成失败(status={s})，tid={tid}")
        if final:
            img_url = extract_img_url(final)

    if not img_url:
        agent_txt = extract_agent_text(chat)
        raise RuntimeError(f"未返回图片URL" + (f"：{agent_txt[:120]}" if agent_txt else ""))

    log("下载成品图…")
    size = download_image(img_url, out_path)
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError("下载文件无效")
    log(f"完成 ✓ {out_path.name} ({size}B)")
    return {"ok": True, "image": out_path.name, "tid": tid, "size": size}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--image", action="append", default=[], help="参考图本地路径，可重复")
    ap.add_argument("--out", required=True, help="成品图输出路径(.png)")
    ap.add_argument("--key-idx", type=int, default=-1, help="优先使用的 key 序号（keys.json 下标），并发任务各用不同 key")
    args = ap.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    images = [Path(p) for p in args.image]
    for p in images:
        if not p.exists():
            raise RuntimeError(f"图片不存在: {p}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Key 故障转移：风控 → 禁用并换 key；积分不足 → 换 key；最多试 5 个
    errors = []
    for idx, ak, sk in pick_keys(5, first=args.key_idx):
        log(f"使用 Lovart key #{idx + 1}")
        try:
            result = attempt(prompt, images, out_path, ak, sk)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            return
        except Exception as e:
            err = str(e)
            errors.append(f"key#{idx + 1}: {err[:120]}")
            log(f"key #{idx + 1} 失败：{err[:150]}")
            if "risk control" in err.lower():
                disable_key(idx)
            elif "Insufficient credits" not in err:
                # 非风控/非积分错误（网络、参数等）换 key 无意义，直接失败
                raise
    raise RuntimeError("所有尝试均失败 | " + " ; ".join(errors))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)[:400]}, ensure_ascii=False), flush=True)
        sys.exit(1)
