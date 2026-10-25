# -*- coding: utf-8 -*-
import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from reconciliation_pagination import set_max_page_size
from sync_aftersales import backup_database, wait_api

ORDERS_URL = "https://agentseller-eu.temu.com/mmsos/orders.html?fulfillmentMode=9&pageNumber=1&pageSize=20&queryType=0&sortType=1&timeZone=UTC%2B8&sellerNoteLabelList=&packageAbnormalTypeList="
ORDER_API = "/kirogi/bg/mms/recentOrderList"
CST = timezone(timedelta(hours=8))
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


def collect_orders(page):
    page.goto(ORDERS_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    if "auth/authentication" in page.url:
        raise RuntimeError("欧区代理后台登录失效")
    page_size = set_max_page_size(page, 100)  # 卖家中心订单页上限 100
    rows = []
    parents = set()
    page_number = 1
    expected_total = None
    while True:
        payload = _click_query(page) if page_number == 1 else _click_next(page)
        result = payload.get("result") or {}
        total = result.get("totalItemNum")
        items = result.get("pageItems")
        if not isinstance(total, int) or not isinstance(items, list):
            raise ValueError("订单接口缺少 totalItemNum/pageItems")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError(f"订单翻页期间总数变化: {expected_total} -> {total}")
        for item in items:
            parent = (item.get("parentOrderMap") or {}).get("parentOrderSn")
            if not parent:
                raise ValueError("订单缺少 parentOrderSn")
            parents.add(parent)
            rows.extend(flatten_order_item(item))
        if not items or page_number * page_size >= expected_total:
            break
        page_number += 1
    if len(parents) != expected_total:
        raise RuntimeError(f"订单总数不一致: 页面={expected_total}, 抓取={len(parents)}")
    return rows


def sync_orders(db_path):
    from playwright.sync_api import sync_playwright

    backup = backup_database(db_path, os.path.join(os.path.dirname(db_path), "backups"))
    con = sqlite3.connect(db_path)
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if "orders.html" in (pg.url or "")), None) or ctx.new_page()
            rows = collect_orders(page)
        upsert_orders(con, rows)
        parents = {row["order_no"] for row in rows}
        print(f"订单主单: {len(parents)}; 订单SKU行: {len(rows)}; 备份: {backup}")
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
    args = parser.parse_args()
    if args.source == "orders":
        sync_orders(os.path.abspath(args.db))


if __name__ == "__main__":
    main()
