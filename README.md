# Position: A Score Should Travel With Its Repair History (supplementary data)

We release here the data and code behind the count of reporting events in Section 3 of the paper, a position paper at the NeurIPS 2026 workshop on AI for Meta-Science. Two scripts read only the files in `data/` and regenerate every count-derived number that the main text and Appendix C print, together with Figure 1. Numbers that the paper takes from the documents themselves, such as page anchors and quoted figures, come from the cited sources and lie outside the scripts.

## Running the scripts

Both scripts run from the root of this folder under Python 3 with pandas, numpy, scipy and matplotlib.

```
python code/compute_summary.py
python code/make_fig1.py
```

We tested them with Python 3.11, pandas 3.0, numpy 2.4, scipy 1.17 and matplotlib 3.10, and together they run in a few seconds. The summary script prints each number at the precision the paper uses, rounding half up, and writes every value at full precision beside its printed form to `output/summary_values.csv`. The figure script draws both panels of Figure 1 from `data/tally.csv` and `data/model_report_dates.csv`. It writes `figure1.pdf`, `figure1.svg` and `figure1.png` to `output/` and the plotted values to `figure1_values_a.csv` and `figure1_values_b.csv`. The script keeps the design of the published figure, including the right-axis maximum of 75%. The published figure is set in Helvetica. Where neither Helvetica nor Arial is installed, the script falls back to the metric-compatible Liberation Sans. The files in `output/` were drawn on such a machine and are set in Liberation Sans, with the plotted values of the published figure.

The bootstrap intervals use seed 20261002 and 10,000 replicates. We resample documents with replacement within each class, and model reports also within the groups before and after June 2024. Each stratum, namely the five classes, the two timing groups and the HLE documents, draws from its own random stream, spawned from the seed in a fixed order. A rerun therefore reproduces every interval exactly, and a change in one class leaves the intervals of the others unchanged. Counts of zero carry exact (Clopper–Pearson) 95% intervals. The `output/` folder holds the files that the two scripts wrote for this release, and with the versions above a rerun matches them byte for byte apart from the creation dates inside `figure1.pdf` and `figure1.svg`. Under pandas 2.2, numpy 1.26, scipy 1.13 and matplotlib 3.9 the printed numbers, the plotted values and the pixels of the figure stay the same. Only the last digit of three exact upper limits in `summary_values.csv` changes.

We checked the release against the working files behind the paper. Run from a fresh copy of this folder, the summary script reproduces the count-derived numbers of the main text and every value in the tables of Appendix C. The figure script reproduces the plotted values of Figure 1 byte for byte.

## Files

Row counts exclude the header line.

| File | Rows | Contents |
|---|---|---|
| `data/tally.csv` | 195 | Every coded row of the MMLU count with its final codes. The 194 coded rows cover 26 documents, and one further row records a release document that prints no MMLU-family score (the Claude 4 system card). |
| `data/tally_first_pass.csv` | 195 | The same rows with their codes before the second coding and adjudication. |
| `data/adjudication_log.csv` | 162 | Every change between the two tallies and every ruling, with the rule applied and the reason. |
| `data/second_coding_cells.csv` | 1,552 | The second coding of all 194 coded rows, one line per row and category, beside the first-pass code. |
| `data/coding_rules.md` | | The coding rules, ending with the nine adjudication rules (R1 to R9) and the tie-break that the logs cite. |
| `data/model_report_dates.csv` | 85 | Release month, timing group and variant flags for each coded row of the model reports. |
| `data/census.csv` | 114 | Records of the census of whole reports, one per passage of a model report that states a qualification. |
| `data/document_level_records.csv` | 21 | Qualifications that the first pass recorded in the model reports outside the coded events. |
| `data/hle_tally.csv` | 14 | The Humanity's Last Exam (HLE) events, 14 in 9 documents, with their final codes. |
| `data/hle_second_coding_cells.csv` | 140 | The second coding of the HLE events, one line per event and category. |
| `data/hle_adjudication_log.csv` | 4 | The three HLE rulings and the wording code that follows one of them. |
| `data/hle_linked_documents.csv` | 9 | The codes that methodology documents linked from five HLE events would add. |
| `data/population.csv` | 45 | The MMLU successor population of Appendix F, the original MMLU and 44 artefacts. |
| `data/release_survey.csv` | 17 | The release-report survey of Appendix G. |
| `code/compute_summary.py` | | Recomputes every count-derived number in the main text and Appendix C. |
| `code/make_fig1.py` | | Draws Figure 1. |
| `output/summary_values.csv` | 695 | Every value the summary script computes, at full precision and as printed. |
| `output/figure1.pdf`, `output/figure1.svg`, `output/figure1.png` | | Figure 1. |
| `output/figure1_values_a.csv`, `output/figure1_values_b.csv` | 18 and 9 | The values plotted in panels (a) and (b), with the printed-only and every-row readings beside the headline. |

## The unit and the readings

The unit of the count is the reporting event, a sentence, table or figure that states or plots a model's MMLU-family score. A row of `tally.csv` is an event when its `unit_status` is score or plotted, and 170 of the 194 coded rows qualify. The other 24 rows report no model score and enter only the every-row reading. The six substantive qualifications are K2 to K7, and an event's count of qualifications is their sum. K1 records whether the event identifies the benchmark variant. It holds at all 194 coded rows of the final tally, and the means therefore count K2 to K7 only.

The summary script reports the seven readings of Appendix C. Five of them change the unit, the conventions or the weighting, and the last uses the codes before adjudication.

- **Headline.** Events whose `unit_status` is score or plotted.
- **Stated only.** K5 and K6 count only where `K5_wording` or `K6_wording` is 1.
- **Documents weighted.** Each document weighs the same. The mean is the mean of the per-document means, and the share with none is the mean of the per-document shares.
- **K5 and K6 dropped.** We set K5 and K6 to 0 everywhere.
- **Printed only.** Events whose `unit_status` is score.
- **Every row.** Every coded row counts, including the 24 rows that report no model score.
- **Before adjudication.** The headline reading of `tally_first_pass.csv`.

Model reports split at June 2024, when MMLU-Pro and MMLU-Redux appeared, by the `group` column of `model_report_dates.csv`.

## The tally

Each K code is 1 when the qualification attaches to the event. A qualification attaches when it sits in the same paragraph, table or figure or in a place the event explicitly points to. The coding rules in `data/coding_rules.md` give the full definitions. `tally_first_pass.csv` has the same columns.

| Column | Meaning |
|---|---|
| `row` | Row number, counted from 0, that the logs and the second-coding cells cite. |
| `doc_id` | Citation key of the document. |
| `document` | Name of the document as the paper gives it. |
| `class` | C1 construction paper, C2 repair papers, C3 model reports, C4 leaderboard post, C5 governance syntheses. |
| `location` | Page of the PDF file and the element coded, such as a table, figure or paragraph. |
| `unit_status` | score (states a model's score as a number, including an approximate value or a bound), plotted (shows model scores only as marks), not_score (prints numbers, none of them a model's score), no_numeral (names the benchmark and prints no number). Empty for the Claude 4 system card. |
| `n_scores` | Number of scores the row states or plots. Empty where the row reports no model score or the coder recorded no count. |
| `models_named` | Models or classes of model named at the event. |
| `K1` | Variant identified. 1 if the event, read with its document, identifies the benchmark. |
| `K2` | Implementation. 1 if the event states how the scores were obtained, such as the evaluation code, prompt, shot count, scoring rule or grader. |
| `K3` | Contamination. 1 if words say that the authors checked or addressed contamination. |
| `K4` | Item error. 1 if words concern item errors, ground-truth problems or corrected labels. |
| `K5` | Aggregate. 1 if the event qualifies the aggregate in words, by a statistic on the reported scores, or by a displayed breakdown or labelled human baseline. |
| `K6` | Scope. 1 if the event limits language or cultural scope in words, by results for two or more languages, or by naming a translated or multilingual variant. |
| `K7` | Saturation. 1 if words concern the benchmark's ceiling or its power to separate models. |
| `K5_wording`, `K6_wording` | Filled only where K5 or K6 is 1. The value 1 means that words or statistics carry the qualification, and 0 means that a display, a label or a variant name alone carries it. |
| `quote` | Short verbatim quotation from the event. |
| `unit_evidence` | What the page prints that decided `unit_status`. |
| `unit_alt` | A second unit status that the classification considered, where it recorded one. |
| `found_by` | Origin of the row. The value `first pass` covers the primary corpus, `first pass, vendor documents added later` covers the three vendor documents added to it, `completeness search` covers the 72 rows that the two completeness searches added, and `page check` covers the five rows that a later check of the quoted pages added, three table images in the Llama 4 announcement and two passages in the GPT-4o system card. |

## Conventions

Every table in `data/` except `population.csv` identifies a document by its citation key in `doc_id` and by the name the paper uses in `document`. The `row` column numbers the rows of both tallies from 0. The logs, the second-coding cells and `model_report_dates.csv` refer to rows by these numbers, and a reason that reads "as row 35" points to row 35 of `tally.csv`. The HLE files number their events from 0 in the same way, in the column `event_id`. Page numbers in locations are those of the PDF file, as in the paper. The row for the Claude 4 system card has no `unit_status` and enters no statistic, since it records only that the document prints no MMLU-family score.

The `n_scores` column follows Appendix D. Score rows always carry a positive count, plotted rows carry a count where the coder recorded one, and rows that report no model score carry none. Three plotted rows from the two AI Index reports hold only approximate counts in the coding record. We leave them empty, as Appendix D does. In the first pass one score row of the Claude 3 model card recorded a count of 0 for a bound ("above 80%"). The amendment in the log sets that count to 1, and both tallies carry 1.

The tallies fill `K5_wording` and `K6_wording` only where K5 or K6 is 1. `tally.csv` writes these codes as 1.0 and 0.0, and `tally_first_pass.csv` writes them as 1 and 0, as the coded files hold them. Every code keeps the value of the coded files character for character, and blank codes stay blank.

The adjudication log records every change between `tally_first_pass.csv` and `tally.csv`. Its `stage` column reads adjudication for the 149 entries of the adjudication itself. They comprise the rulings on the 97 disputed cells, the nine agreed cells that the audit recoded, 32 wording codes, two corrections of a location and a count, and nine entries that change no code. Each of those nine records a second reading of a cell in the five page-check rows that the first pass flagged and the final code declines. An audit of the five page-check rows changed no code and corrected the reasons of three entries. The `stage` column reads amendment for the 13 entries that came after, namely a reversed ruling at Table 5 of the Qwen2 report with its wording code, four corrected counts of scores, the corrected location and count of Table 7 of the GPT-4o system card, and the five rows that the page check added, whose `field` reads row. Each entry gives the value it replaced in `before` and the value it set in `after`. The `second_coding` column holds the second coder's value where a second coder coded the cell. Applying the `after` values in order to `tally_first_pass.csv` reproduces every code, location and count of `tally.csv`, with the wording codes equal in value.

The `rule` column cites R1 to R9 of `coding_rules.md`, alone, in pairs or with the tie-break. The label `wording` marks a corrected wording code, `follows K5` and `follows K6` mark wording codes set to match an adjudicated category, and `unit` marks a change to a location or a count of scores. The `before` value of a count is the count as first recorded, and it can therefore differ from the count that `tally_first_pass.csv` gives under the convention above. The log omits four entries that recorded only additions to a free-text notes field, since the release does not carry that field.

The HLE log gives the first-pass, second-coding and adjudicated value of each ruled cell. Its `earlier_coding` column gives the code that an earlier coding of the same events assigned before we wrote down the conventions, and that code decides no ruling. Its `follows` column says whether each ruling follows the first pass or the second coding.

Five agents coded the first 189 rows a second time without access to the first-pass codes, a sixth coded the three Llama 4 rows in the same way, and a seventh coded the two GPT-4o rows. `second_coding_cells.csv` records their codes beside the first pass. The `coder_group` column names the agent, and `second_coding_evidence` and `second_coding_uncertain` give its evidence and its notes on uncertain calls. The `flagged` column marks the three Llama 4 rows, whose agent declared that general coding conventions and an earlier ruling naming the announcement surfaced from memory, and `memory_at_start` records what it saw. The agent for the two GPT-4o rows declared that nothing about them surfaced from memory. Two agents coded the 14 HLE events a second time in the same way. In `hle_second_coding_cells.csv` the `flagged` column marks the eight Google and Meta events, whose agent saw corpus-level counts from an earlier coding when it started. The `memory_at_start` column records what each agent saw, as Appendix E describes.

To find whether a model report states a qualification anywhere, the summary script combines three sources, namely the codes at its events, the census records and the document-level records. A census record names an MMLU-family benchmark when `concerns_mmlu_family` is yes and makes a generic statement about all benchmarks when it is unclear. Appendix C counts the generic statements in brackets. The census covers the first 15 reports. A later run on the Llama 4 announcement found three hits, all on scope terms in its page text, and none of them states a qualification. The file therefore holds no record from it. The census did not search for implementation statements, and the implementation column therefore rests on the event codes, the document-level records and a targeted search of the Qwen2 report.

In `model_report_dates.csv` the column `release_month` gives the month of the first arXiv version, or the vendor's month of release for a document without one. The column `group` reads pre before June 2024 and post after it, and the Claude 3.5 Sonnet addendum of June 2024 reads contemporaneous and falls in neither group. The flags `orig_mmlu`, `repaired_variant` and `translation` mark events that report the original English MMLU, a repaired variant (MMLU-Pro, MMLU-Redux or Global MMLU) and a translated MMLU. The flag `inferred` marks two Qwen3 rows whose flags we set from the template of Tables 3 and 4 of the same report, because their locations do not name the benchmarks.

`hle_linked_documents.csv` lists the codes that the methodology documents linked from five HLE events would add, with the statement behind each code. Its `reading` column separates the additions of the linked-document reading from the four possible aggregate additions of Appendix E. A statement marked as a paraphrase reports the document's content without quoting it.

`population.csv` reproduces the table of Appendix F with the original MMLU in its first row. The phrase "not confirmed" marks a detail that the compilation could not check against a primary record. `release_survey.csv` holds the table of Appendix G, with document names that follow the tally.

## AI assistance

Claude models (Anthropic), working as agents under written rules, carried out the document searches, the coding, the completeness searches, the census, the adjudication and the audits described in Appendices B and E. They also compiled the population and survey tables of Appendices F and G, and language model tools assisted with reference checking, the appendices, formatting and code. We reviewed all of it and take full responsibility for the content.

## Licence and citation

The code in `code/` is released under the MIT licence (`LICENSE`). The data and outputs we created are released under CC BY 4.0 (`LICENSE-DATA.md`), and short quotations from the coded documents remain under the rights of their publishers. `CITATION.cff` gives the citation for this archive, and each release is archived on Zenodo with a DOI.
