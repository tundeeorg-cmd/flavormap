# FlavorMap — Research Questions (v2)

**Version:** 5 November 2026 · **Supersedes:** Bible v4 §6 wording · ✏️ = changed in this version

**Changes in v2:** RQ1 adds a permutation baseline and bootstrap confidence intervals. RQ4 is reframed as a test of the field's ingredient-list standard. RQ5 is replaced with a nationwide question about web presence of endangered dishes, so it no longer depends on fieldwork.

## ภาษาไทย

| RQ | แบบสั้น | แบบเต็ม สำหรับเปเปอร์ |
|---|---|---|
| **RQ1** ✏️ | อาหารประจำจังหวัดที่รัฐเลือก สูตรบนเว็บ และอาหารที่คนในจังหวัดทำกินจริง **ต่างกันจริง หรือแค่บังเอิญ?** | ชุดวัตถุดิบของอาหารประจำจังหวัดจากสามแหล่ง ได้แก่ เอกสารของกรมส่งเสริมวัฒนธรรม สูตรจากเว็บไซต์อาหาร และอาหารที่แม่ครัวในจังหวัดทำกินจริง แตกต่างกันมากน้อยเพียงใด เมื่อวัดด้วยระยะห่างของชุดวัตถุดิบ (cosine distance) ในจังหวัดเดียวกัน **และความแตกต่างนั้นมากกว่าที่คาดได้จากความบังเอิญหรือไม่ โดยเทียบกับค่าพื้นฐานจากการสุ่มสลับจังหวัด (permutation test) และรายงานช่วงความเชื่อมั่นแบบ bootstrap?** |
| **RQ2** | อาหารแต่ละภาคมีเอกลักษณ์เพราะวัตถุดิบที่ใส่ หรือเพราะวัตถุดิบที่คนในภาคไม่ใส่? | ความโดดเด่นของอาหารแต่ละจังหวัดเกิดจากวัตถุดิบที่ใช้มากกว่าค่าเฉลี่ยของประเทศ หรือจากวัตถุดิบที่ใช้น้อยกว่าหรือไม่ใช้เลย และผลการแยกสองส่วนนี้สอดคล้องกับสิ่งที่แม่ครัวบอกว่า "บ้านเราไม่มีวันใส่" หรือไม่? |
| **RQ3** | มีอาหารหรือวัตถุดิบอะไรบ้างที่คนในจังหวัดทำกินจริง แต่ไม่อยู่ในรายชื่ออาหารของรัฐ? | เมนูและวัตถุดิบที่แม่ครัวในนครราชสีมาและบุรีรัมย์ระบุว่าทำกินจริง ปรากฏในรายชื่ออาหาร 3 เมนูต่อจังหวัดของรัฐ และในสูตรจากเว็บไซต์มากน้อยเพียงใด และมีอะไรบ้างที่ไม่ปรากฏในแหล่งใดเลย? |
| **RQ4** | นักวิจัยศึกษาอาหารจากรายชื่อวัตถุดิบอย่างเดียว ถ้าไม่มีขั้นตอนการทำ เราจะยังทำอาหารจานนั้นออกมาได้จริงไหม? | ข้อมูลสูตรอาหารแบบรายชื่อวัตถุดิบ ซึ่งงานวิจัยด้านอาหารใช้เป็นมาตรฐาน ยังเก็บความรู้เพียงพอที่จะทำอาหารจานนั้นได้จริงหรือไม่ และข้อมูลใดสูญหายไป (ปริมาณ ลำดับ เทคนิค ชนิดวัตถุดิบที่เจาะจง)? ทดสอบโดยการทำอาหาร 8 จานจากสูตรของรัฐ เว็บไซต์ และแม่ครัว |
| **RQ5** | อินเทอร์เน็ตกำลังช่วยรักษา หรือปล่อยให้เมนูพื้นบ้านที่ใกล้สูญหายหายไป? | เมนูที่รัฐระบุว่าใกล้สูญหาย มีสูตรเผยแพร่บนเว็บไซต์อาหารมากน้อยเพียงใด เมื่อเทียบกับเมนูที่รัฐระบุว่ายังมีการสืบทอดอยู่? |

## English

| RQ | Short version | Full version (for the paper) |
|---|---|---|
| **RQ1** ✏️ | How different are the dishes the state chose to represent each province, the recipes on the web, and what people in that province actually cook, **and are the differences real or just chance?** | How far apart are the ingredient profiles of the same province across three sources: the Department of Cultural Promotion's records, recipes on food websites, and the dishes home cooks in that province actually make? Distance is measured as cosine distance between ingredient profiles within each province. **Are these differences larger than expected by chance? We compare against a baseline built by randomly shuffling province labels (a permutation test) and report bootstrap confidence intervals.** |
| **RQ2** | Does a region's food identity come from the ingredients it uses, or from the ingredients it refuses to use? | Is each province's culinary distinctiveness driven by ingredients it uses more than the national average, or by ingredients it uses less or never uses? Does this decomposition agree with what home cooks say "we would never put in"? |
| **RQ3** | Which dishes and ingredients do people actually cook that are missing from the state's list? | To what extent do the dishes and ingredients that home cooks in Nakhon Ratchasima and Buri Ram report cooking appear in the state's three-dishes-per-province list and in web recipes, and which appear in neither? |
| **RQ4** | Researchers study food from ingredient lists alone. Without the cooking steps, can we still actually make the dish? | Does the ingredient-list representation of recipes, standard in computational food research, retain enough knowledge to cook the dish, and what information is lost (quantities, order, technique, ingredient specificity)? We test this by cooking eight dishes from state, web and home-cook sources. |
| **RQ5** | Is the internet helping to preserve endangered local dishes, or letting them disappear? | How widely are recipes for dishes the state classifies as endangered published on food websites, compared with dishes the state classifies as still being passed on? |

## Implementation note for RQ1 (timeline task T1.19)

- **Permutation test (HD-44, revised 2026-11-06):** the unit is the region (HD-37). **Primary:** within each region, shuffle the official/commercial labels across its recipes 9,999 times (register-label shuffle), recompute the official↔commercial distance each time, and report where the observed distance falls (empirical p-value, Holm-adjusted across the four regions). **Secondary:** shuffle region labels within each register. The primary test was chosen after trial results were seen (recorded in HD-44).
- **Bootstrap:** 95% bias-corrected percentile intervals from 9,999 resamples of recipes within each region.
- Report n beside every distance.
- Changing the RQ wording after pre-registration requires a dated amendment in `docs/hypotheses.md`, not a silent edit.
