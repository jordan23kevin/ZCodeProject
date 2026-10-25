# -*- coding: utf-8 -*-
import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from aftersales_core import flatten_aftersale, list_signature
from aftersales_db import ensure_schema, existing_signatures, upsert_aftersales, refresh_estimates, reconcile_return_label
from reconciliation_pagination import set_max_page_size

LISTER_URL = "/garen/mms/afterSales/queryReturnAndRefundPaList"
DETAIL_URL = "/garen/mms/afterSales/queryReturnDetails"
DETAIL_URLS = (DETAIL_URL, "/garen/mms/afterSales/queryRefundDetails")
PAGE_URL = "https://agentseller-eu.temu.com/mmsos/return-refund-list.html"
CST = timezone(timedelta(hours=8))


def parse_list_payload(payload, requested_page):
    if payload.get("error_code") or payload.get("success") is False:
        raise ValueError(f"售后列表接口失败: {payload}")
    vo = (payload.get("result") or {}).get("mmsPageVO")
    if not isinstance(vo, dict) or not isinstance(vo.get("data"), list):
        raise ValueError("售后列表缺少 mmsPageVO.data")
    page_size = vo.get("pageSize")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
        raise ValueError(f"售后列表 pageSize 必须为正整数且不能是 bool: {page_size!r}")
    if vo.get("pageNumber") != requested_page or not isinstance(vo.get("totalCount"), int):
        raise ValueError(f"售后列表页码或总数异常: {vo}")
    return vo


def _extract_detail_result(payload):
    if not isinstance(payload, dict):
        raise ValueError(f"售后详情格式异常: {payload}")
    result = payload.get("result") or payload
    if not isinstance(result, dict):
        raise ValueError(f"售后详情格式异常: {payload}")
    for candidate in (payload, result):
        if candidate.get("success") is False or candidate.get("error_code"):
            raise ValueError(f"售后详情接口失败: {payload}")
    return result


def parse_detail_payload(payload, parent_after_sales_sn):
    result = _extract_detail_result(payload)
    if result.get("parentAfterSalesSn") != parent_after_sales_sn:
        raise ValueError(f"售后详情不匹配: {parent_after_sales_sn}")
    return result


def wait_api(page, endpoint, trigger, match=None):
    endpoints = (endpoint,) if isinstance(endpoint, str) else tuple(endpoint)
    errors = []
    for _ in range(2):
        found = []
        def on_response(resp):
            if not any(candidate in resp.url for candidate in endpoints):
                return
            try:
                body = resp.body().decode("utf-8", "ignore")
                payload = json.loads(body)
                if match is None or match(payload):
                    found.append(payload)
            except BaseException as exc:
                errors.append(exc)
        page.on("response", on_response)
        try:
            trigger()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if found:
                    return found[0]
                page.wait_for_timeout(200)
        except Exception as exc:
            errors.append(exc)
        finally:
            page.remove_listener("response", on_response)
    raise TimeoutError(f"两次等待接口均失败: {endpoint}; errors={errors}")


def click_query(page):
    return wait_api(page, LISTER_URL, lambda: page.evaluate("""
      () => {const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='查询');
      if(!els.length)throw new Error('未找到查询按钮');els[0].click();}
    """))


def click_next(page):
    return wait_api(page, LISTER_URL, lambda: page.evaluate("""
      () => {const e=document.querySelector('li[class*=PGT_next]:not([class*=PGT_disabled])');
      if(!e)throw new Error('下一页不可用');e.click();}
    """))


def open_detail(page, row_index, parent_after_sales_sn):
    payload = wait_api(
        page, DETAIL_URLS,
        lambda: page.evaluate("""
          (index) => {const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='查看售后详情');
          if(!els[index])throw new Error('详情按钮索引越界: '+index);els[index].click();}
        """, row_index),
        match=lambda body: _extract_detail_result(body).get("parentAfterSalesSn") == parent_after_sales_sn)
    page.keyboard.press("Escape")
    return parse_detail_payload(payload, parent_after_sales_sn)


def _detail_amount_to_minor(value, decimals):
    if not isinstance(value, str):
        return value
    from decimal import Decimal
    text = value.strip()
    for token in ("€", "¥", "zł", "kr.", "kr", "Kč"):
        text = text.replace(token, "")
    text = "".join(text.split())
    if text in ("", "-", "--"):
        return None
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        scaled = Decimal(text).scaleb(decimals)
    except Exception as exc:
        raise ValueError(f"无法解析售后金额: {value!r}") from exc
    if scaled != scaled.to_integral_value():
        raise ValueError(f"售后金额精度异常: {value!r}, decimals={decimals}")
    return int(scaled)


def flatten_collected_aftersale(list_row, seen_at, detail):
    if detail is None:
        return flatten_aftersale(list_row, seen_at)
    normalized = dict(detail)
    decimals = (detail.get("nationalPriceConfigVO") or {}).get("decimals", 2)
    normalized["afterSalesItemVOList"] = []
    for item in detail.get("afterSalesItemVOList") or []:
        normalized_item = dict(item)
        for field in ("applyRefundAmount", "refundAmount"):
            normalized_item[field] = _detail_amount_to_minor(item.get(field), decimals)
        normalized["afterSalesItemVOList"].append(normalized_item)
    rows = flatten_aftersale(list_row, seen_at, normalized)
    raw_detail = json.dumps(detail, ensure_ascii=False)
    for row in rows:
        row["detail_json"] = raw_detail
    return rows


def collect_aftersales(page, signatures, seen_at):
    page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    if "auth/authentication" in page.url:
        raise RuntimeError("欧区代理后台登录失效")
    page_size = set_max_page_size(page, 100)  # 卖家中心售后页上限 100
    rows = []
    page_number = 1
    expected_total = None
    while True:
        payload = click_query(page) if page_number == 1 else click_next(page)
        vo = parse_list_payload(payload, page_number)
        if expected_total is None:
            expected_total = vo["totalCount"]
        elif vo["totalCount"] != expected_total:
            raise RuntimeError(f"翻页期间总数变化: {expected_total} -> {vo['totalCount']}")
        for index, list_row in enumerate(vo["data"]):
            as_id = list_row["parentAfterSalesSn"]
            signature = list_signature(list_row)
            detail = open_detail(page, index, as_id) if signatures.get(as_id) != signature else None
            rows.extend(flatten_collected_aftersale(list_row, seen_at, detail))
        if not vo["data"] or page_number * page_size >= expected_total:
            break
        page_number += 1
    collected_parents = {row["as_id"] for row in rows}
    if len(collected_parents) != expected_total:
        raise RuntimeError(f"售后总数不一致: 页面={expected_total}, 抓取={len(collected_parents)}")
    return rows


def backup_database(db_path, backup_dir):
    from pathlib import Path
    source = Path(db_path)
    destination = Path(backup_dir)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{source.stem}_before_aftersales_{datetime.now(CST):%Y%m%d_%H%M%S}{source.suffix}"
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return str(target)


def ensure_cdp(playwright):
    import subprocess
    import urllib.request
    try:
        return playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
    except Exception:
        pass
    check = subprocess.run([
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
        "Where-Object { $_.CommandLine -and $_.CommandLine.Contains('edge-cdp-profile') } | "
        "ForEach-Object { $_.ProcessId }"
    ], capture_output=True, text=True, timeout=30)
    if check.stdout.strip():
        raise RuntimeError("专用 Edge 已运行但 9222 未开启；请只关闭该专用实例后重试，未自动结束任何进程")
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    subprocess.Popen([
        edge, "--remote-debugging-port=9222", r"--user-data-dir=C:\edge-cdp-profile",
        "--no-first-run", "--no-default-browser-check", "--js-flags=--max-old-space-size=4096",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
       creationflags=0x00000008 | 0x00000200)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            with opener.open("http://127.0.0.1:9222/json/version", timeout=2) as response:
                if response.status == 200:
                    return playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("专用 Edge 的 9222 未就绪")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    parser.add_argument("--skip-reconcile", action="store_true")
    args = parser.parse_args()
    db_path = os.path.abspath(args.db)
    con = sqlite3.connect(db_path)
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='aftersale'").fetchone():
            raise RuntimeError("目标库不是有效的 Temu 对账库")
        print("备份:", backup_database(db_path, os.path.join(os.path.dirname(db_path), "backups")))
        ensure_schema(con)
        signatures = existing_signatures(con)
        seen_at = datetime.now(CST).isoformat(timespec="seconds")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = ensure_cdp(p)
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if "return-refund-list" in (pg.url or "")), None)
            page = page or ctx.new_page()
            rows = collect_aftersales(page, signatures, seen_at)
        upsert_aftersales(con, rows)
        detail_count = len({r["as_id"] for r in rows if r["detail_fetched_at"] == seen_at})
        print(f"售后明细行: {len(rows)}; 售后主单: {len({r['as_id'] for r in rows})}")
        print("本次详情抓取:", detail_count)
        if not args.skip_reconcile:
            actual_ids = [r[0] for r in con.execute("SELECT bill_id FROM return_label")]
            outcomes = {key: 0 for key in ("实际", "回正", "待核对")}
            for bill_id in actual_ids:
                outcomes[reconcile_return_label(con, bill_id, seen_at)] += 1
            fee_status = []
            created = refresh_estimates(con, seen_at, fee_status)
            pending = {key: sum(1 for row in fee_status if row["source"] == key) for key in ("待出账", "待核对")}
            print("实际账单:", outcomes, "新增暂估:", len(created), "费用状态:", pending)
    finally:
        con.close()


if __name__ == "__main__":
    main()
