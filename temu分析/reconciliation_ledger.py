# -*- coding: utf-8 -*-
import argparse
import calendar
import json
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone

from reconciliation_pagination import set_max_page_size
from reconciliation_sync import fetch_start, months_between, set_date_range
from sync_aftersales import backup_database, ensure_cdp, wait_api

CST = timezone(timedelta(hours=8))
LEDGER_URL = "https://seller.kuajingmaihuo.com/labor/bill"
SHIP_URL = "https://agentseller-eu.temu.com/labor/stml-logistics"
RETURN_URL = "https://agentseller-eu.temu.com/labor/stml-reverse-logistics"
LEDGER_API = "/api/merchant/fund/detail/pageSearch"
SHIP_API = "/portal/selene/seller/portal/recon/list"
RETURN_API = "/portal/selene/seller/return/list"
LEDGER_COLUMNS = ["file_key", "tx_time", "tx_type", "currency", "amount", "remark", "source_file", "query_id", "trans_sn"]
SHIP_COLUMNS = ["file_key", "bill_id", "package_no", "waybill_no", "carrier", "bill_type", "remark", "amount", "currency", "status", "tx_time", "source_file"]
RETURN_COLUMNS = ["file_key", "bill_id", "waybill_no", "po", "bill_type", "currency", "remark", "amount", "tx_time", "source_file"]


def iso_ms(value):
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, CST).isoformat(timespec="seconds")


def ensure_financial_schema(con):
    for table, column, sql_type in [("ledger", "query_id", "TEXT"), ("ledger", "trans_sn", "TEXT"), ("ship_label", "bill_id", "TEXT")]:
        existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
    con.commit()


def flatten_ledger(row):
    tx_time = row["createTime"]
    change_type = row.get("moneyChangeType")
    sign = 1 if change_type == 1 else -1 if change_type == 2 else (1 if row.get("fundTypeDesc") in ("结算", "充值") else -1)
    value = abs((row.get("amountFormat") or {}).get("value") or 0) / 100
    return {
        "file_key": f"ledger|{tx_time[:7]}",
        "tx_time": tx_time,
        "tx_type": row.get("fundTypeDesc"),
        "currency": row.get("currencyType") or "CNY",
        "amount": value * sign,
        "remark": row.get("remark"),
        "source_file": "api:fund/detail/pageSearch",
        "query_id": row.get("queryId"),
        "trans_sn": row.get("transSn"),
    }


def flatten_ship(row):
    money = row.get("priceCurrencyFormat") or {}
    amount = abs(float(money.get("amountYuan") or 0))
    sign = -1 if money.get("sign") == "-" or row.get("reconciliationTypeDesc") == "支出" else 1
    return {
        "file_key": f"ship_label|{iso_ms(row.get('deductTime'))[:7]}",
        "bill_id": row.get("reconciliationId"),
        "package_no": row.get("packageSn"),
        "waybill_no": row.get("waybillSn"),
        "carrier": row.get("serviceProviderName"),
        "bill_type": row.get("reconciliationTypeDesc"),
        "remark": row.get("remark"),
        "amount": amount * sign,
        "currency": money.get("currencyCode") or "CNY",
        "status": row.get("statusDesc"),
        "tx_time": iso_ms(row.get("deductTime")),
        "source_file": "api:portal/recon/list",
    }


def flatten_return(row):
    amount = abs(float(row.get("totalCharge") or 0))
    sign = -1 if row.get("sign") == "-" or row.get("deductTypeDesc") == "支出" else 1
    return {
        "file_key": f"return_label|{iso_ms(row.get('deductTime'))[:7]}",
        "bill_id": row.get("reconciliationId"),
        "waybill_no": row.get("waybillSn"),
        "po": row.get("parentOrderSn"),
        "bill_type": row.get("reconciliationTypeDesc") or row.get("deductTypeDesc"),
        "currency": row.get("sellerCurrency") or "CNY",
        "remark": row.get("remark"),
        "amount": amount * sign,
        "tx_time": iso_ms(row.get("deductTime")),
        "source_file": "api:seller/return/list",
    }


def _query(page, endpoint):
    return wait_api(page, endpoint, lambda: page.evaluate("""
      () => {const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='查询');
      if(!els.length)throw new Error('未找到账务查询按钮');els[0].click();}
    """))


def _next(page, endpoint, page_number):
    for attempt in range(3):
        try:
            page.wait_for_selector('li[class*=PGT_pagerItem], [class*=paginationContainer]', timeout=10000)
            break
        except Exception:
            if attempt == 2:
                raise
            print(f"第{attempt + 1}次等待分页器超时，重试")
            page.wait_for_timeout(2000)
    return wait_api(page, endpoint, lambda: page.evaluate("""
      (pageNumber) => {
        const items=[...document.querySelectorAll('[class*=PGT_pagerItem]')];
        const target=items.find(e=>e.getClientRects().length&&e.innerText.trim()===String(pageNumber));
        if(target){target.click();return;}
        const visible=[...document.querySelectorAll('li[class*=PGT_next], [class*="__next"]')]
          .filter(e=>e.getClientRects().length&&!/disable/i.test(String(e.className)));
        const next=visible[visible.length-1];
        if(!next)throw new Error('账务下一页不可用: '+pageNumber);next.click();
      }
    """, page_number))


def set_page_size(page, preferred=100):
    return set_max_page_size(page, preferred)  # 面单页上限 100


def collect_month(page, url, endpoint, year, month, start_day, end_day, kind):
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(3500)
    if kind == "ship":
        page.click("text=已出账", timeout=10000)
        page.wait_for_timeout(1500)
    set_date_range(page, date(year, month, start_day), date(year, month, end_day))
    page_size = set_page_size(page, 100)
    rows = []
    seen = set()
    page_number = 1
    expected_total = None
    while True:
        for attempt in range(3):
            payload = _query(page, endpoint) if page_number == 1 else _next(page, endpoint, page_number)
            result = payload.get("result") or {}
            total = result.get("total")
            data = result.get("resultList") if kind == "ledger" else result.get("list")
            if isinstance(total, int) and isinstance(data, list):
                break
            if payload.get("error_code") != 40002:
                raise ValueError(f"{kind}接口缺少 total/明细列表: {json.dumps(payload,ensure_ascii=False)[:1200]}")
            print(f"{kind} {year}-{month:02d} 第{attempt+1}次网络超时，重试")
            page.wait_for_timeout(1000 * (attempt + 1))
        else:
            raise RuntimeError(f"{kind} {year}-{month:02d} 连续3次网络超时")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError(f"{kind}翻页期间总数变化: {expected_total} -> {total}")
        for row in data:
            if kind == "ledger":
                flattened = flatten_ledger(row)
                key = (flattened["query_id"], flattened["trans_sn"], flattened["tx_time"], flattened["remark"], flattened["amount"])
            elif kind == "ship":
                flattened = flatten_ship(row)
                key = flattened["bill_id"]
            else:
                flattened = flatten_return(row)
                key = flattened["bill_id"]
            expected_month = f"{year}-{month:02d}"
            if not flattened["file_key"].endswith(expected_month):
                raise RuntimeError(f"{kind}返回账期错误: 期望{expected_month}, 实际{flattened['file_key']}")
            if key not in seen:
                seen.add(key)
                rows.append(flattened)
        if not data or page_number * page_size >= expected_total:
            break
        page_number += 1
    if len(rows) != expected_total:
        raise RuntimeError(f"{kind} {year}-{month:02d} 总数不一致: 页面={expected_total}, 抓取={len(rows)}")
    return rows


def replace_snapshot(con, table, columns, rows):
    if not rows:
        raise RuntimeError(f"{table} 快照为空，拒绝清空")
    placeholders = ",".join("?" for _ in columns)
    # 只替换本次抓到的月份（file_key），90 天窗口外已结算的历史月份保留在库里
    file_keys = sorted({row["file_key"] for row in rows})
    with con:
        for file_key in file_keys:
            con.execute(f"DELETE FROM {table} WHERE file_key=?", (file_key,))
        con.executemany(
            f"INSERT INTO {table}({','.join(columns)}) VALUES({placeholders})",
            [[row.get(name) for name in columns] for row in rows],
        )


def sync_financials(db_path, start=None, end=None):
    from playwright.sync_api import sync_playwright

    if end is None:
        end = date.today()
    if start is None:
        start = fetch_start()  # 滚动窗口：只抓最近 90 天

    con = sqlite3.connect(db_path)
    try:
        ensure_financial_schema(con)
        backup = backup_database(db_path, os.path.join(os.path.dirname(db_path), "backups"))
        snapshots = {"ledger": [], "ship_label": [], "return_label": []}
        with sync_playwright() as p:
            browser = ensure_cdp(p)  # 9222 不通时自动拉起专用 Edge
            ctx = browser.contexts[0]
            page = ctx.new_page()
            for kind, url, endpoint, table in [
                ("ledger", LEDGER_URL, LEDGER_API, "ledger"),
                ("ship", SHIP_URL, SHIP_API, "ship_label"),
                ("return", RETURN_URL, RETURN_API, "return_label"),
            ]:
                for year, month in months_between(start, end):
                    start_day = start.day if (year, month) == (start.year, start.month) else 1
                    last_day = calendar.monthrange(year, month)[1] if (year, month) < (end.year, end.month) else end.day
                    rows = collect_month(page, url, endpoint, year, month, start_day, last_day, kind)
                    snapshots[table].extend(rows)
                    print(f"{kind} {year}-{month:02d}: {len(rows)} 行")
        columns = {"ledger": LEDGER_COLUMNS, "ship_label": SHIP_COLUMNS, "return_label": RETURN_COLUMNS}
        for table, rows in snapshots.items():
            replace_snapshot(con, table, columns[table], rows)
        print(f"账务: {len(snapshots['ledger'])}; 发货面单: {len(snapshots['ship_label'])}; 退货面单: {len(snapshots['return_label'])}; 备份: {backup}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    args = parser.parse_args()
    sync_financials(os.path.abspath(args.db))


if __name__ == "__main__":
    main()
