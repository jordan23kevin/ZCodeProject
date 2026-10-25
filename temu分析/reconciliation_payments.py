# -*- coding: utf-8 -*-
import argparse
import os
import sqlite3
from datetime import date

from reconciliation_pagination import set_max_page_size
from reconciliation_sync import fetch_start, months_between, set_date_range
from sync_aftersales import backup_database, wait_api

SETTLE_URL = "https://agentseller-eu.temu.com/labor/settle"
PAYMENT_COLUMNS = [
    "file_key", "status", "po", "sku_id", "sku_name", "sku_code", "qty", "declared_price", "is_promo", "currency",
    "sale_back", "sale_back_net", "sale_reversal", "ship_back", "ship_back_net", "ship_reversal", "source_file",
]


def money(obj):
    value = (obj or {}).get("value")
    return None if value is None else value / 100


def flatten_payment_row(row, status, order_months):
    po = row["parentOrderSn"]
    if po not in order_months:
        raise ValueError(f"订单库缺少 PO，无法确定款项月份: {po}")
    month = order_months[po]
    file_key = f"payment_{'received' if status == '已到账' else 'pending'}|{month}"
    rows = []
    for item in row.get("skuItems") or []:
        sale_back = money(row.get("productPaymentAmount"))
        sale_discount = money(row.get("productPaymentDiscountAmount")) or 0
        ship_back = money(row.get("shippingPaymentAmount"))
        ship_discount = money(row.get("shippingPaymentDiscountAmount")) or 0
        rows.append({
            "file_key": file_key,
            "status": status,
            "po": po,
            "sku_id": str(item["id"]),
            "sku_name": item.get("name"),
            "sku_code": item.get("extCode"),
            "qty": item.get("number"),
            "declared_price": money(item.get("declarationSupplyPrice") or item.get("supplyPrice")),
            "is_promo": int(bool(item.get("promotionalPrice"))),
            "currency": row.get("currency") or "CNY",
            "sale_back": sale_back,
            "sale_back_net": None if sale_back is None else sale_back - sale_discount,
            "sale_reversal": money(row.get("productRefundAmount")),
            "ship_back": ship_back,
            "ship_back_net": None if ship_back is None else ship_back - ship_discount,
            "ship_reversal": money(row.get("shippingRefundAmount")),
            "source_file": "api:settled/po" if status == "已到账" else "api:unsettle",
        })
    return rows


def _query(page, endpoint):
    return wait_api(page, endpoint, lambda: page.evaluate("""
      () => {const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='查询');
      if(!els.length)throw new Error('未找到结算查询按钮');els[0].click();}
    """))


def _next(page, endpoint):
    return wait_api(page, endpoint, lambda: page.evaluate("""
      () => {const e=document.querySelector('li[class*=PGT_next]:not([class*=PGT_disabled])');
      if(!e)throw new Error('结算下一页不可用');e.click();}
    """))


def collect_payments(page, status, order_months, start=None, end=None):
    import calendar

    if end is None:
        end = date.today()
    if start is None:
        start = fetch_start()  # 滚动窗口：只抓最近 90 天

    label = "已到账款项" if status == "已到账" else "待处理款项"
    endpoint = "/api/xiaowenhou/settle-flow/sm/settled/po/page-query" if status == "已到账" else "/api/xiaowenhou/settle-flow/sm/unsettle/page-query"
    page.goto(SETTLE_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    page.click(f"text={label}", timeout=10000)
    page.wait_for_timeout(1500)
    rows = []
    for year, month in months_between(start, end):
        start_day = start.day if (year, month) == (start.year, start.month) else 1
        last_day = calendar.monthrange(year, month)[1] if (year, month) < (end.year, end.month) else end.day
        set_date_range(page, date(year, month, start_day), date(year, month, last_day))
        page_size = set_max_page_size(page, 200)  # 结算页上限 200
        page_number = 1
        expected_total = None
        month_rows = []
        seen = set()
        seen_pos = set()
        while True:
            payload = _query(page, endpoint) if page_number == 1 else _next(page, endpoint)
            result = payload.get("result") or {}
            total = result.get("total")
            data = result.get("dataList")
            if not isinstance(total, int) or not isinstance(data, list):
                raise ValueError(f"{label}接口缺少 total/dataList")
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise RuntimeError(f"{label}翻页期间总数变化: {expected_total} -> {total}")
            for row in data:
                seen_pos.add(row["parentOrderSn"])
                for flattened in flatten_payment_row(row, status, order_months):
                    key = (flattened["po"], flattened["sku_id"])
                    if key not in seen:
                        seen.add(key)
                        month_rows.append(flattened)
            if not data or page_number * page_size >= expected_total:
                break
            page_number += 1
        if len(seen_pos) != expected_total:
            raise RuntimeError(f"{label} {year}-{month:02d} 主单数不一致: 页面={expected_total}, 抓取={len(seen_pos)}")
        rows.extend(month_rows)
        print(f"{label} {year}-{month:02d}: {len(month_rows)} 行")
    return rows


def replace_payments(con, rows):
    if not rows:
        raise RuntimeError("款项快照为空，拒绝清空 payment")
    keys = {(row["status"], row["po"], row["sku_id"]) for row in rows}
    if len(keys) != len(rows):
        raise RuntimeError("款项快照存在重复 PO+SKU，拒绝整表替换")
    # 只替换本次抓到的月份（file_key），90 天窗口外已结算的历史月份保留在库里
    file_keys = sorted({row["file_key"] for row in rows})
    received = {}
    for row in rows:
        if row["status"] == "已到账":
            received[(row["po"], row["sku_id"])] = row

    def financial_signature(row):
        return (
            row["qty"], round(row["sale_back"] or 0, 2), round(row["sale_reversal"] or 0, 2),
            round(row["ship_back"] or 0, 2), round(row["ship_reversal"] or 0, 2),
        )

    filtered = []
    duplicates = 0
    conflicts = []
    for row in rows:
        key = (row["po"], row["sku_id"])
        if row["status"] == "待处理" and key in received:
            if financial_signature(row) == financial_signature(received[key]):
                duplicates += 1
                continue
            conflicts.append(key)
        filtered.append(row)
    if conflicts:
        raise RuntimeError(f"已到账与待处理金额不一致，需人工核对: {conflicts[:10]}")
    placeholders = ",".join("?" for _ in PAYMENT_COLUMNS)
    with con:
        for file_key in file_keys:
            con.execute("DELETE FROM payment WHERE file_key=?", (file_key,))
        con.executemany(
            f"INSERT INTO payment({','.join(PAYMENT_COLUMNS)}) VALUES({placeholders})",
            [[row.get(name) for name in PAYMENT_COLUMNS] for row in filtered],
        )
    return duplicates


def sync_payments(db_path):
    from playwright.sync_api import sync_playwright

    con = sqlite3.connect(db_path)
    try:
        order_months = {po: str(created)[:7] for po, created in con.execute("SELECT order_no,created_at FROM orders")}
        backup = backup_database(db_path, os.path.join(os.path.dirname(db_path), "backups"))
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if "labor/settle" in (pg.url or "")), None) or ctx.new_page()
            received = collect_payments(page, "已到账", order_months)
            pending = collect_payments(page, "待处理", order_months)
        duplicates = replace_payments(con, received + pending)
        print(f"已到账: {len(received)}; 待处理: {len(pending) - duplicates}; 剔除重复在途: {duplicates}; 备份: {backup}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    args = parser.parse_args()
    sync_payments(os.path.abspath(args.db))


if __name__ == "__main__":
    main()
