"""The kapook ingredient block is read positionally, from text lines.

There is nothing structured to read it from. Across the 2,702 cached pages no page
carries a schema.org ``Recipe`` node, only 845 use ``<ul><li>``, and only 1,103 use a
bullet glyph. What holds everywhere is that the block is a run of short lines under a
heading — so the article is flattened to lines and the block is bounded by its heading
above and by a method heading, a further ingredient heading, or prose below.

Flattening has to happen before text extraction, not after: most of the corpus separates
its lines with ``<br>``, which carries no text of its own, so extracting text first
collapses the whole list into a single line.
"""

from __future__ import annotations

import json

import pytest

from src.config import RAW_DIR
from src.ingest.kapook_page import (
    article_lines,
    article_metadata,
    ingredient_sections,
    parse_file,
    parse_html,
    site_category,
)

RAW = RAW_DIR / "kapook_cooking"


def page(body: str, published: str = "2014-09-30T15:58:58+07:00", headline: str = "สูตร") -> str:
    """A minimal page in the shape the site actually serves."""
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": headline,
        "datePublished": published,
        "articleBody": "PROSE THAT MUST NEVER BE STORED",
    }
    return (
        "<html><body>"
        f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
        f'<div id="main_article" class="main_article">{body}</div>'
        "</body></html>"
    )


def test_br_delimited_list_is_read_as_separate_items() -> None:
    """The majority layout. Extracting text before splitting yields one line, not eight."""
    html = page(
        "<h3><b>ส่วนผสม ครัวซองต์</b></h3>"
        "&nbsp; &nbsp; • แป้งขนมปัง 500 กรัม<br />"
        "&nbsp; &nbsp; • นมผง 100 กรัม<br />"
        "&nbsp; &nbsp; • ยีสต์ 10 กรัม<br />"
    )
    sections = ingredient_sections(article_lines(html) or [])
    assert len(sections) == 1
    assert sections[0].items == ["แป้งขนมปัง 500 กรัม", "นมผง 100 กรัม", "ยีสต์ 10 กรัม"]


def test_list_markup_and_numbering_and_zero_width_padding_are_all_read() -> None:
    """Three layouts, one reading. The CMS editor indents with runs of U+200B, which
    survive text extraction and defeat both strip() and a leading-marker match."""
    listed = ingredient_sections(
        article_lines(page("<h3>ส่วนผสม</h3><ul><li>กะปิ 2 ช้อนโต๊ะ</li><li>มะนาว 1 ลูก</li></ul>"))
        or []
    )
    numbered = ingredient_sections(
        article_lines(
            page(
                "<div><b>ส่วนผสม ปูไข่ดอง</b></div>"
                "<div>​​   ​1. ​ปูทะเลไข่ 1 ตัว</div>"
                "<div>​​   ​2.​ ตะไคร้ 1 ช้อนโต๊ะ</div>"
            )
        )
        or []
    )
    assert listed[0].items == ["กะปิ 2 ช้อนโต๊ะ", "มะนาว 1 ลูก"]
    assert numbered[0].items == ["ปูทะเลไข่ 1 ตัว", "ตะไคร้ 1 ช้อนโต๊ะ"]


def test_the_newer_template_heading_is_recognised() -> None:
    """`สิ่งที่ต้องเตรียม` rather than `ส่วนผสม`. Reading only the latter left 244 pages
    parsing to nothing, several of them ordinary recipes."""
    html = page('<div>สิ่งที่ต้องเตรียม "เนื้อสเต๊ก"</div><div>เนื้อโคขุน 200 กรัม</div>')
    assert ingredient_sections(article_lines(html) or [])[0].items == ["เนื้อโคขุน 200 กรัม"]


def test_method_heading_ends_the_section() -> None:
    html = page(
        "<h3>ส่วนผสม</h3>ไข่ไก่ 2 ฟอง<br />"
        "<h3>วิธีทำครัวซองต์</h3>ตอกไข่ใส่ชาม<br />คนให้เข้ากัน<br />"
    )
    sections = ingredient_sections(article_lines(html) or [])
    assert len(sections) == 1
    assert sections[0].items == ["ไข่ไก่ 2 ฟอง"]


def test_prose_under_the_heading_ends_the_section_rather_than_being_collected() -> None:
    """Some pages run straight from the heading into narration with no method heading
    between. 99.5% of genuine ingredient lines are under 96 characters."""
    prose = "จากนั้นให้นวดแป้งไปสักพักจนส่วนผสมทั้งหมดละลายเข้ากันดี " * 4
    html = page(f"<h3>ส่วนผสม</h3>ไข่ไก่ 2 ฟอง<br />{prose}<br />แป้งสาลี 100 กรัม<br />")
    assert ingredient_sections(article_lines(html) or [])[0].items == ["ไข่ไก่ 2 ฟอง"]


def test_sections_are_kept_separate_and_never_merged() -> None:
    """A page is not reliably one dish. Whether these two sections are one recipe with a
    sauce or two recipes in a roundup is a decision about the unit of observation, and
    the parser does not get to make it by concatenating."""
    html = page(
        "<div><b>ส่วนผสม ปูไข่ดอง</b></div><div>ปูทะเลไข่ 1 ตัว</div>"
        "<div><b>ส่วนผสม น้ำจิ้มซีฟู้ด</b></div><div>น้ำมะนาว 6 ช้อนโต๊ะ</div>"
    )
    sections = ingredient_sections(article_lines(html) or [])
    assert [s.heading for s in sections] == ["ส่วนผสม ปูไข่ดอง", "ส่วนผสม น้ำจิ้มซีฟู้ด"]
    assert [len(s.items) for s in sections] == [1, 1]


def test_article_prose_is_never_carried_on_the_record() -> None:
    """ETHICS.md permits ingredient lists, dates and derived labels from this source.
    The JSON-LD hands us the full recipe text in the same node as the date; taking the
    node wholesale would put the prose one asdict() away from a database column."""
    record = parse_html(page("<h3>ส่วนผสม</h3>ไข่ไก่ 2 ฟอง<br />"), url="x/view1.html")
    assert "PROSE" not in json.dumps(record.__dict__, default=str)
    assert set(article_metadata(page(""))) == {"headline", "datePublished"}


def test_publication_date_is_taken_but_never_guessed() -> None:
    assert parse_html(page(""), "x/view1.html").published_at.isoformat() == "2014-09-30"
    unstamped = parse_html(page("", published=""), "x/view1.html")
    assert unstamped.published_at is None
    assert "no usable datePublished" in unstamped.notes


def _breadcrumb(*names: str, page_last: bool = True) -> str:
    items = [{"@type": "ListItem", "position": 1, "name": "cooking",
              "item": "https://cooking.kapook.com"}]
    items += [{"@type": "ListItem", "position": i + 2, "name": n,
               "item": f"https://cooking.kapook.com/c{i}"} for i, n in enumerate(names)]
    if page_last:
        items.append({"@type": "ListItem", "position": len(items) + 1,
                      "name": "ชื่อเมนูของหน้านี้", "item": "https://cooking.kapook.com/view1.html"})
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def test_the_site_category_path_is_taken_verbatim() -> None:
    assert site_category(_breadcrumb("สูตรขนม", "เบเกอรี่")) == "สูตรขนม > เบเกอรี่"
    assert site_category(_breadcrumb("เคล็ดลับทำอาหาร")) == "เคล็ดลับทำอาหาร"


def test_the_page_itself_and_the_site_root_are_never_the_category() -> None:
    # Without the trailing page element, nothing is dropped from the category path.
    assert site_category(_breadcrumb("เมนูอาหาร", "เมนูไข่", page_last=False)) == (
        "เมนูอาหาร > เมนูไข่"
    )
    assert site_category(_breadcrumb()) is None  # only root and page: no category


def test_a_missing_category_is_none_and_noted_never_guessed() -> None:
    record = parse_html(page(""), "x/view1.html")
    assert record.category_source is None
    assert "no breadcrumb category" in record.notes


def test_parse_html_carries_the_category_onto_the_record() -> None:
    html = page("").replace("<html><body>", "<html><body>" + _breadcrumb("สูตรขนม", "ขนมไทย"))
    assert parse_html(html, "x/view1.html").category_source == "สูตรขนม > ขนมไทย"


def test_a_page_without_an_article_container_is_noted_not_raised() -> None:
    record = parse_html("<html><body><p>ไข่ไก่</p></body></html>", url="x/view1.html")
    assert record.sections == [] and not record.is_usable
    assert any("container" in note for note in record.notes)


def test_a_mushroom_is_not_an_informant() -> None:
    """`เห็ดนางฟ้า` is the oyster mushroom and `นางฟ้า` alone names dishes made from it.
    Both read as the honorific `นาง` plus a given name to the PDPA pattern, which
    redacted two section headings in the corpus before FOOD_COMPOUNDS existed."""
    record = parse_html(
        page("<div><b>ส่วนผสม นางฟ้าผัดฉ่า</b></div><div>เห็ดนางฟ้า 200 กรัม</div>"),
        url="x/view1.html",
    )
    assert record.sections[0].heading == "ส่วนผสม นางฟ้าผัดฉ่า"
    assert record.sections[0].items == ["เห็ดนางฟ้า 200 กรัม"]
    assert record.redaction.total == 0


def test_a_contributor_name_in_a_heading_is_still_redacted() -> None:
    record = parse_html(
        page("<div>ส่วนผสม โดย นางฟองจันทร์ ใจดี</div><div>ไข่ไก่ 2 ฟอง</div>"),
        url="x/view1.html",
    )
    assert "ฟองจันทร์" not in record.sections[0].heading
    assert record.redaction.n_names == 1


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_corpus_coverage_holds() -> None:
    """The measured position on 2026-08-23: 2,521 of 2,702 cached pages yield at least
    one ingredient section, and every one carries a title and a publication date. The
    181 that do not are product reviews, knife-technique articles, and recipes whose
    ingredient list is an image or an embedded Facebook post — checked by hand, not
    assumed. The bound is set below the measurement so that a real regression trips it
    while ordinary corpus growth does not."""
    records = [parse_file(p) for p in sorted(RAW.glob("view*.html"))]
    assert len(records) > 2000, "corpus is smaller than expected — was the fetch cut short?"
    usable = [r for r in records if r.is_usable]
    assert len(usable) / len(records) > 0.90
    assert all(r.published_at is not None for r in records)
    assert all(r.title_th for r in records)


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_no_zero_byte_page_is_cached() -> None:
    """40 sitemap URLs answer 200 with an empty body. The fetcher records them as
    `empty`, so they neither reach the corpus nor count toward its coverage."""
    assert [p.name for p in RAW.glob("view*.html") if p.stat().st_size == 0] == []


@pytest.mark.skipif(not RAW.exists(), reason="raw corpus not present")
def test_a_page_has_no_category_only_when_the_site_gives_it_none() -> None:
    """Measured 2026-09-28: 2,677 of 2,702 pages carry a category. The other 25 have a
    breadcrumb of just site root + the page itself; None is the true value for those,
    and must never hide a category the parser failed to read."""
    uncategorised = [p for p in sorted(RAW.glob("view*.html"))
                     if parse_file(p).category_source is None]
    wrongly_empty = [
        p.name for p in uncategorised
        if p.read_text(encoding="utf-8", errors="replace").count('"@type":"ListItem"') != 2
    ]
    assert not wrongly_empty, f"category missed on {wrongly_empty[:5]}"
    assert len(uncategorised) == 25
