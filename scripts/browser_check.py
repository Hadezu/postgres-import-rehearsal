"""Verify and record the generated read-only evidence, desktop and mobile."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results/browser"
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 900},
        record_video_dir=str(OUT),
        record_video_size={"width": 1280, "height": 900},
    )
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((ROOT / "evidence/review.html").as_uri())
    assert (
        page.locator("h1").inner_text().replace("\n", " ")
        == "Review first. Apply exactly. Undo carefully."
    )
    buttons = page.get_by_role("button")
    assert buttons.count() == 6
    for i in range(6):
        buttons.nth(i).click()
        section = page.locator(f"#step-{i}")
        assert section.is_visible()
        assert page.locator("section:visible").count() == 1
        assert section.locator("tbody tr").count() == 3
        page.evaluate("window.scrollTo({top: 360, behavior: 'smooth'})")
        page.wait_for_timeout(1400)
    page.get_by_role("button", name="5 · Stale plan").click()
    page.screenshot(path=str(ROOT / "evidence/desktop.png"), full_page=True)
    page.get_by_role("button", name="6 · Protected undo").click()
    assert "REFUSED" in page.locator("#step-5").inner_text()
    page.locator("#step-5 .table-wrap").scroll_into_view_if_needed()
    page.wait_for_timeout(1500)
    video = page.video
    ctx.close()
    video.save_as(str(ROOT / "evidence/demo.webm"))
    mobile = browser.new_page(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    mobile.goto((ROOT / "evidence/review.html").as_uri())
    mobile.get_by_role("button", name="6 · Protected undo").click()
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert mobile.locator("#step-5").is_visible()
    mobile.screenshot(path=str(ROOT / "evidence/mobile.png"), full_page=True)
    # Keyboard focus and activation are native buttons; check an actual keyboard transition.
    mobile.get_by_role("button", name="1 · Preview").focus()
    mobile.keyboard.press("Enter")
    assert mobile.locator("#step-0").is_visible()
    assert not errors, errors
    browser.close()
(OUT / "result.json").write_text(
    json.dumps(
        {"desktop": "PASS", "mobile": "PASS", "keyboard": "PASS", "page_errors": errors}, indent=2
    )
)
print("Desktop, mobile, keyboard, and six evidence steps PASS")
