# Coding rules (1 October 2026)

These are the rules under which the MMLU tally was adjudicated. They combine the original coding protocol,
three written conventions and the nine adjudication rules (R1 to R9, listed at the end of this file). Code
every event under them. Where a rule leaves two readings open, code the one that credits the document with the
qualification, and say so in the evidence.

## Unit

An event is a sentence, a table or a figure that reports a model's score on the benchmark. A table or figure
counts as one event, including its caption and notes. Give every event a `unit_status`:

| unit_status | The event |
|---|---|
| `score` | states at least one model's score as a number: exact, approximate ("around 70%") or a bound ("above 90%"), in text, in a table cell or printed on a figure |
| `plotted` | shows model scores only as plotted marks (bars, points, lines), with no printed score |
| `not_score` | prints benchmark numbers, none of which is a model's score: a human or expert baseline, a dataset property, a rank or rank change, a difference where neither score is stated, a correlation, or a derived quantity |
| `no_numeral` | names the benchmark and prints no number for it |

Any printed score makes the event `score`. A difference from a fixed reference (random chance, a human
baseline) counts as a score only if the reference value is printed at the event.

## Attachment

A qualification attaches to an event if it appears in the same paragraph, in the same table or figure
including its caption and notes, or in a place the event explicitly points to ("see Appendix 10.2", "As
shown in Table 1"). Attachment runs from the event: a paragraph that points to a table does not carry its
own qualifications into the table, and a methods section that no caption points to attaches to nothing.

## Categories

- **K1, variant identified.** The event, read with its document, identifies which benchmark it reports. A
  name is enough; a release or version label is not required.
- **K2, implementation.** The event states how the reported scores were obtained: the harness (including
  the authors' own pipeline named as such, or a named harness the benchmark is released in), prompt format
  or prompting condition, shot count, scoring rule (for example "EM", "Pass@1"), grader, or a pointer to
  code. Training procedures, contamination-analysis parameters, model or inference-mode names, and
  rescaling for display do not count.
- **K3, contamination.** Words at the event, or at a place it points to, say contamination was checked or
  addressed. A variant's name or an unlabelled difference between splits does not count.
- **K4, item error.** Words at the event, or at a place it points to, about item errors, ground-truth
  problems, corrected labels or disputed answers. The name of a corrected variant alone does not count.
- **K5, aggregate.** The event qualifies the aggregate:
  - in words: uneven performance across subjects, calibration, a comparison with human experts, the score's
    sensitivity to the prompt, decoding method, shot count or implementation, or a tolerance for treating
    close scores as equal;
  - by a statistic that applies to the reported scores: confidence intervals, standard deviations or error
    bars, significance tests;
  - by a displayed per-subject or per-category breakdown, or a labelled human or expert baseline.
  Scores printed under several settings without such words count under K2 only. A spread between models
  and a method's tuning procedure do not count.
- **K6, scope.** The event limits the score's language or cultural scope: in words (translation by machine
  or by people, translation quality, cultural or regional knowledge, localisation), by displaying results
  for two or more languages, or by naming a translated or multilingual variant. A single language heading
  is a label, and the name of a monolingual non-English benchmark does not count alone.
- **K7, saturation.** Words at the event about the benchmark's ceiling or its power to separate models, in
  either direction: saturated, near ceiling, scores tightly clustered, hard to tell models apart, or room
  for improvement. A plotted shape, a threshold, a bound on a score or a contrast between gains does not
  count. A comparison with human experts is K5, and also K7 only with such words.

For K5 and K6, also record `K5_wording` and `K6_wording` where the code is 1: 1 if words or statistics carry
it, 0 if the only basis is a display, a label or a variant name.

## Humanity's Last Exam (in addition to the above)

- **K4** includes any qualification about HLE's items: the FutureHouse audit, HLE-Gold-Bio/Chem, the reason
  for HLE-Verified, a correction from HLE's review period or bug bounty, or a statement that some answers are
  disputed.
- **K2** includes the grader of HLE answers (for example "judged by GPT-4o") and the tool setting
  ("with tools", "with search").
- Record `hle_variant` for any corrected or restricted set named at the event (HLE-Verified, HLE-Gold, the
  text-only subset, a third-party run such as "(AA)", or a version label).
- A separate document linked from the event (for example a methodology PDF) is not attached; record what it
  would add in the notes as the alternative reading.

## Adjudication rules

The adjudication logs cite these rules by number. The sections above restate them.

- **R1.** Variant (K1): the event, read with its document, identifies the benchmark.
- **R2.** Attachment runs from the event. A qualification outside the event's own paragraph, table or figure
  (including caption and notes) attaches only if the event explicitly points to it, and then the pointed-to
  location's qualifications attach. A paragraph that points to a table does not carry its own qualifications
  into the table.
- **R3.** Implementation (K2) states how the reported scores were obtained: the harness (including the authors'
  own pipeline named as such, or a named harness the benchmark is released in), prompt format or prompting
  condition, shot count, scoring rule, or a pointer to code. Training procedures, contamination-analysis
  parameters, model or inference-mode names, and rescaling for display do not count.
- **R4.** A comparison with human experts, in words or as a labelled baseline, is an aggregate qualification
  (K5), as the protocol lists "expert gap" under K5. It is also K7 only if the event says the benchmark is
  saturated, no longer separates models, or has room above current scores.
- **R5.** Saturation (K7) needs words at the event about the benchmark's ceiling or its power to separate
  models, in either direction (saturated, near ceiling, scores tightly clustered, hard to discern differences;
  or room for improvement). A plotted shape, a choice of threshold, a bound on a score or a contrast between
  gains is the coder's inference and does not count.
- **R6.** Contamination (K3) needs words at the event, or an explicit pointer from it, saying contamination was
  checked or addressed. A variant's name or an unlabelled validation-test difference does not count.
- **R7.** Aggregate (K5) follows the written convention: words (unevenness across subjects, calibration, expert
  gap, sensitivity of scores to the prompt, decoding method, shot count or implementation, or a tolerance for
  treating close scores as equal), statistics that apply to the reported scores (confidence intervals,
  standard deviations or error bars, significance tests), or a displayed per-subject or per-category
  breakdown. Scores printed under several settings without such words count under K2 only. A spread between
  models and a method's tuning procedure do not count.
- **R8.** Scope (K6) follows the written convention: words limiting language or cultural scope, displayed
  results for two or more languages (including rows grouped under two or more language headings), or the name
  of a translated or multilingual variant. A single language heading is a label, and the name of a monolingual
  non-English benchmark (KMMLU, CMMLU) does not count alone.
- **R9.** Item error (K4) needs words at the event, or an explicit pointer from it, about item errors,
  ground-truth problems or corrected labels. The name of a corrected variant alone does not count, as in
  panel (b) of Figure 1.
- **Tie-break**, in every class alike: where a cell fits two readings of a rule, the ruling credits the
  document with the qualification.
