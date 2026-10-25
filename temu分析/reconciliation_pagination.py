# -*- coding: utf-8 -*-
"""Temu 后台分页共享工具。

各页面每页条数上限（2026-10-25 用户确认）：
  - 卖家中心（订单、售后）与面单页：最大 100
  - 结算页：最大 200
订单、结算、售后、账务统一调用 set_max_page_size(page, 该页上限)；
找不到分页选择器时按当前页大小继续，不报错中断。

兼容两套分页组件（下拉选项均为 li[class*=cIL_item]）：
  - beast-core PGT：账务页(seller.kuajingmaihuo.com/labor/bill)、结算页(agentseller-eu/labor/settle)
  - index-module：发货面单页(labor/stml-logistics)、退货面单页(labor/stml-reverse-logistics)
两套触发器的 class 都含 "sizeSelect"，用 [class*=sizeSelect] 统一命中。
"""
import re


def set_max_page_size(page, max_size=100):
    """把页面每页条数切到不超过 max_size 的最大可用档位。
    返回实际生效的每页条数；找不到选择器/选项时按当前页大小继续。"""
    def _current_size():
        try:
            return page.evaluate("""() => {
              const e=[...document.querySelectorAll('[class*=sizeSelect]')].find(e=>e.getClientRects().length);
              if(!e)return 10;
              const input=e.querySelector('input');
              if(input&&parseInt(input.value,10))return parseInt(input.value,10);
              const m=(e.innerText||'').match(/\\d+/);
              return m?parseInt(m[0],10):10;
            }""")
        except Exception:
            return 10

    try:
        page.wait_for_selector("[class*='sizeSelect']", state="visible", timeout=5000)
        selector = page.locator("[class*='sizeSelect']").first
        current = (selector.inner_text() or "").replace("\n", " ").strip()
        if str(max_size) in current:
            return max_size
        selector.click(timeout=5000)
        page.wait_for_timeout(400)
        option_elements = page.locator("li[class*='cIL_item']")
        available = []
        for text in option_elements.all_inner_texts():
            text = text.strip()
            if text.isdigit():
                available.append(int(text))
        allowed = [size for size in available if size <= max_size]
        if allowed:
            choice = max(allowed)
            if str(choice) in current:
                return choice
            option = page.locator("li[class*='cIL_item']").filter(
                has_text=re.compile(rf"^{choice}$")).first
            option.click(timeout=5000)
            page.wait_for_timeout(1000)
            return choice
        print(f"页面没有 ≤{max_size} 的分页选项（可选: {sorted(set(available))}），按当前页大小继续")
    except Exception as exc:
        print(f"设置最大分页失败（上限 {max_size}），使用当前分页: {exc}")
    return _current_size()
