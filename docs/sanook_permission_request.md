# Permission request: Sanook (บริษัท เทนเซ็นต์ (ประเทศไทย) จำกัด)

**Status:** DRAFT, not sent. Decision recorded 2026-10-12: **option A, ask first**
(`ETHICS.md` stays **no-go** until a written yes).
**Drafted:** 2026-10-12

Sent in Thai; the English version below is for the repository record and the paper's
appendix, not for sending. When a reply arrives, record it as a dated row in the
`ETHICS.md` register (`sanook_food`) and note it in `docs/source_audit.md`.

## Why this letter is different from the DCP one

The DCP request asks before collecting. Sanook's 80 recipes were **already collected**, on
2026-10-07, in a separate session, before Sanook's terms were read. The terms
(`https://www.sanook.com/termservice/`) forbid scraping and data mining without the
company's prior written permission. This letter says so plainly, asks permission after the
fact, and offers to delete everything. Nothing from Sanook has been loaded, analysed or
published, and nothing will be unless the answer is yes.

## Before sending: things to fill or check

1. **Your school year.** This draft says ม.๔ (Grade 10), as in the mentor letters; the
   DCP draft says ม.๕ (Grade 11). Use whichever is true, the same in both letters.
2. **The recipient.** Sanook's contact or copyright address on `sanook.com` (the contact
   page or the footer of the terms page). Prefer a named editorial or legal contact over a
   general inbox. Not filled in here, so that it is checked rather than guessed.
3. **A co-signatory.** A parent or teacher, named in the signature block, with a CC.
4. **The numbers.** 80 recipes from 69 articles, dated 2009-10-22 to 2026-07-10
   (`data/coverage/sources_20261012.md`, `scripts/inventory_sources.py`).

## Expected outcomes

| Reply | Action |
|---|---|
| Yes, including publishing derived ingredient lists | `ETHICS.md` → go. Load under HD-40 |
| Yes, for analysis only, no redistribution | `ETHICS.md` → go, with Sanook rows excluded from every public release |
| No | Delete the local files (`data/raw/sanook_food/`); record the deletion date in `ETHICS.md` |
| No reply | Stays no-go. Note in `ETHICS.md` the date permission was sought |

---

## ฉบับภาษาไทย (ส่งฉบับนี้)

**เรื่อง** ขออนุญาตใช้ข้อมูลสูตรอาหารจากเว็บไซต์ Sanook เพื่อการศึกษาวิจัยเชิงวิชาการ (ไม่แสวงหากำไร)

**เรียน** ฝ่ายบรรณาธิการ / ฝ่ายกฎหมาย บริษัท เทนเซ็นต์ (ประเทศไทย) จำกัด (Sanook)

ดิฉัน Jenissa Vichiansin นักเรียนชั้นมัธยมศึกษาปีที่ ๔ โรงเรียนนานาชาติ ISB กรุงเทพมหานคร
กำลังจัดทำโครงงานวิจัยอิสระด้านวิทยาการข้อมูล เรื่อง **อาหารไทยในแต่ละจังหวัดถูกบันทึกไว้อย่างไร**
โดยเปรียบเทียบเมนูที่ภาครัฐคัดเลือก สูตรที่เผยแพร่บนเว็บไซต์ และสิ่งที่ผู้ปรุงอาหารในบ้านทำจริง

**๑. สิ่งที่เกิดขึ้นแล้ว ซึ่งดิฉันขอชี้แจงตามตรง**

เมื่อวันที่ ๗ ตุลาคม ๒๕๖๙ โครงงานของดิฉันได้รวบรวมข้อมูลสูตรอาหาร ๘๐ สูตร จากบทความ ๖๙ บทความ
บนเว็บไซต์ Sanook ด้วยโปรแกรมอัตโนมัติ **ก่อนที่ดิฉันจะได้อ่านข้อกำหนดในการให้บริการของบริษัท**
เมื่ออ่านแล้ว ดิฉันพบว่าข้อกำหนดไม่อนุญาตให้ดึงข้อมูลโดยไม่ได้รับอนุญาตเป็นลายลักษณ์อักษรล่วงหน้า
ดิฉันจึงหยุดใช้ข้อมูลดังกล่าวทันที ข้อมูลนี้ **ยังไม่ได้ถูกนำไปวิเคราะห์ ไม่ได้ถูกนำเข้าฐานข้อมูล
และไม่ได้เผยแพร่ในรูปแบบใด** และถูกเก็บไว้ในเครื่องของดิฉันเท่านั้น ดิฉันขออภัยที่ไม่ได้ตรวจสอบก่อน

**๒. สิ่งที่ขออนุญาต**

ขออนุญาตใช้ข้อมูล ๘๐ สูตรที่รวบรวมไว้แล้ว เฉพาะส่วนต่อไปนี้
- ชื่อสูตร วันที่เผยแพร่ แท็ก และข้อความที่ระบุภาคหรือจังหวัดของอาหาร
- **รายการวัตถุดิบ** (ชื่อวัตถุดิบและปริมาณ) และลิงก์กลับไปยังบทความต้นฉบับ

โดยจะ **ไม่ใช้** วิธีทำ เนื้อความบทความ รูปภาพ หรือชื่อผู้เขียน และจะไม่เก็บข้อมูลเพิ่มจากเว็บไซต์

**๓. ขอบเขตการใช้งาน (ขอให้บริษัทเลือกได้)**

- **แบบที่ ๑:** ใช้วิเคราะห์ และเผยแพร่เฉพาะรายชื่อวัตถุดิบที่ผ่านการจัดมาตรฐานแล้ว
  เป็นชุดข้อมูลเปิดเพื่อการศึกษา พร้อมอ้างอิง Sanook และลิงก์กลับทุกสูตร
- **แบบที่ ๒:** ใช้วิเคราะห์เท่านั้น โดยไม่เผยแพร่ข้อมูลที่มาจาก Sanook ต่อในรูปแบบใด

หากบริษัทไม่อนุญาต ดิฉันจะ **ลบข้อมูลทั้งหมด** และแจ้งยืนยันการลบกลับมา

**๔. สิ่งที่ยินดีตอบแทน**

- อ้างอิง Sanook ในบทความวิชาการและในชุดข้อมูลทุกฉบับที่ได้รับอนุญาต
- จัดส่งผลการวิเคราะห์ให้บริษัทโดยไม่มีค่าใช้จ่าย

หากต้องการข้อมูลเพิ่มเติม ดิฉันยินดีชี้แจงทันที

ขอแสดงความนับถือ

Jenissa Vichiansin
นักเรียนชั้นมัธยมศึกษาปีที่ ๔ · โรงเรียนนานาชาติ ISB กรุงเทพมหานคร
อีเมล: tundee.org@gmail.com
โครงงาน: `github.com/tundeeorg-cmd/flavormap`

*ผู้ปกครอง / อาจารย์ที่ปรึกษา:* [ชื่อ] — [อีเมล]

---

## English version (for the record, not for sending)

**Subject:** Permission to use Sanook recipe data for non-commercial academic research

Dear Editorial / Legal Team, Tencent (Thailand) Co., Ltd. (Sanook),

I am Jenissa Vichiansin, a Grade 10 student at International School Bangkok, working on
an independent data-science project on how Thai provincial food is recorded: comparing the
dishes the state selected, recipes published online, and what home cooks actually make.

**1. What has already happened, stated plainly.** On 7 October 2026 my project collected
80 recipes from 69 Sanook articles with an automated program, **before I had read your
Terms of Service**. Having read them, I understand they do not permit data extraction
without your prior written permission, so I stopped using the data immediately. It has
**not been analysed, loaded into any database, or published in any form**, and is held
only on my own computer. I apologise for not checking first.

**2. What I am asking.** Permission to use those 80 already-collected recipes, limited to
their titles, publication dates, tags, any text naming the dish's region or province,
**the ingredient lists** (names and quantities), and a link back to each article. I will
**not** use method text, article prose, images or author names, and I will collect
nothing further from the site.

**3. Scope: your choice.**
- **Option 1:** use them for analysis, and publish only normalised ingredient lists as an
  open educational dataset, crediting Sanook with a link to every recipe.
- **Option 2:** use them for analysis only, publishing nothing derived from Sanook.

If you would prefer I not use them, I will **delete all of the data** and confirm the
deletion to you.

**4. In return.** Sanook will be credited in the academic paper and in every permitted
dataset release, and I will send you the results free of charge.

I am happy to answer any questions.

Respectfully,

Jenissa Vichiansin · Grade 10, International School Bangkok
tundee.org@gmail.com · `github.com/tundeeorg-cmd/flavormap`

*Parent / supervising teacher:* [name] — [email]
