# -*- coding: utf-8 -*-
"""欧区结算自动同步：对账中心(seller.kuajingmaihuo.com/labor/bill) 导出→下载→入库

流程（2026-10-25 用户指认来源页）：
  1. 逐月设置日期（窗口=最近90天对齐月初）；
  2. 点「导出」→ 选「导出列表 + 账务详情」→ 确认；
  3. 打开「导出历史」，等"查询时间=当月"的新记录生成；
  4. 点该记录的「下载财务明细(欧区)」，保存到 E:\\Temu账单\\auto_eu\\；
  5. 解析入库 settlement_eu + violation（file_key=europe|YYYY-MM 整月替换）。
已有当月生成且未过期的记录直接复用下载，不重复发起导出。
"""
import argparse
import glob
import json
import os
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from reconciliation_sync import fetch_start, months_between, set_date_range
from sync_aftersales import backup_database, ensure_cdp

CST = timezone(timedelta(hours=8))
BILL_URL = "https://seller.kuajingmaihuo.com/labor/bill"
SAVE_DIR = r"E:\Temu账单\auto_eu"

EU_COLUMNS = ["file_key", "flow_id", "batch_no", "po", "doc_no", "tx_type", "amount", "sku_id", "sku_name",
              "sku_code", "qty", "declared_price", "is_promo", "currency", "total_declared", "coupon",
              "shop_discount", "price_discount", "ship_fee_relief", "arrive_time", "remark", "source_file"]
VIO_COLUMNS = ["file_key", "violation_id", "po", "vtype", "amount", "currency", "tx_time", "source_file"]

JS_CLICK_TEXT = """(txt) => {
  const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&e.textContent.trim()===txt&&e.getClientRects().length);
  if(!els.length) return 'NOT_FOUND:'+txt;
  els[els.length-1].click();
  return 'CLICKED:'+txt;
}"""

GET_PANEL = """() => {
  const els=[...document.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.includes('导出历史')&&e.getClientRects().length);
  if(!els.length) return '';
  let node = els[els.length-1];
  for (let i=0;i<8&&node.parentElement;i++){ node=node.parentElement; if(node.innerText.length>300) break; }
  return node.innerText;
}"""


def f2num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).replace(",", "").replace("¥", "").replace("￥", "").strip()
    try:
        return float(t)
    except ValueError:
        return 0.0


def load_bill_page(page):
    page.goto(BILL_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)
    if "auth/authentication" in (page.url or ""):
        raise RuntimeError("商家中心登录失效（seller.kuajingmaihuo.com）")


def click_text(page, txt):
    return page.evaluate(JS_CLICK_TEXT, txt)


def open_history(page):
    """确保导出历史面板打开并刷新"""
    panel = page.evaluate(GET_PANEL)
    if "账务明细生成时间" not in panel:
        click_text(page, "导出历史")
        page.wait_for_timeout(2000)
    else:
        click_text(page, "刷新")
        page.wait_for_timeout(2000)
    return page.evaluate(GET_PANEL)


def find_entry(panel, s, e):
    """在面板文本里找覆盖目标月的记录（返回 True/False）"""
    expect = f"{s:%Y-%m-%d} 00:00:00 ~ {e:%Y-%m-%d} 23:59:59"
    return expect in panel


JS_STATE = """(expect) => {
  // 从"查询时间"叶子向上找记录卡片，其中**可用（非 disabled）**的欧区按钮才算 READY；
  // disabled = 生成中或已失效
  let generating = false;
  const timeEls=[...document.querySelectorAll('*')].filter(e=>
    e.children.length===0&&e.textContent.includes(expect)&&e.textContent.trim().length<expect.length+16&&e.getClientRects().length);
  for (const t of timeEls) {
    let node = t;
    for (let i=0;i<10&&node.parentElement;i++) {
      node = node.parentElement;
      const btns=[...node.querySelectorAll('button')].filter(b=>b.getClientRects().length&&
        [...b.querySelectorAll('*')].some(e=>e.textContent.trim()==='下载财务明细(欧区)'));
      for (const btn of btns) {
        if (!btn.disabled) {
          document.querySelectorAll('[data-eu-dl]').forEach(e=>e.removeAttribute('data-eu-dl'));
          btn.setAttribute('data-eu-dl','1');
          btn.scrollIntoView({block:'center'});
          return JSON.stringify({state:'READY'});
        }
        generating = true;
      }
    }
  }
  const panel=[...document.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.includes('导出历史')&&e.getClientRects().length);
  let p='';
  if(panel.length){let node=panel[panel.length-1];for(let i=0;i<8&&node.parentElement;i++){node=node.parentElement;if(node.innerText.length>300)break;}p=node.innerText||'';}
  return JSON.stringify({state: generating ? 'GENERATING' : (p.includes(expect) ? 'GENERATING' : 'ABSENT')});
}"""


def download_eu(page, s, e, save_path, since_ts):
    """在导出历史里找到目标月记录，等其生成完成（出现可点的'下载财务明细(欧区)'），
    用真实鼠标事件点击（合成点击无用户手势会被 Edge 拦下载），
    然后轮询 artifacts/Downloads 目录，等新 xlsx 落盘后移动到目标路径。"""
    expect = f"{s:%Y-%m-%d} 00:00:00 ~ {e:%Y-%m-%d} 23:59:59"
    deadline = time.time() + 150
    pos = None
    while time.time() < deadline:
        dismiss_popup(page)
        raw = page.evaluate(JS_STATE, expect)
        info = json.loads(raw)
        if info.get("state") == "READY":
            pos = info
            break
        click_text(page, "刷新")   # 刷新导出历史
        page.wait_for_timeout(3000)
    else:
        raise RuntimeError(f"欧区明细生成超时（状态 {pos}）: {expect}")
    page.bring_to_front()  # 后台标签页的下载会被 Edge 拦截，必须置前台
    # 给**可用（非 disabled）**的欧区下载按钮打标记，locator.click() 触发完整真实点击序列
    marked = page.evaluate("""(expect) => {
      const timeEls=[...document.querySelectorAll('*')].filter(e=>
        e.children.length===0&&e.textContent.includes(expect)&&e.textContent.trim().length<expect.length+16&&e.getClientRects().length);
      for (const t of timeEls) {
        let node = t;
        for (let i=0;i<10&&node.parentElement;i++) {
          node = node.parentElement;
          const btns=[...node.querySelectorAll('button')].filter(b=>!b.disabled&&b.getClientRects().length&&
            [...b.querySelectorAll('*')].some(e=>e.textContent.trim()==='下载财务明细(欧区)'));
          if (btns.length) {
            document.querySelectorAll('[data-eu-dl]').forEach(e=>e.removeAttribute('data-eu-dl'));
            btns[0].setAttribute('data-eu-dl','1');
            btns[0].scrollIntoView({block:'center'});
            return true;
          }
        }
      }
      return false;
    }""", expect)
    if not marked:
        raise RuntimeError("欧区下载按钮标记失败")
    # 下载捕获：先等 playwright download 事件，再兜底轮询 artifacts/Downloads 目录
    deadline = time.time() + 120
    got = None
    try:
        with page.expect_download(timeout=60000) as dl_info:
            page.locator("[data-eu-dl='1']").click(timeout=15000)
        got = dl_info.value
        got.save_as(save_path)
        return save_path
    except Exception as exc:
        print(f"[eu-dl] download 事件未捕获（{str(exc)[:60]}），轮询目录兜底")
    while time.time() < deadline:
        temp_root = os.environ.get("TEMP", r"C:\Users\Administrator\AppData\Local\Temp")
        candidates = [f for d in glob.glob(os.path.join(temp_root, "playwright-artifacts-*"))
                      for f in glob.glob(os.path.join(d, "*"))]
        candidates += glob.glob(r"C:\Users\Administrator\Downloads\*.xlsx")
        candidates += glob.glob(os.path.join(SAVE_DIR, "*.xlsx"))
        fresh = [f for f in candidates if os.path.isfile(f) and os.path.getmtime(f) > since_ts]
        if fresh:
            newest = max(fresh, key=os.path.getmtime)
            time.sleep(1.5)
            try:
                with open(newest, "rb") as fh:
                    head = fh.read(2)
            except OSError:
                continue
            if head != b"PK":
                continue
            if os.path.abspath(newest) == os.path.abspath(save_path):
                return save_path
            if os.path.exists(save_path):
                os.remove(save_path)
            import shutil
            shutil.move(newest, save_path)
            return save_path
        time.sleep(2)
    raise RuntimeError("下载超时（事件与目录轮询均未捕获文件）")


def dismiss_popup(page):
    """点掉'导出已完成'等提示弹窗（含'我知道了'按钮），存在则返回 True"""
    r = click_text(page, "我知道了")
    if r.startswith("CLICKED"):
        page.wait_for_timeout(1200)
        return True
    return False


def export_month(page, s, e):
    """对当前日期区间发起一次导出（选'导出列表 + 账务详情'），并等'导出已完成'弹窗点掉"""
    click_text(page, "导出")
    page.wait_for_timeout(1200)
    r = click_text(page, "导出列表 + 账务详情")
    if r.startswith("NOT_FOUND"):
        raise RuntimeError(f"导出弹窗选项缺失: {r}")
    page.wait_for_timeout(400)
    click_text(page, "确认")
    page.wait_for_timeout(1500)
    # 等待导出完成的提示弹窗（最多 120s），出现就点掉"我知道了"
    deadline = time.time() + 120
    while time.time() < deadline:
        if dismiss_popup(page):
            print("  导出完成（已点'我知道了'）")
            return
        page.wait_for_timeout(3000)
    print("  未等到'导出已完成'弹窗（可能已在导出历史就绪，继续）")


def import_eu_xlsx(con, path, file_key):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    n_set = n_vio = 0
    cur = con.cursor()
    cur.execute("DELETE FROM settlement_eu WHERE file_key=?", (file_key,))
    cur.execute("DELETE FROM violation WHERE file_key=?", (file_key,))
    for sn in wb.sheetnames:
        rows = [list(r) for r in wb[sn].iter_rows(values_only=True)]
        if sn == "结算":
            for r in rows[2:]:
                if not r or not r[0]:
                    continue
                cur.execute(
                    f"""INSERT OR IGNORE INTO settlement_eu({','.join(EU_COLUMNS)}) VALUES({','.join('?' for _ in EU_COLUMNS)})""",
                    (file_key, r[0], r[1], r[2], r[3], r[4], f2num(r[5]), r[6], r[7], r[8],
                     int(float(r[9])) if r[9] else None, f2num(r[10]), r[11], r[12], f2num(r[13]),
                     f2num(r[14]), f2num(r[15]), f2num(r[16]), f2num(r[17]), r[18], r[19],
                     os.path.basename(path)))
                n_set += 1
        elif sn.startswith("支出"):
            for r in rows[1:]:
                if not r or not r[0]:
                    continue
                cur.execute(
                    f"""INSERT OR REPLACE INTO violation({','.join(VIO_COLUMNS)}) VALUES({','.join('?' for _ in VIO_COLUMNS)})""",
                    (file_key, r[0], r[1], r[2], f2num(r[3]), r[4], r[5], os.path.basename(path)))
                n_vio += 1
    wb.close()
    con.commit()
    return n_set, n_vio


def close_drawer(page):
    """关掉导出历史抽屉（Escape + 关闭按钮 + 遮罩，多重手段）"""
    closed = page.evaluate("""() => {
      const wr=[...document.querySelectorAll('[data-testid="beast-core-drawer"]')].filter(e=>e.getClientRects().length);
      if(!wr.length) return false;
      // 1) 抽屉内关闭按钮
      const btn=[...wr[0].querySelectorAll('[class*=close],[class*=Close]')].find(e=>e.getClientRects().length);
      if(btn){btn.click();return true}
      // 2) 点遮罩
      const masks=[...document.querySelectorAll('[class*=Drawer_mask]')].filter(e=>e.getClientRects().length);
      if(masks.length){masks[0].click();return true}
      return false
    }""")
    if not closed:
        page.keyboard.press("Escape")
    page.wait_for_timeout(1200)
    # 验证已关闭
    still = page.evaluate("""() => [...document.querySelectorAll('[data-testid="beast-core-drawer"]')].filter(e=>e.getClientRects().length).length""")
    if still:
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
    return not still


def sync_eu_settlement(db_path):
    from playwright.sync_api import sync_playwright

    os.makedirs(SAVE_DIR, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE IF NOT EXISTS settlement_eu(
        file_key TEXT, flow_id TEXT, batch_no TEXT, po TEXT, doc_no TEXT, tx_type TEXT,
        amount REAL, sku_id TEXT, sku_name TEXT, sku_code TEXT, qty INTEGER, declared_price REAL,
        is_promo TEXT, currency TEXT, total_declared REAL, coupon REAL, shop_discount REAL,
        price_discount REAL, ship_fee_relief REAL, arrive_time TEXT, remark TEXT, source_file TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS violation(
        file_key TEXT, violation_id TEXT, po TEXT, vtype TEXT, amount REAL,
        currency TEXT, tx_time TEXT, source_file TEXT)""")
    con.commit()
    try:
        with sync_playwright() as p:
            browser = ensure_cdp(p)
            ctx = browser.contexts[0]
            page = ctx.new_page()  # 独立标签页，防干扰
            try:
                load_bill_page(page)
                total_set = total_vio = 0
                for year, month in months_between(fetch_start(), date.today()):
                    import calendar
                    close_drawer(page)  # 抽屉开着会挡住日期/导出操作
                    s = date(year, month, 1)
                    e = min(date(year, month, calendar.monthrange(year, month)[1]), date.today())
                    set_date_range(page, s, e)
                    page.wait_for_timeout(800)
                    panel = open_history(page)
                    if not find_entry(panel, s, e):
                        export_month(page, s, e)
                        # 轮询等记录生成
                        deadline = time.time() + 120
                        while time.time() < deadline:
                            panel = open_history(page)
                            if find_entry(panel, s, e):
                                break
                            page.wait_for_timeout(3000)
                        else:
                            raise RuntimeError(f"欧区导出超时未生成: {s}~{e}")
                    save_path = os.path.join(SAVE_DIR, f"europe_{year}-{month:02d}.xlsx")
                    since_ts = time.time()  # 只认点击之后新落盘的文件
                    download_eu(page, s, e, save_path, since_ts)
                    n_set, n_vio = import_eu_xlsx(con, save_path, f"europe|{year}-{month:02d}")
                    total_set += n_set
                    total_vio += n_vio
                    print(f"欧区 {year}-{month:02d}: 结算 {n_set} 行, 违规 {n_vio} 行 -> {save_path}")
            finally:
                try:
                    page.close()
                except Exception:
                    pass
        print(f"欧区同步完成: 结算 {total_set} 行, 违规 {total_vio} 行, 窗口=最近90天(月初对齐)")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("TEMU_BILLS_DB", r"E:\Temu账单\temu_bills.db"))
    args = parser.parse_args()
    sync_eu_settlement(os.path.abspath(args.db))


if __name__ == "__main__":
    main()
