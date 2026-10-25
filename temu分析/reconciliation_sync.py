# -*- coding: utf-8 -*-
import argparse
import calendar
import json
import os
import sqlite3
from datetime import date, datetime, timedelta, timezone

from reconciliation_pagination import set_max_page_size
from sync_aftersales import backup_database, ensure_cdp, wait_api

ORDERS_URL = "https://agentseller-eu.temu.com/mmsos/orders.html?fulfillmentMode=9&pageNumber=1&pageSize=20&queryType=0&sortType=1&timeZone=UTC%2B8&sellerNoteLabelList=&packageAbnormalTypeList="
ORDER_API = "/kirogi/bg/mms/recentOrderList"
CST = timezone(timedelta(hours=8))
# 抓数窗口：平台最晚结算 90 天、可用退款 90 天，只抓最近 90 天（2026-10-25 用户确认）
SYNC_DAYS = 90


def fetch_start(days=SYNC_DAYS):
    """滚动抓数窗口起点（含）。已结算的历史月份定格在库里，不重抓。"""
    return date.today() - timedelta(days=days)


def months_between(start_day, end_day):
    """闭区间内逐月 (year, month) 列表"""
    months = []
    year, month = start_day.year, start_day.month
    while (year, month) <= (end_day.year, end_day.month):
        months.append((year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months
ORDER_STATUSES = {1: "平台处理中", 2: "待发货", 3: "已取消", 4: "已发货", 5: "已签收"}
ORDER_COLUMNS = [
    "sub_order_no", "sku_id", "order_no", "site", "order_status", "batch_order_no", "sub_status", "qty",
    "product_name", "skc_id", "spu_id", "sku_code", "attrs", "carrier", "ship_wh", "tracking_no", "logistics",
    "country", "created_at", "confirmed_at", "ship_deadline", "shipped_at", "signed_at", "remark", "source_file",
]


def flatten_order_item(item, source_file="api:recentOrderList"):
    parent = item.get("parentOrderMap") or {}
    waybills = parent.get("waybillInfoList") or []
    waybill = waybills[0] if waybills else {}
    rows = []
    for order in item.get("orderList") or []:
        products = order.get("productInfoList") or []
        for product in products:
            sku_id = product.get("productSkuId")
            if not sku_id:
                raise ValueError(f"订单缺少 productSkuId: {parent.get('parentOrderSn')}")
            status_code = parent.get("parentOrderStatus") or order.get("orderStatus")
            rows.append({
                "sub_order_no": order.get("orderSn"),
                "sku_id": str(sku_id),
                "order_no": parent.get("parentOrderSn"),
                "site": parent.get("siteName") or parent.get("regionName1"),
                "order_status": ORDER_STATUSES.get(status_code, str(status_code) if status_code is not None else None),
                "batch_order_no": None,
                "sub_status": ORDER_STATUSES.get(order.get("orderStatus"), ORDER_STATUSES.get(status_code)),
                "qty": product.get("productQuantity") or order.get("quantity") or order.get("fulfillmentQuantity"),
                "product_name": order.get("goodsName"),
                "skc_id": product.get("productSkcId"),
                "spu_id": product.get("productSpuId"),
                "sku_code": (order.get("extCodeList") or [None])[0],
                "attrs": order.get("spec") or order.get("originalSpecName"),
                "carrier": waybill.get("shipCompanyName"),
                "ship_wh": order.get("warehouseName"),
                "tracking_no": waybill.get("trackingNumber"),
                "logistics": waybill.get("shipCompanyName"),
                "country": parent.get("regionName1"),
                "created_at": parent.get("parentOrderTimeStr"),
                "confirmed_at": parent.get("parentConfirmTimeStr"),
                "ship_deadline": parent.get("expectShipLatestTimeStr"),
                "shipped_at": parent.get("parentShippingTimeStr"),
                "signed_at": parent.get("parentReceiptTimeStr"),
                "remark": json.dumps(parent.get("sellerNoteDTO"), ensure_ascii=False) if parent.get("sellerNoteDTO") else None,
                "source_file": source_file,
            })
    return rows


def upsert_orders(con, rows):
    if not rows:
        return
    placeholders = ",".join("?" for _ in ORDER_COLUMNS)
    updates = ",".join(
        f"{name}=COALESCE(excluded.{name},orders.{name})" for name in ORDER_COLUMNS
        if name not in ("sub_order_no", "sku_id")
    )
    sql = (
        f"INSERT INTO orders({','.join(ORDER_COLUMNS)}) VALUES({placeholders}) "
        f"ON CONFLICT(sub_order_no,sku_id) DO UPDATE SET {updates}"
    )
    with con:
        con.executemany(sql, [[row.get(name) for name in ORDER_COLUMNS] for row in rows])


def _click_query(page):
    return wait_api(page, ORDER_API, lambda: page.evaluate("""
      () => {const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='查询');
      if(!els.length)throw new Error('未找到订单查询按钮');els[0].click();}
    """))


def _click_next(page):
    return wait_api(page, ORDER_API, lambda: page.evaluate("""
      () => {const e=document.querySelector('li[class*=PGT_next]:not([class*=PGT_disabled])');
      if(!e)throw new Error('订单下一页不可用');e.click();}
    """))


def _load_orders_page(page):
    page.goto(ORDERS_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    if "auth/authentication" in page.url:
        raise RuntimeError("欧区代理后台登录失效")


def _flatten_page_items(items):
    rows = []
    for item in items:
        rows.extend(flatten_order_item(item))
    return rows


def collect_orders(page, known_orders=None, full=False):
    """抓订单（2026-10-25 用户确认，取消前端日期筛选依赖）：
    - 增量（默认）：每页 500 条从最新页开始，每页主单号与数据库撞库，
      整页均已同步即停；新订单入库自带 created_at，利润归月与按日期筛选一致。
    - full=True 兜底：100 条/页 + 逐月设日期全量翻页（500 档会重置日期筛选，
      且页面默认时间窗只覆盖约 30 天，故全量走已验证的逐月方式）。"""
    _load_orders_page(page)
    rows = []
    seen_parents = set()
    if full:
        page_size = set_max_page_size(page, 100)
        page.wait_for_timeout(1500)
        end_day = date.today()
        start_day = fetch_start()
        for year, month in months_between(start_day, end_day):
            s = date(year, month, start_day.day) if (year, month) == (start_day.year, start_day.month) else date(year, month, 1)
            e = date(year, month, end_day.day) if (year, month) == (end_day.year, end_day.month) else date(year, month, calendar.monthrange(year, month)[1])
            set_date_range(page, s, e)
            page.wait_for_timeout(800)
            page_number = 1
            prev_first = None
            while True:
                payload = _click_query(page) if page_number == 1 else _click_next(page)
                items = (payload.get("result") or {}).get("pageItems")
                if not isinstance(items, list):
                    raise ValueError("订单接口缺少 pageItems")
                if not items:
                    break
                page_parents = []
                for item in items:
                    parent = (item.get("parentOrderMap") or {}).get("parentOrderSn")
                    if not parent:
                        raise ValueError("订单缺少 parentOrderSn")
                    page_parents.append(parent)
                if prev_first and page_parents and page_parents[0] == prev_first:
                    raise RuntimeError("翻页未生效（内容未变化）")
                prev_first = page_parents[0]
                seen_parents.update(page_parents)
                rows.extend(_flatten_page_items(items))
                nxt = page.locator("li[class*=PGT_next]")
                if nxt.count() == 0:
                    break  # 单页结果，无翻页器
                nxt_cls = nxt.get_attribute("class") or ""
                if "PGT_disabled" in nxt_cls:
                    break
                page_number += 1
            print(f"全量 {s}~{e}: 累计扫描 {len(seen_parents)} 单")
        return rows, seen_parents, set()

    # 增量撞库
    page_size = set_max_page_size(page, 500)  # 订单页上限 500 条/页（尽力切，末页判断不依赖它）
    page.wait_for_timeout(1500)   # 等切换条数后的重新加载完成
    known = known_orders or set()
    new_parents = set()
    page_number = 1
    prev_first = None
    while True:
        payload = _click_query(page) if page_number == 1 else _click_next(page)
        result = payload.get("result") or {}
        items = result.get("pageItems")
        if not isinstance(items, list):
            raise ValueError("订单接口缺少 pageItems")
        if not items:
            break
        page_parents = []
        for item in items:
            parent = (item.get("parentOrderMap") or {}).get("parentOrderSn")
            if not parent:
                raise ValueError("订单缺少 parentOrderSn")
            page_parents.append(parent)
        if prev_first and page_parents and page_parents[0] == prev_first:
            raise RuntimeError("翻页未生效（内容未变化）")
        prev_first = page_parents[0]
        new_here = [p for p in page_parents if p not in known]
        seen_parents.update(page_parents)
        new_parents.update(new_here)
        rows.extend(_flatten_page_items(items))
        print(f"第{page_number}页: {len(page_parents)} 单 / 新单 {len(new_here)}")
        if not new_here:
            print("整页均已同步（撞库命中），停止")
            break
        # 末页判断看「下一页」按钮状态（不依赖档位值，与页面真实状态一致）
        nxt = page.locator("li[class*=PGT_next]")
        if nxt.count() == 0:
            break  # 单页结果，无翻页器
        nxt_cls = nxt.get_attribute("class") or ""
        if "PGT_disabled" in nxt_cls:
            break
        page_number += 1
    return rows, seen_parents, new_parents


def sync_orders(db_path, full=False):
    from playwright.sync_api import sync_playwright

    backup = backup_database(db_path, os.path.join(os.path.dirname(db_path), "backups"))
    con = sqlite3.connect(db_path)
    try:
        known = {row[0] for row in con.execute("SELECT DISTINCT order_no FROM orders")}
        with sync_playwright() as p:
            browser = ensure_cdp(p)  # 9222 不通时自动拉起专用 Edge
            ctx = browser.contexts[0]
            # 独立新标签页抓取，避免与用户手动操作互相干扰；结束自动关闭
            page = ctx.new_page()
            try:
                rows, seen, new = collect_orders(page, known_orders=known, full=full)
            finally:
                try:
                    page.close()
                except Exception:
                    pass
        upsert_orders(con, rows)
        print(f"撞库: 库内已有主单 {len(known)}; 本次扫描 {len(seen)}; 新增主单 {len(new)}; "
              f"入库SKU行 {len(rows)}; 模式={'全量' if full else '增量撞库'}; 备份: {backup}")
    finally:
        con.close()


def set_date_range(page, start_day, end_day):
    if not page.evaluate("""() => {const e=document.querySelector('[class*=RPR_outerPickerWrapper]');return !!(e&&e.getClientRects().length)}"""):
        page.click('input[data-testid="beast-core-rangePicker-htmlInput"]')
        page.wait_for_timeout(1000)

    def has_month(month):
        return page.evaluate("""(month) => [...document.querySelectorAll('[class*=RPR_dateText]')].some(e=>e.getClientRects().length>0&&e.innerText.trim()===month+'月')""", month)

    def navigate(month, direction):
        for _ in range(30):
            if has_month(month):
                return
            page.evaluate("""(direction) => {const e=document.querySelector(`svg[data-testid="beast-core-icon-${direction}"][class*=RPR_iconPrevNext]`);if(!e)throw new Error('月份导航不可用');e.dispatchEvent(new MouseEvent('click',{bubbles:true}))}""", direction)
            page.wait_for_timeout(250)
        raise RuntimeError(f"无法导航到月份: {month}")

    def click_day(month, day):
        clicked = page.evaluate("""([month,day]) => {
          const headers=[...document.querySelectorAll('[class*=RPR_panelHeader]')].filter(e=>e.getClientRects().length>0);
          const index=headers.findIndex(e=>{const t=e.querySelector('[class*=RPR_dateText]');return t&&t.innerText.trim()===month+'月'});
          if(index<0)return false;
          const tables=[...document.querySelectorAll('[class*=RPR_tableWrapper]')].filter(e=>e.getClientRects().length>0);
          const table=tables[index];
          if(!table)return false;
          const cells=[...table.querySelectorAll('[class*=RPR_tdDay]')].filter(e=>!String(e.className).includes('RPR_outOfMonth')&&e.innerText.trim()===String(day));
          if(!cells.length)return false;
          cells[0].click();return true;
        }""", [month, day])
        if not clicked:
            raise RuntimeError(f"无法选择日期: {month}月{day}日")
        page.wait_for_timeout(400)

    if start_day.year != end_day.year or start_day.month != end_day.month:
        raise ValueError("跨月账期请逐月抓取")
    visible_months = page.evaluate("""() => [...document.querySelectorAll('[class*=RPR_dateText]')].filter(e=>e.getClientRects().length>0).map(e=>parseInt(e.innerText,10)).filter(Number.isFinite)""")
    direction = "left" if visible_months and start_day.month < min(visible_months) else "right"
    navigate(start_day.month, direction)
    click_day(start_day.month, start_day.day)
    click_day(end_day.month, end_day.day)
    # 部分场景选完起止日期后面板会自动关闭，此时区间已生效，无需再点确认
    picker_open = page.evaluate("""() => {const e=document.querySelector('[class*=RPR_outerPickerWrapper]');return !!(e&&e.getClientRects().length)}""")
    if picker_open:
        page.evaluate("""() => {const root=document.querySelector('[class*=RPR_outerPickerWrapper]');const els=[...root.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()==='确认'&&e.getClientRects().length>0);if(!els.length)throw new Error('未找到日期确认按钮');els[els.length-1].click()}""")
    page.wait_for_timeout(500)
    value = page.locator('input[data-testid="beast-core-rangePicker-htmlInput"]').input_value()
    expected = f"{start_day:%Y-%m-%d} ~ {end_day:%Y-%m-%d}"
    if value != expected:
        raise RuntimeError(f"日期设置失败: 期望 {expected}, 实际 {value}")
    page.keyboard.press("Escape")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    parser.add_argument("--source", choices=["orders"], default="orders")
    parser.add_argument("--full", action="store_true", help="全量翻页（默认增量撞库，整页已同步即停）")
    args = parser.parse_args()
    if args.source == "orders":
        sync_orders(os.path.abspath(args.db), full=args.full)


if __name__ == "__main__":
    main()
