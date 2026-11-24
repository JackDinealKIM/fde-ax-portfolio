#!/usr/bin/env python3
"""Headless verification for documents/fde-portfolio-demo/index.html.

Checks: zero console/page errors, 3D hero renders, industry tabs switch,
question buttons change answer + sources, free-text search (match and no-evidence
paths), ROI sliders/packages update numbers, no horizontal overflow on mobile.
Writes screenshots to screenshots/.

Usage: python3 scripts/verify.py
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = (ROOT / "index.html").as_uri()
SHOTS = ROOT / "screenshots"
SHOTS.mkdir(exist_ok=True)

results = {"url": URL, "checks": [], "console_errors": [], "page_errors": []}


def check(name, ok, detail=""):
    results["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("[PASS] " if ok else "[FAIL] ") + name + (" — " + str(detail)[:200] if detail else ""))


def txt(page, sel):
    return page.locator(sel).inner_text().strip()


def auto_scroll(pg, step=700):
    """Scroll through the page like a visitor so reveal animations trigger."""
    h = pg.evaluate("document.body.scrollHeight")
    y = 0
    while y < h:
        pg.mouse.wheel(0, step)
        pg.wait_for_timeout(90)
        y += step
    pg.wait_for_timeout(600)
    pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(500)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--enable-unsafe-swiftshader", "--use-gl=swiftshader"])

        # ---------------- desktop ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: results["console_errors"].append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: results["page_errors"].append(str(e)))
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(2200)

        hero_cls = page.locator("#hero3d").get_attribute("class") or ""
        check("3D hero initialised", "ready" in hero_cls or "fallback" in hero_cls, hero_cls)
        check("hero uses WebGL (not fallback)", "ready" in hero_cls, hero_cls)
        labels = page.locator(".nlabel").count()
        check("hero labels present", labels == 5, f"{labels} labels")
        page.screenshot(path=str(SHOTS / "01-desktop-hero.png"))

        # initial answer auto-runs first commerce question
        q0 = txt(page, "#aQ")
        check("commerce Q1 auto-answer", "안전재고" in q0, q0)
        check("citation badges rendered", page.locator(".a-text sup.cite").count() >= 2,
              page.locator(".a-text sup.cite").count())
        src_names = page.locator(".src .name").all_inner_texts()
        check("source badges listed", len(src_names) >= 2, src_names)
        check("confidence chip", page.locator("#aBadges .chip.ok").count() == 1,
              txt(page, "#aBadges"))

        page.locator("#demo").scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        page.locator(".demo-shell").screenshot(path=str(SHOTS / "02-desktop-demo.png"))

        # question button 2
        first_q = txt(page, "#aQ")
        page.locator('#qlist button[data-i="1"]').click()
        page.wait_for_timeout(1100)
        second_q = txt(page, "#aQ")
        second_src = page.locator(".src .name").all_inner_texts()
        check("question button changes answer", first_q != second_q and "반품" in second_q, second_q)
        check("sources change with question", second_src != src_names, second_src)

        # tab switch to office
        page.locator("#tab-office").click()
        page.wait_for_timeout(1200)
        office_q = txt(page, "#aQ")
        office_src = page.locator(".src .name").all_inner_texts()
        check("office tab switches preset", "원천징수" in office_q, office_q)
        check("office tab aria-selected", page.locator("#tab-office").get_attribute("aria-selected") == "true", "")
        check("office sources differ", office_src != src_names, office_src)
        check("answer panel labelled by active tab",
              page.locator("#kbPanel").get_attribute("aria-labelledby") == "tab-office", "")

        # free-text search — matched
        page.locator("#qInput").fill("연차")
        page.locator("#searchForm button").click()
        page.wait_for_timeout(1200)
        match_q = txt(page, "#aQ")
        check("free-text search matches", "연차" in match_q, match_q)

        # free-text search — no evidence
        page.locator("#qInput").fill("우리 회사 주차장 규정 알려줘")
        page.locator("#searchForm button").click()
        page.wait_for_timeout(1300)
        empty_foot = txt(page, "#aFoot")
        check("no-evidence path shows 근거 없음", "근거 없음" in empty_foot, empty_foot)
        check("no-evidence warning chip", page.locator("#aBadges .chip.warn").count() == 1, txt(page, "#aBadges"))
        check("no sources shown on no-evidence", page.locator("#aSources").is_hidden(), "")
        page.locator(".demo-shell").screenshot(path=str(SHOTS / "03-desktop-demo-no-evidence.png"))

        # back to commerce, search 반품
        page.locator("#tab-commerce").click()
        page.wait_for_timeout(900)
        page.locator("#qInput").fill("반품")
        page.locator("#searchForm button").click()
        page.wait_for_timeout(1200)
        check("commerce search 반품", "반품" in txt(page, "#aQ"), txt(page, "#aQ"))

        # ---------- ROI ----------
        page.locator("#roi").scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        h0 = txt(page, "#rHours")
        a0 = txt(page, "#rAnnual")
        p0 = txt(page, "#rPayback")
        results["roi_default"] = {"hours": h0, "annual": a0, "payback": p0, "note": txt(page, "#roiNote")}
        check("ROI default hours", h0.startswith("175"), h0)
        check("ROI default annual", a0.startswith("5,249"), a0)
        check("ROI default payback", p0.startswith("1.1"), p0)

        # move people slider via keyboard (real user interaction)
        page.locator("#rPeople").focus()
        for _ in range(12):
            page.keyboard.press("ArrowRight")
        page.wait_for_timeout(300)
        h1, a1, p1 = txt(page, "#rHours"), txt(page, "#rAnnual"), txt(page, "#rPayback")
        check("slider changes numbers", (h1, a1, p1) != (h0, a0, p0), f"{h1} / {a1} / {p1}")
        check("people output updated", txt(page, "#oPeople").startswith("20"), txt(page, "#oPeople"))

        # minutes + wage sliders
        page.locator("#rMin").fill("120")
        page.locator("#rWage").fill("40000")
        page.wait_for_timeout(300)
        h2, a2, p2 = txt(page, "#rHours"), txt(page, "#rAnnual"), txt(page, "#rPayback")
        check("minute/wage sliders update", (a2 != a1) and txt(page, "#oWage").startswith("40,000"),
              f"{h2} / {a2} / {p2} / {txt(page, '#oWage')}")

        # package switch
        page.locator('#pkgPick button[data-cost="12000000"]').click()
        page.wait_for_timeout(300)
        p3 = txt(page, "#rPayback")
        check("package switch changes payback", p3 != p2, f"{p2} -> {p3}")
        check("package aria-pressed", page.locator('#pkgPick button[data-cost="12000000"]').get_attribute("aria-pressed") == "true", "")
        mail = page.locator("#mailBtn").get_attribute("href")
        check("mailto carries computed numbers", mail.startswith("mailto:mashiaro@naver.com") and "body=" in mail, mail[:120])
        results["roi_changed"] = {"hours": h2, "annual": a2, "payback": p3, "mail": mail[:160]}
        page.locator(".roi-grid").screenshot(path=str(SHOTS / "04-desktop-roi.png"))

        # packages + process + full page
        page.locator("#packages").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        page.locator("#packages .wrap").screenshot(path=str(SHOTS / "05-desktop-packages.png"))
        page.locator("#process").scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        page.locator("#process .wrap").screenshot(path=str(SHOTS / "06-desktop-process.png"))

        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(400)
        auto_scroll(page)
        hidden_reveals = page.locator(".reveal:not(.in)").count()
        check("all sections revealed after scroll", hidden_reveals == 0, f"{hidden_reveals} hidden")
        page.screenshot(path=str(SHOTS / "07-desktop-full.png"), full_page=True)

        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check("no horizontal overflow (desktop)", overflow <= 1, overflow)
        ctx.close()

        # ---------------- mobile ----------------
        m = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                is_mobile=True, has_touch=True, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        mp = m.new_page()
        mp.on("console", lambda msg: results["console_errors"].append("mobile: " + msg.text) if msg.type == "error" else None)
        mp.on("pageerror", lambda e: results["page_errors"].append("mobile: " + str(e)))
        mp.goto(URL, wait_until="load")
        mp.wait_for_timeout(2200)
        mp.screenshot(path=str(SHOTS / "08-mobile-hero.png"))
        m_hero_cls = mp.locator("#hero3d").get_attribute("class") or ""
        check("mobile hero visual active", "ready" in m_hero_cls or "fallback" in m_hero_cls, m_hero_cls)
        m_overflow = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check("no horizontal overflow (mobile)", m_overflow <= 1, m_overflow)

        mp.locator("#demo").scroll_into_view_if_needed()
        mp.wait_for_timeout(600)
        mp.locator(".demo-shell").screenshot(path=str(SHOTS / "09-mobile-demo.png"))
        mp.locator("#roi").scroll_into_view_if_needed()
        mp.wait_for_timeout(600)
        mp.locator(".roi-grid").screenshot(path=str(SHOTS / "10-mobile-roi.png"))
        mp.evaluate("window.scrollTo(0,0)")
        mp.wait_for_timeout(300)
        auto_scroll(mp, 500)
        m_hidden = mp.locator(".reveal:not(.in)").count()
        check("mobile sections revealed after scroll", m_hidden == 0, f"{m_hidden} hidden")
        mp.screenshot(path=str(SHOTS / "11-mobile-full.png"), full_page=True)
        m.close()

        browser.close()

    results["summary"] = {
        "passed": sum(1 for c in results["checks"] if c["ok"]),
        "failed": sum(1 for c in results["checks"] if not c["ok"]),
        "console_errors": len(results["console_errors"]),
        "page_errors": len(results["page_errors"]),
    }
    (ROOT / "screenshots" / "verify-report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results["summary"], ensure_ascii=False))
    if results["console_errors"]:
        print("CONSOLE ERRORS:", results["console_errors"][:5])
    if results["page_errors"]:
        print("PAGE ERRORS:", results["page_errors"][:5])
    return 0 if results["summary"]["failed"] == 0 and not results["console_errors"] and not results["page_errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
