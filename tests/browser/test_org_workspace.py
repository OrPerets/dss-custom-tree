"""Browser regression coverage for the organization workspace using real demo routes.

Run with: python3 -m pytest tests/browser -q
Requires Flask, pandas, pytest, playwright and its Chromium browser.
"""
import csv
import io
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def preview_url():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "demo" / "serve.py"), "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urlopen(url + "/health", timeout=1):
                    break
            except OSError:
                if process.poll() is not None:
                    pytest.fail("Local preview server exited before becoming ready")
                time.sleep(.1)
        else:
            pytest.fail("Local preview server did not become ready")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser, preview_url):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_default_timeout(6000)
    page.goto(preview_url)
    expect(page.locator(".org-node")).to_have_count(8)
    yield page
    page.close()
    assert errors == []


def search(page, text):
    page.get_by_role("searchbox", name="Search people").fill(text)


def state(page, expression):
    return page.evaluate("() => { const s = angular.element(document.body).scope(); return " + expression + "; }")


def test_overview_and_expand_collapse(page):
    expect(page.get_by_role("complementary", name="Employee details")).to_have_count(0)
    expect(page.locator(".canvas-footer")).to_contain_text("8 of 15 people shown")
    page.get_by_role("button", name="Show direct reports of Daniel Katz").click()
    expect(page.locator(".org-node")).to_have_count(10)
    page.get_by_role("button", name="Hide direct reports of Daniel Katz").click()
    expect(page.locator(".org-node")).to_have_count(8)
    levels = page.get_by_role("combobox", name="Visible organization levels")
    levels.select_option("all")
    expect(page.locator(".org-node")).to_have_count(15)
    levels.select_option("2")
    expect(page.locator(".org-node")).to_have_count(4)
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_search_reveals_hidden_people_and_preserves_collapsed_view(page):
    search(page, "Tomer")
    expect(page.locator(".org-node")).to_have_count(4)
    expect(page.locator(".filter-context")).to_contain_text("1 match")
    assert state(page, "s.state.diagram.byId.E009 !== undefined")
    search(page, "zz-no-person")
    expect(page.get_by_role("heading", name="No matching people")).to_be_visible()
    page.get_by_role("button", name="Clear search and filters").click()
    expect(page.locator(".org-node")).to_have_count(8)


def test_details_disclosure_and_escape_focus(page):
    card = page.get_by_role("button", name="Daniel Katz, Engineering Manager. View employee details")
    card.focus()
    page.keyboard.press("Enter")
    details = page.get_by_role("complementary", name="Employee details")
    expect(details).to_be_visible()
    expect(details.get_by_text("CEO should only", exact=False)).to_have_count(0)
    expect(details.get_by_text("E005", exact=True)).not_to_be_visible()
    details.locator("summary", has_text="Employee information").click()
    expect(details.get_by_text("E005", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    expect(details).to_have_count(0)
    expect(card).to_be_focused()


def test_filters_and_review_scope(page):
    page.get_by_role("button", name="Filters", exact=True).click()
    filters = page.get_by_role("region", name="Organization filters")
    filters.get_by_role("combobox", name="Department", exact=True).select_option("Engineering")
    expect(page.locator(".filter-context")).to_contain_text("5 matches")
    expect(page.locator(".org-node")).to_have_count(6)
    page.keyboard.press("Escape")
    expect(filters).not_to_be_visible()
    page.get_by_role("button", name="Clear all", exact=True).click()
    page.get_by_role("button", name="1 item to review").click()
    expect(page.locator(".org-node")).to_have_count(3)
    expect(page.locator(".filter-context")).to_contain_text("1 match")
    page.get_by_role("button", name="Ella Peleg, People Ops Manager. View employee details").click()
    expect(page.locator(".review-note")).to_contain_text("capacity")


def test_manager_change_validation_versions_and_exports(page):
    search(page, "Tomer")
    page.get_by_role("button", name="Tomer Niv, Data Engineer. View employee details").click()
    details = page.get_by_role("complementary", name="Employee details")
    details.locator("summary", has_text="Change manager").click()
    details.get_by_role("combobox", name="New manager").select_option(label="Daniel Katz · Engineering Manager")
    details.get_by_role("button", name="Apply change").click()
    expect(page.locator(".feedback-toast")).to_contain_text("Tomer Niv now reports to Daniel Katz")
    assert state(page, "s.state.nodeMap.E009.manager_id") == "E005"
    expect(page.locator(".workspace-status")).to_have_text("1 unsaved change")
    page.get_by_role("button", name="Dismiss notification").click()
    page.get_by_role("button", name="Save version", exact=True).click()
    expect(page.locator(".feedback-toast")).to_contain_text("Version saved")
    expect(page.locator(".workspace-status")).to_have_text("No unsaved changes")
    assert state(page, "s.state.nodeMap.E009.manager_id") == "E005"
    page.get_by_role("button", name="Dismiss notification").click()
    with page.expect_download() as download:
        page.get_by_role("button", name="Export", exact=True).click()
    rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text())))
    assert next(row for row in rows if row["employee_id"] == "E009")["manager_id"] == "E005"
    page.get_by_role("button", name="Dismiss notification").click()
    page.get_by_role("button", name="Changes & versions", exact=True).click()
    history = page.get_by_role("region", name="Changes and versions")
    with page.expect_download() as download:
        history.get_by_role("button", name="Export change history").click()
    move_rows = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text())))
    assert len(move_rows) == 1
    page.get_by_role("button", name="Dismiss notification").click()
    page.get_by_role("button", name="Changes & versions", exact=True).click()
    history.get_by_role("button", name="Load version").click()
    expect(page.locator(".feedback-toast")).to_contain_text("Version loaded")
    assert state(page, "s.state.nodeMap.E009.manager_id") == "E005"
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Dismiss notification").click()
    search(page, "Omer")
    page.get_by_role("button", name="Omer Tzur, Recruiter. View employee details").click()
    details = page.get_by_role("complementary", name="Employee details")
    change = details.locator("details").filter(has=page.locator("summary", has_text="Change manager"))
    if not change.get_attribute("open") == "":
        change.locator("summary").click()
    details.get_by_role("combobox", name="New manager").select_option(label="Shira Azul · Sales Manager")
    details.get_by_role("button", name="Apply change").click()
    expect(page.locator(".feedback-toast")).to_contain_text("Move rejected")
    assert state(page, "s.state.nodeMap.E014.manager_id") == "E013"
    expect(page.locator(".workspace-status")).to_have_text("No unsaved changes")


def test_html_drag_drop_still_applies_move(page):
    page.get_by_role("combobox", name="Visible organization levels").select_option("all")
    source = page.locator(".org-node").filter(has=page.get_by_role("button", name="Tomer Niv, Data Engineer. View employee details"))
    target = page.locator(".org-node").filter(has=page.get_by_role("button", name="Daniel Katz, Engineering Manager. View employee details"))
    transfer = page.evaluate_handle("new DataTransfer()")
    source.locator(".org-node__drag-handle").dispatch_event("dragstart", {"dataTransfer": transfer})
    expect(page.locator(".feedback-toast")).to_contain_text("Move preview")
    target.dispatch_event("dragover", {"dataTransfer": transfer})
    expect(target).to_have_class(re.compile("org-node--drop-valid"))
    target.dispatch_event("drop", {"dataTransfer": transfer})
    expect(page.locator(".feedback-toast")).to_contain_text("Tomer Niv now reports to Daniel Katz")
    assert state(page, "s.state.nodeMap.E009.manager_id") == "E005"


@pytest.mark.parametrize("width,height", [(390, 844), (768, 1024), (1024, 768), (1920, 1080)])
def test_responsive_controls_and_dropdowns(page, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.get_by_role("button", name="Filters", exact=True).click()
    panel = page.get_by_role("region", name="Organization filters")
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= height
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Changes & versions", exact=True).click()
    panel = page.get_by_role("region", name="Changes and versions")
    expect(panel).to_be_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= height
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_mobile_readability_and_touch_pan(browser, preview_url):
    page = browser.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    page.goto(preview_url)
    expect(page.locator(".org-node")).to_have_count(8)
    page.wait_for_function("angular.element(document.body).scope().state.canvas.scale >= .85")
    before = state(page, "s.state.canvas.x")
    chart = page.locator(".tree-viewport")
    chart.evaluate("""element => {
        const touch = new Touch({identifier: 1, target: element, clientX: 100, clientY: 450});
        element.dispatchEvent(new TouchEvent('touchstart', {bubbles: true, touches: [touch]}));
        const moved = new Touch({identifier: 1, target: element, clientX: 170, clientY: 450});
        element.dispatchEvent(new TouchEvent('touchmove', {bubbles: true, cancelable: true, touches: [moved]}));
        element.dispatchEvent(new TouchEvent('touchend', {bubbles: true, touches: []}));
    }""")
    assert state(page, "s.state.canvas.x") == pytest.approx(before + 70)
    assert not state(page, "s.state.canvas.dragging")
    search(page, "Tomer")
    expect(page.locator(".org-node")).to_have_count(4)
    page.get_by_role("button", name="Tomer Niv, Data Engineer. View employee details").click()
    expect(page.get_by_role("complementary", name="Employee details")).to_be_visible()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    page.close()


def test_no_storage_and_loading_error(browser, preview_url):
    page = browser.new_page()
    def without_storage(route):
        response = route.fetch()
        route.fulfill(response=response, body=response.text().replace('snapshot_folder: "Local preview snapshots"', 'snapshot_folder: null'))
    page.route(preview_url + "/", without_storage)
    page.goto(preview_url)
    expect(page.locator(".org-node")).to_have_count(8)
    expect(page.get_by_role("button", name="Save version", exact=True)).to_be_disabled()
    page.get_by_role("button", name="Changes & versions", exact=True).click()
    expect(page.get_by_role("region", name="Changes and versions")).to_contain_text("configure a baseline folder")
    page.route("**/validate-input", lambda route: route.fulfill(status=500, json={"message": "Test source is unavailable"}))
    page.reload()
    expect(page.get_by_role("heading", name="Organization unavailable")).to_be_visible()
    expect(page.get_by_role("alert")).to_contain_text("Test source is unavailable")
    page.unroute("**/validate-input")
    page.get_by_role("button", name="Try again").click()
    expect(page.locator(".org-node")).to_have_count(8)
    page.close()
