"""Provincial culture offices (*.m-culture.go.th), under docs/scraping_rules.md.

    uv run python -m scripts.scrape_m_culture --audit

**A retroactive stage A.** 2,584 local-dish rows, 1,570 page texts and 328 PDF texts from
the 76 provincial culture-office sites were collected on 2026-10-07 **outside these
rules**, in a separate session: its User-Agent carried no contact email, it paced
requests at 0.5 s, and it never read robots.txt. They now sit in data/raw/m_culture/
(local, gitignored) and contain personal data, so nothing is loaded unless this audit
gets a `go`, and then only through a parser that redacts at parse time.

robots.txt is checked on the ministry host and on all 76 provincial hosts the data came
from. The ministry's site-policy page was not located by web search on 2026-10-07, so the
terms entry is the ministry home page, whose footer links the policies; the researcher
reads those by hand. Stage A only: discovery and parsing are not built, and no register is
assigned.
"""

from __future__ import annotations

from src.scrape.base import AuditOnlyScraper, main


class Site(AuditOnlyScraper):
    source_id = "m_culture"
    slug = "m_culture"
    base_url = "https://www.m-culture.go.th"
    tos_url = "https://www.m-culture.go.th/"
    extra_robots_hosts = (
        "https://amnatcharoen.m-culture.go.th",
        "https://angthong.m-culture.go.th",
        "https://ayutthaya.m-culture.go.th",
        "https://buengkan.m-culture.go.th",
        "https://buriram.m-culture.go.th",
        "https://chachoengsao.m-culture.go.th",
        "https://chainat.m-culture.go.th",
        "https://chaiyaphum.m-culture.go.th",
        "https://chanthaburi.m-culture.go.th",
        "https://chiangmai.m-culture.go.th",
        "https://chiangrai.m-culture.go.th",
        "https://chonburi.m-culture.go.th",
        "https://chumphon.m-culture.go.th",
        "https://kalasin.m-culture.go.th",
        "https://kamphaengphet.m-culture.go.th",
        "https://kanchanaburi.m-culture.go.th",
        "https://khonkaen.m-culture.go.th",
        "https://krabi.m-culture.go.th",
        "https://lampang.m-culture.go.th",
        "https://lamphun.m-culture.go.th",
        "https://loei.m-culture.go.th",
        "https://lopburi.m-culture.go.th",
        "https://maehongson.m-culture.go.th",
        "https://mahasarakham.m-culture.go.th",
        "https://mukdahan.m-culture.go.th",
        "https://nakhonnayok.m-culture.go.th",
        "https://nakhonpathom.m-culture.go.th",
        "https://nakhonphanom.m-culture.go.th",
        "https://nakhonratchasima.m-culture.go.th",
        "https://nakhonsawan.m-culture.go.th",
        "https://nakhonsrithammarat.m-culture.go.th",
        "https://nan.m-culture.go.th",
        "https://narathiwat.m-culture.go.th",
        "https://nongbualamphu.m-culture.go.th",
        "https://nongkhai.m-culture.go.th",
        "https://nonthaburi.m-culture.go.th",
        "https://pattani.m-culture.go.th",
        "https://phangnga.m-culture.go.th",
        "https://phatthalung.m-culture.go.th",
        "https://phatumthani.m-culture.go.th",
        "https://phayao.m-culture.go.th",
        "https://phetchabun.m-culture.go.th",
        "https://phetchaburi.m-culture.go.th",
        "https://phichit.m-culture.go.th",
        "https://phitsanulok.m-culture.go.th",
        "https://phrae.m-culture.go.th",
        "https://phuket.m-culture.go.th",
        "https://prachinburi.m-culture.go.th",
        "https://prachuapkhirikhan.m-culture.go.th",
        "https://ranong.m-culture.go.th",
        "https://ratchaburi.m-culture.go.th",
        "https://rayong.m-culture.go.th",
        "https://roiet.m-culture.go.th",
        "https://sakaeo.m-culture.go.th",
        "https://sakonnakhon.m-culture.go.th",
        "https://samutprakan.m-culture.go.th",
        "https://samutsakhon.m-culture.go.th",
        "https://samutsongkhram.m-culture.go.th",
        "https://saraburi.m-culture.go.th",
        "https://satun.m-culture.go.th",
        "https://singburi.m-culture.go.th",
        "https://sisaket.m-culture.go.th",
        "https://songkhla.m-culture.go.th",
        "https://sukhothai.m-culture.go.th",
        "https://suphanburi.m-culture.go.th",
        "https://suratthani.m-culture.go.th",
        "https://surin.m-culture.go.th",
        "https://tak.m-culture.go.th",
        "https://trad.m-culture.go.th",
        "https://trang.m-culture.go.th",
        "https://ubonratchathani.m-culture.go.th",
        "https://udonthani.m-culture.go.th",
        "https://uthaithani.m-culture.go.th",
        "https://uttaradit.m-culture.go.th",
        "https://yala.m-culture.go.th",
        "https://yasothon.m-culture.go.th",
    )


if __name__ == "__main__":
    raise SystemExit(main(Site()))
