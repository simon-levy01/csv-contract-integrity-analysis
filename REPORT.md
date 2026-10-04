# CSV benchmark: failure mechanisms in the saved responses

Offline analysis prepared 2026-10-04. Uses the already-completed 2026-10-02 runs only.

## Main finding

The official strict score is still **0/60 for each model**. Every saved response fails the JSON-only entry condition, so the primary scorer cannot assess mutation in any of the 120 responses. This is **unknown**, not zero mutation.

The separate, unchanged diagnostic removes exactly one complete outer `json` fence, only when there is no surrounding prose or nested fence. It reveals very different downstream behavior: **Gemini passes 59/60; Haiku passes 14/60.** All 38 Haiku responses that enter this adapter and then fail contain parseable JSON. Most failures concern which rows may be emitted and which issues must be reported, not incorrect arithmetic on an otherwise eligible row.

No inference was rerun. No provider access, new model requests, notebook benchmark execution, original-artifact edits or public posting were involved.

## 1. Mutually exclusive diagnostic outcomes

| Model | Cases | Strict pass | Adapted pass | Adapter-ineligible | Eligible but JSON-unparseable | Parsed JSON, wrong contract |
| --- | --- | --- | --- | --- | --- | --- |
| gemini | 60 | 0 | 59 | 1 | 0 | 0 |
| haiku | 60 | 0 | 14 | 8 | 0 | 38 |

The last four columns sum to 60 for each model. “Parsed JSON, wrong contract” does not mean every CSV target was valid: two Haiku cases contain blank emitted targets, which violate the integer requirement. They are still JSON-parseable.

Adapter-ineligible is a wrapper classification, not a judgment that a complete valid JSON body exists:
- Gemini's `preservation-05` has an incomplete JSON string and unclosed fence. Its saved response contains 448 visible characters; usage reports 7,996 output tokens against a requested 8,000-token cap. Those are observations. The artifacts do not establish the cause or how reported tokens were allocated.
- Seven Haiku responses contain text outside a complete JSON fence. One (`csv_format-06`) contains multiple complete JSON fences and surrounding text. These are not stripped or rescored using a broader extractor.

Haiku ineligible IDs: `exact_join-04`, `exact_join-06`, `exact_join-07`, `current_safety-07`, `ambiguity-04`, `ambiguity-05`, `csv_format-06`, `composition-v3-03-02`.

## 2. Original fixture families

These are the benchmark's original six high-level fixture families, not six statistically independent or exhaustive contract-clause tests. Only cases 03–08 are evaluated; cases 01–02 in each family remain excluded development cases. Strict passes are zero throughout. No eligible JSON-unparseable cases occur in any family.

| Original family | n | Gemini pass | Gemini ineligible | Haiku pass | Haiku ineligible | Haiku parsed wrong |
| --- | --- | --- | --- | --- | --- | --- |
| Exact key joins | 6 | 6 | 0 | 1 | 3 | 2 |
| Protected-cell preservation | 6 | 5 | 1 | 4 | 0 | 2 |
| Current values / pre-existing new values | 6 | 6 | 0 | 1 | 1 | 4 |
| Ambiguous or unmatched keys | 6 | 6 | 0 | 0 | 2 | 4 |
| Quantity semantics | 6 | 6 | 0 | 4 | 0 | 2 |
| CSV format and schema | 6 | 6 | 0 | 4 | 1 | 1 |

Totals: Gemini 35/36 passes, 1 ineligible. Haiku 14/36 passes, 7 ineligible, 15 parsed wrong.

## 3. Composition recipes

Each recipe has four correlated transformations. The 24 cases are not 24 independent samples. Recipe descriptions below summarize the frozen input/oracle content. No eligible JSON-unparseable cases occur here.

| Recipe | Contract interaction | n | Gemini pass | Haiku pass | Haiku ineligible | Haiku parsed wrong |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Exact keys, protected strings, invalid and unmatched counts | 4 | 4 | 0 | 0 | 4 |
| 2 | Duplicate export keys and duplicate count keys | 4 | 4 | 0 | 0 | 4 |
| 3 | Pre-existing new values, invalid current/count, signed zero | 4 | 4 | 0 | 1 | 3 |
| 4 | Packed dimensions across counted and uncounted locations | 4 | 4 | 0 | 0 | 4 |
| 5 | Product-wide option completeness | 4 | 4 | 0 | 0 | 4 |
| 6 | Duplicate variant/location and not-stocked current value | 4 | 4 | 0 | 0 | 4 |

Totals: Gemini 24/24 passes. Haiku 0/24 passes, 1 ineligible, 23 parsed wrong. This establishes a failure on every tested Haiku composition, not a general failure rate for unseen compositions.

## 4. What went wrong after JSON parsing

The following are **overlapping case counts among Haiku's 38 parsed-wrong cases**. One case can have several tags; do not add them together.

| Observed mechanism | Cases | Meaning |
| --- | --- | --- |
| Incorrect issue report | 33 | Missing or spurious source/record/code triples |
| Forbidden source-row emission | 31 | 30 cases emit row-blocked data; 1 emits despite a fatal SCHEMA error |
| Omitted eligible source rows | 12 | 13 eligible rows absent; changed-but-emitted counterparts are not counted as omissions |
| Protected data/header alteration | 8 | 7 cases change existing string values; 1 replaces the unrecognized On hand header |
| Existing string values changed | 7 | Unicode normalization in preservation-04 and all six recipe transformation-03 cases |
| False fatal errors | 3 | Haiku invents CSV_SYNTAX, MAPPING or INVALID_COUNT instead of the required nonfatal result |
| Null instead of a required CSV | 4 | Includes omitted output and null instead of a valid header-only CSV |
| Integer emitted despite invalid source count | 3 | 1e2 becomes 100; two 2.5 cases emit 2, even though the row must be blocked |
| Blank emitted target | 2 | composition-v3-01-03 and composition-v3-01-04 |
| Missed fatal schema error | 1 | csv_format-07 accepts an unrecognized header by replacing it |
| Row order changed, candidate otherwise equivalent | 1 | exact_join-03 reverses two valid rows |
| Wrong target on an otherwise eligible mapped row | 0 | No observed example in the canonical parsed subset |

“Zero wrong targets on eligible rows” is narrow. It does not excuse applying a number to a row the contract forbids, coercing a non-integer count, omitting a valid row or changing protected cells. Likewise, output line endings, quoting, header order and equivalent integer spellings are intentionally ignored by the frozen scorer; they are not counted as errors.

### Mutation and omission must stay separate

In the posthoc diagnostic, Haiku has **32 mutation-positive cases among 52 assessable cases**, with **55 destructive emitted rows** as defined by the frozen scorer. Six other parsed-wrong cases have zero destructive emitted rows: `exact_join-03`, `exact_join-05`, `preservation-05`, `current_safety-04`, `ambiguity-03`, `quantity_semantics-05`. They still fail on row order, omission, wrong error/issue reporting or null output.

Gemini has zero destructive emitted rows among its 59 diagnostic-assessable cases; its one ineligible case remains unknown. Haiku's eight ineligible cases also remain unknown. None of these conditional diagnostic findings replaces the primary mutation status of unknown for all 60 cases per model.

## 5. Traceable case studies

### A. Recognizing a conflict did not prevent applying the update

Haiku `current_safety-05` reports `NEW_VALUE_CONFLICT` for export record 2, which is the correct issue. The contract nevertheless requires that row to be excluded and the candidate to contain only the header. Haiku instead emits the row with `On hand (new)=4` while reporting the conflict. This is a failure to enforce an acknowledged validation result: one destructive emitted row out of one source row. Gemini passes this case after the same single-fence adapter.

Request SHA-256: `78f87aec88dbcf8bb0388bbabff1b8e238bd95bbf50713627aa3bc7c765c7fd3`. Haiku response SHA-256: `58ecb50162679957d882574024f7d6950fc59cb68e27095c49ab0339b14e46ae`.


### B. A visually identical identifier is still a changed identifier

Haiku `preservation-04` changes the protected SKU from decomposed `e` plus U+0301 (`é`) to precomposed U+00E9 (`é`). The desired target count remains correct at 2. The contract requires exact string preservation for SKUs, so this is one destructive emitted row out of one source row. This is not a permitted equivalent-integer rewrite. Gemini preserves the original code points and passes the diagnostic.

Request SHA-256: `17c73267ca1c1c5faac51e3556c8ce2699edcb5bf86a650be12e87778324c747`. Haiku response SHA-256: `3a77792d2816934206e2f724f7f183b0d825c935ec1ca690b73993c3c65bda05`.


### C. Packed dimensions must be checked across locations without counts

In `composition-v3-04-01`, the Green variant has populated dimensions at L and blank dimensions at Other. Only L has a count, but the contract checks every location of that variant. Both Green rows must therefore be blocked for `PACKED_INCONSISTENT`; the Other row also needs `UNMATCHED_EXPORT`. Only the Black/B row may be emitted.

Haiku emits the Green/A row with a new count of 5 as well as Black/B. It assigns incorrect/incomplete issue codes and produces one destructive emitted row out of three source rows. The same recipe fails all four Haiku transformations. Gemini passes all four.

Request SHA-256: `219b1f3a87372c77de5eef9a09700cbafa8cdedf85703ce3004f52aa33eb6b46`. Haiku response SHA-256: `f271190a9fbba9a9df7d358c4df067311c9a19dd59719abec4b03cef7b5fc8f7`.


### D. Omission is a different failure from mutation

In `exact_join-05`, the locations `North` and `north` are distinct exact keys. Haiku emits the `North` row correctly but omits the valid `north` row, and invents duplicate/ambiguous issue codes. Its diagnostic fails while destructive emitted rows remain zero. That does not make the output correct or complete.

Request SHA-256: `d926c187e4d2955aaa7595fb3607cb0fad74cbe66dfce95f78c4c9425ad342c9`. Haiku response SHA-256: `f9246179faf1828be27ef3309384bb88ffaa9f44b2f1efa4a1eba0bae75fed64`.


## 6. Provenance and reproducibility

Sources:
- [Haiku saved Kaggle output, version 354732397](https://www.kaggle.com/code/simonlevy42/csv-inventory-contract-benchmark/output?scriptVersionId=354732397)
- [Gemini saved Kaggle output, version 354731097](https://www.kaggle.com/code/simonlevy42/csv-inventory-contract-benchmark/output?scriptVersionId=354731097)
- [Existing benchmark article](https://dev.to/simon_levy_e0b34a39073843/a-csv-benchmark-with-two-zero-scores-and-a-useful-diagnostic-n9e)

Both original primary reports have 60 nonempty response records, unique evaluated case IDs, and no abort. The evaluation comprises 36 original fixtures plus 24 compositions; 12 development cases are excluded. Original report bytes were verified before and after analysis.

| Artifact | SHA-256 |
| --- | --- |
| Haiku primary report | 0653bda45621a01a742cb1ca21fa0c54569a01e10366176c5ebc3df1ba917d7d |
| Gemini primary report | 1db779322fa5cf93e0dae218842c8ac1188e94252f08d4b4bb40136fcf749263 |
| Source notebook | 90bd6d974edd82fcd68b9d428163c05ad4a1d2cf5d776f82a6acc0e60917e261 |
| Frozen contract, independently recomputed | fd05304bb5187c7f2c5ce7f03d8020a7721ada236971b44b7c2d7e04f9d843e2 |
| Portable case payload, independently recomputed | a08a7b2d3d2f6426098f83137e5de9bf5ac2ba13954af8fb831d6baf695371f9 |

All 120 per-case request hashes match the exact contract/input JSON constructed from the extracted frozen cases. Offline replay reproduces all 120 primary verdicts and all 120 stored posthoc outcomes. All 72 frozen expected responses pass an oracle/scorer self-consistency check. That is not independent validation of every expected label.

The grader SHA-256 declaration agrees across the notebook and both reports. Its original serialization/hash recipe was not available, so the original grader hash was not independently recomputed. The analysis records a separate fingerprint of the isolated scorer-function source and verifies its behavior against every saved verdict. Do not describe this as independent cryptographic verification of the original grader implementation.

The self-contained portable supplement uses `analyze.py` to verify its manifest and replay the extracted pure functions in `scorer.py`; it requires no notebook or network. The original reports remain the authoritative raw evidence. See [README.md](README.md) for the one-command reproduction instructions and [PROVENANCE.md](PROVENANCE.md) for source hashes and limitations.

Companion artifacts under `expected/` (reproduced under `results/`):
- `analysis.json`: provenance, every case classification, exact expected/actual failed responses, issue-code differences and row-level evidence
- `case-ledger.csv`: all 120 cases, IDs, model, status, tags, timestamps, request/response hashes and source URLs
- `model-summary.csv`, `group-summary.csv`, `category-summary.csv`, `recipe-summary.csv`: mutually exclusive outcome counts
- `overlapping-failure-tags.csv`: all secondary tag counts, including explicit zero categories
- `reproduction-receipt.json`: explicit hash/replay verification and original-grader-hash caveat

The exact frozen cases and contract are under `data/`; both canonical runs' byte-identical raw reports are in `data/gemini/` and `data/haiku/`.

## 7. Limits and interpretation

- One saved run per model; no sampling distribution, repeatability estimate or general model ranking is established.
- Public synthetic fixtures and four correlated variants per recipe; no claim of hidden-test generalization or 60 independent tests.
- The diagnostic is posthoc and deliberately narrow. Expanding it to remove prose, select among multiple JSON blocks or repair truncation would answer a different question and was not done.
- Failure-mechanism tags are descriptive and overlapping. They do not alter the official score or the frozen destructive-row definition.
- Source-row lineage is exact on protected cells where possible; changed rows are linked only when exactly one source row differs in one protected field. No ambiguous/fuzzy matches are resolved. A changed-but-emitted row is not counted again as an omitted source row.
- No live Shopify import, production safety test, causal explanation of provider token behavior or new cost measurement is implied.

## Appendix: every parsed-wrong case

All 38 are Haiku cases. Primary strict failure applies to every case for both models, including diagnostic passes.

| Case | Destructive emitted rows | Omitted eligible source records | Overlapping tags |
| --- | --- | --- | --- |
| exact_join-03 | 0 | none | row_order_only_candidate_mismatch |
| exact_join-05 | 0 | 3 | incorrect_issue_report; omitted_eligible_source_row |
| preservation-04 | 1 | none | protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| preservation-05 | 0 | 2 | false_fatal_error; null_candidate_instead_of_csv; omitted_eligible_source_row |
| current_safety-04 | 0 | none | false_fatal_error; incorrect_issue_report; null_candidate_instead_of_csv |
| current_safety-05 | 1 | none | emitted_blocked_source_row |
| current_safety-06 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| current_safety-08 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| ambiguity-03 | 0 | none | incorrect_issue_report; null_candidate_instead_of_csv |
| ambiguity-06 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| ambiguity-07 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| ambiguity-08 | 2 | none | emitted_blocked_source_row; incorrect_issue_report |
| quantity_semantics-05 | 0 | none | false_fatal_error; incorrect_issue_report; null_candidate_instead_of_csv |
| quantity_semantics-06 | 1 | none | emitted_blocked_source_row; incorrect_issue_report; integer_emitted_despite_invalid_count |
| csv_format-07 | 1 | none | changed_candidate_headers; emitted_blocked_source_row; missed_fatal_error; protected_cell_change |
| composition-v3-01-01 | 1 | 3 | emitted_blocked_source_row; incorrect_issue_report; integer_emitted_despite_invalid_count; omitted_eligible_source_row |
| composition-v3-01-02 | 1 | 2,3 | emitted_blocked_source_row; incorrect_issue_report; integer_emitted_despite_invalid_count; omitted_eligible_source_row |
| composition-v3-01-03 | 3 | 3 | emitted_blocked_source_row; incorrect_issue_report; interior_bom_replaced_with_bidi_control; invalid_emitted_target; omitted_eligible_source_row; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-01-04 | 1 | 3 | emitted_blocked_source_row; incorrect_issue_report; invalid_emitted_target; omitted_eligible_source_row |
| composition-v3-02-01 | 3 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-02-02 | 3 | 5 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row |
| composition-v3-02-03 | 2 | 5 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-02-04 | 2 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-03-01 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-03-03 | 2 | none | emitted_blocked_source_row; incorrect_issue_report; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-03-04 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-04-01 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-04-02 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-04-03 | 2 | none | emitted_blocked_source_row; incorrect_issue_report; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-04-04 | 1 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-05-01 | 2 | 4 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row |
| composition-v3-05-02 | 2 | 4 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row |
| composition-v3-05-03 | 2 | 4 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-05-04 | 2 | 4 | emitted_blocked_source_row; incorrect_issue_report; omitted_eligible_source_row |
| composition-v3-06-01 | 3 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-06-02 | 3 | none | emitted_blocked_source_row; incorrect_issue_report |
| composition-v3-06-03 | 4 | none | emitted_blocked_source_row; incorrect_issue_report; protected_cell_change; protected_string_value_change; unicode_nfc_normalization |
| composition-v3-06-04 | 2 | none | emitted_blocked_source_row; incorrect_issue_report |