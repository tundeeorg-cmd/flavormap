"""Offline tests for scripts/audit_source.py's parsing logic.

No live network calls — everything here runs against recorded/synthetic HTML so
the test suite stays fast and deterministic. fetch_robots/check_sitemap (which
do make network calls) are exercised manually via `python -m scripts.audit_source`,
not in CI.
"""

from scripts.audit_source import (
    RateLimiter,
    analyze_hydration_static,
    build_user_agent,
    extract_fields,
)

SERVER_RENDERED_HTML = """
<html><head><title>ต้มยำกุ้ง - สูตรอาหารไทย</title>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Recipe", "name": "ต้มยำกุ้ง"}
</script>
</head>
<body>
<h1>ต้มยำกุ้ง</h1>
<div class="ingredient-list">
  <div class="ingredient-item">กุ้ง 300 กรัม</div>
  <div class="ingredient-item">ตะไคร้ 2 ต้น</div>
</div>
<p>ส่วนผสม: กุ้ง ตะไคร้ ใบมะกรูด พริก มะนาว น้ำปลา</p>
<p>วิธีทำ: ต้มน้ำให้เดือด ใส่ตะไคร้และใบมะกรูด ใส่กุ้ง ปรุงรส</p>
</body></html>
"""

JS_HYDRATED_SHELL_HTML = """
<html><head><title>Recipe App</title></head>
<body>
<div id="__next"></div>
<script src="/static/bundle.js"></script>
</body></html>
"""


def test_extract_fields_finds_jsonld_recipe_and_thai_keywords() -> None:
    report = extract_fields("https://example.com/recipe/1", SERVER_RENDERED_HTML)
    assert report.has_jsonld_recipe is True
    assert "ส่วนผสม" in report.thai_keyword_hits
    assert "วิธีทำ" in report.thai_keyword_hits
    assert report.candidate_ingredient_blocks >= 1
    assert report.thai_char_ratio > 0.5
    assert report.title is not None and "ต้มยำกุ้ง" in report.title


def test_extract_fields_no_recipe_signal_on_empty_shell() -> None:
    report = extract_fields("https://example.com/", JS_HYDRATED_SHELL_HTML)
    assert report.has_jsonld_recipe is False
    assert report.thai_keyword_hits == []
    assert report.candidate_ingredient_blocks == 0


def test_hydration_heuristic_flags_spa_shell_as_js_hydrated() -> None:
    report = analyze_hydration_static(JS_HYDRATED_SHELL_HTML)
    assert report.verdict == "js-hydrated"
    assert 'id="__next"' in report.spa_markers_found


def test_hydration_heuristic_flags_rich_text_page_as_server_rendered() -> None:
    report = analyze_hydration_static(SERVER_RENDERED_HTML)
    assert report.verdict == "server-rendered"
    assert report.spa_markers_found == []


def test_build_user_agent_includes_contact_email() -> None:
    ua = build_user_agent("researcher@example.com")
    assert "researcher@example.com" in ua
    assert "FlavorMapResearchBot" in ua


def test_rate_limiter_spaces_calls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    clock = {"t": 0.0}
    sleeps: list[float] = []

    monkeypatch.setattr("scripts.audit_source.time.monotonic", lambda: clock["t"])
    monkeypatch.setattr("scripts.audit_source.time.sleep", lambda s: sleeps.append(s))

    limiter = RateLimiter(min_interval_sec=1.0)
    limiter.wait()  # first call: no prior call, no sleep
    clock["t"] = 0.3
    limiter.wait()  # only 0.3s elapsed, should sleep ~0.7s

    assert sleeps == [0.7]
