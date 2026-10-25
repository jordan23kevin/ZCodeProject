# -*- coding: utf-8 -*-
"""从 sds.hlhfushi.cn/admin/orders 同步衣服成本（单价）到 temu_bills.db.sds_cost

规则（2026-10-25 用户确认）：
  - 先把每页条数切到 200 条/页，再从第 1 页开始遍历（列表按创建时间倒序）；
  - 增量模式（默认）：整页订单全部已入库即停止，之后每次只抓新增；
  - 全量模式（--full）：遍历全部页并回填/修正单价——真实单价永远优先于估价，
    sds 上后面出现金额，重跑全量即自动修正；
  - 没写单价的按货号前缀估价：DX=33 元，HX/RX=56 元（price_source='estimate'）。
"""
import argparse
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
SDS_URL = "https://sds.hlhfushi.cn/admin/orders"
PAGE_SIZE = 200


def estimate_price(design_code):
    code = (design_code or "").upper()
    if code.startswith(("HX", "RX")):
        return 56.0
    return 33.0


def parse_rows(page):
    """解析当前页 DOM：订单行(订单号/第三方单号) + 后随商品行(Extcode/sku/单价/数量)"""
    blocks = []
    current = None
    trs = page.evaluate("""() => [...document.querySelectorAll('table tbody tr')]
        .filter(e=>e.getClientRects().length).map(e=>e.innerText)""")
    for text in trs:
        if "第三方单号" in text or "订单号" in text:
            if current:
                blocks.append(current)
            po_m = re.search(r"第三方单号[:：]\s*(\S+)", text)
            no_m = re.search(r"订单号[:：]\s*(\d+)", text)
            current = {"po": po_m.group(1) if po_m else None,
                       "order_no": no_m.group(1) if no_m else None,
                       "items": []}
        elif "Extcode" in text and current is not None:
            ext_m = re.search(r"Extcode[:：]\s*([^\n]+)", text)
            sku_m = re.search(r"\bsku[:：]\s*(\d+)", text)
            price_m = re.search(r"单价[:：]\s*[￥¥]\s*([0-9]+(?:\.[0-9]+)?)", text)
            qty_m = re.search(r"数量[:：]\s*(\d+)", text)
            time_m = re.search(r"创建时间[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8})", text)
            current["items"].append({
                "extcode": ext_m.group(1).strip() if ext_m else None,
                "sku": sku_m.group(1) if sku_m else "",
                "unit_price": float(price_m.group(1)) if price_m else None,
                "qty": int(qty_m.group(1)) if qty_m else 1,
                "order_time": time_m.group(1) if time_m else None,
            })
    if current:
        blocks.append(current)
    return blocks


def upsert_rows(con, blocks, fetched_at):
    """入库；返回 (新增条数, 新回填真实价条数)"""
    inserted = corrected = 0
    for block in blocks:
        if not block["po"]:
            continue
        for item in block["items"]:
            extcode = item["extcode"] or ""
            design_code = extcode.split("-")[0] if extcode else None
            # 单价 0 元视为没写单价（未定价），按货号估价
            real = item["unit_price"] is not None and item["unit_price"] > 0
            price_source = "sds" if real else "estimate"
            unit_price = item["unit_price"] if real else estimate_price(design_code)
            old = con.execute(
                "SELECT price_source FROM sds_cost WHERE po=? AND sku=?",
                (block["po"], item["sku"])).fetchone()
            con.execute(
                """INSERT INTO sds_cost(po,order_no,sku,extcode,design_code,unit_price,price_source,qty,order_time,fetched_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(po,sku) DO UPDATE SET
                     order_no=excluded.order_no,
                     extcode=excluded.extcode,
                     design_code=excluded.design_code,
                     qty=excluded.qty,
                     order_time=COALESCE(excluded.order_time, sds_cost.order_time),
                     unit_price=CASE WHEN excluded.price_source='sds' THEN excluded.unit_price
                                     WHEN sds_cost.price_source='sds' AND sds_cost.unit_price>0 THEN sds_cost.unit_price
                                     ELSE excluded.unit_price END,
                     price_source=CASE WHEN excluded.price_source='sds'
                                        OR (sds_cost.price_source='sds' AND sds_cost.unit_price>0)
                                       THEN 'sds' ELSE 'estimate' END,
                     fetched_at=excluded.fetched_at""",
                (block["po"], block["order_no"], item["sku"], extcode, design_code,
                 unit_price, price_source, item["qty"], item["order_time"], fetched_at),
            )
            if old is None:
                inserted += 1
            elif real and old[0] != "sds":
                corrected += 1
    con.commit()
    return inserted, corrected


def ensure_schema(con):
    con.execute("""CREATE TABLE IF NOT EXISTS sds_cost(
        po TEXT NOT NULL, order_no TEXT, sku TEXT NOT NULL DEFAULT '',
        extcode TEXT, design_code TEXT, unit_price REAL, price_source TEXT,
        qty INTEGER, order_time TEXT, fetched_at TEXT,
        PRIMARY KEY(po, sku))""")
    con.commit()


def set_page_size_200(page):
    """把每页条数切到 200；失败按当前页大小继续。返回是否成功。"""
    try:
        sel = page.locator(".ant-pagination").locator("visible=true").first.locator(".ant-pagination-options .ant-select")
        sel.click(timeout=5000)
        page.wait_for_timeout(600)
        opt = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option",
                           has_text="200 条/页").first
        opt.click(timeout=5000)
        page.wait_for_timeout(2500)
        rows = page.evaluate("() => [...document.querySelectorAll('table tbody tr')].filter(e=>e.getClientRects().length).length")
        if rows < 100:
            print(f"切换 200 条/页后行数异常（{rows}），按当前页大小继续")
            return False
        return True
    except Exception as exc:
        print(f"切换 200 条/页失败（{exc}），按当前页大小继续")
        return False


def sync_sds_cost(db_path, full=False):
    from playwright.sync_api import sync_playwright

    con = sqlite3.connect(db_path)
    try:
        ensure_schema(con)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if "sds.hlhfushi.cn" in (pg.url or "")), None) or ctx.new_page()
            if "sds.hlhfushi.cn" not in (page.url or ""):
                page.goto(SDS_URL, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)

            ok = set_page_size_200(page)
            # 回到第 1 页（列表按创建时间倒序，增量从最新开始）
            try:
                page.locator(".ant-pagination").locator("visible=true").first.locator("li.ant-pagination-item-1").click(timeout=5000)
                page.wait_for_timeout(2000)
            except Exception:
                pass

            fetched_at = datetime.now(CST).isoformat(timespec="seconds")
            total_inserted = total_corrected = 0
            page_no = 1
            while True:
                blocks = parse_rows(page)
                pos = [b["po"] for b in blocks if b["po"]]
                page_items = sum(len(b["items"]) for b in blocks)
                print(f"第{page_no}页: {len(pos)} 单 / {page_items} 个商品行")
                inserted, corrected = upsert_rows(con, blocks, fetched_at)
                total_inserted += inserted
                total_corrected += corrected
                if not pos:
                    print("当前页没有可识别订单，停止")
                    break
                if not full and inserted == 0 and corrected == 0:
                    print("本页没有新增/更新（增量到位），停止遍历")
                    break
                nxt = page.locator(".ant-pagination").locator("visible=true").first.locator("li.ant-pagination-next")
                if nxt.get_attribute("class") and "ant-pagination-disabled" in (nxt.get_attribute("class") or ""):
                    print("已到最后一页")
                    break
                first_before = pos[0] if pos else None
                try:
                    nxt.click(timeout=5000)
                except Exception as exc:
                    print(f"点下一页失败（{exc}），停止")
                    break
                page.wait_for_timeout(2200)
                # 翻页没生效就停止，避免死循环
                blocks2 = parse_rows(page)
                pos2 = [b["po"] for b in blocks2 if b["po"]]
                if pos2 and pos2[0] == first_before:
                    print("翻页后内容未变化，停止")
                    break
                page_no += 1
        src = con.execute("SELECT price_source, COUNT(*), COALESCE(SUM(qty),0) FROM sds_cost GROUP BY price_source").fetchall()
        for source, cnt, qty_sum in src:
            print(f"库存: price_source={source}: {cnt} 行 (共 {qty_sum} 件)")
        print(f"完成: 新增 {total_inserted} 行, 回填真实价 {total_corrected} 行, 模式={'全量' if full else '增量'}")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    parser.add_argument("--full", action="store_true", help="全量遍历并修正单价（默认增量，整页已入库即停）")
    args = parser.parse_args()
    sync_sds_cost(os.path.abspath(args.db), full=args.full)


if __name__ == "__main__":
    main()
