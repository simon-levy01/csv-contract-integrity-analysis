# CSV benchmark: portable offline analysis supplement

This self-contained package reproduces analysis of two **already-completed public synthetic benchmark runs from 2026-10-02**. It does not modify the benchmark, its prompts, scorer, frozen cases, or reported primary metric. No new model run is performed.

## Run once

An existing **Python 3.8 or later** interpreter is required (minimum supported API level; tested on Linux with Python 3.12.14). Windows/macOS portability is based on cross-platform standard-library APIs and path/newline tests, not execution on those operating systems. Only the Python standard library is used: no installation, package download, API key, account, or network access is needed.

Unzip the archive, open a terminal in its `csv-benchmark-analysis-public` folder, and run:

```sh
python3 -B analyze.py
```

On Windows, the equivalent is `py -3 -B analyze.py` (or `python -B analyze.py` if that is your Python command). A successful run exits 0, verifies all evidence, and writes eight deterministic artifacts to `results/` beside the script. If that folder already contains these analysis artifacts, rerunning replaces them with the same bytes. A folder containing unrelated files is rejected.

You can also run the script from another working directory. Quote paths containing spaces; supply a dedicated output directory if desired:

```sh
python3 -B "csv-benchmark-analysis-public/analyze.py" --output-dir "my reproduced results"
```

The script finds bundled inputs relative to itself, not your current directory. A relative `--output-dir` is resolved from your current directory. Inputs, source code and expected outputs are never overwritten. UTF-8 and LF output are explicit; output does not contain current timestamps or machine-specific paths.

## Expected result

| Model | Strict pass | Posthoc adapted pass | Adapter-ineligible | Eligible JSON-unparseable | Parsed but wrong |
|---|---:|---:|---:|---:|---:|
| Gemini 3.7 Flash | 0/60 | 59/60 | 1 | 0 | 0 |
| Claude Haiku 4.5 | 0/60 | 14/60 | 8 | 0 | 38 |

The frozen primary score remains **0/60 for both models**. All 120 primary mutation outcomes are **unknown**, not zero. The separate posthoc diagnostic accepts exactly one complete outer `json` fence with no surrounding prose or nested fence. It is not the primary metric and is not a broader JSON extractor.

Haiku's diagnostic has 32 mutation-positive cases among 52 assessable cases and 55 destructive emitted rows. Secondary failure tags overlap: 33 incorrect issue reports, 31 blocked-row emissions, 12 cases omitting eligible rows, and 8 protected-cell/header-change cases (7 changing existing string values). Do not sum overlapping tags. See [REPORT.md](REPORT.md) for detailed interpretation and examples.

## Files

- `data/gemini/` and `data/haiku/`: byte-identical original `primary-report.json` and `posthoc-diagnostics.json`, including saved responses and original run metadata.
- `data/frozen-cases.json`: exact original decoded payload of 72 public synthetic cases, including expected responses. The 12 development cases are retained to preserve the exact payload/hash but excluded from both 60-case evaluations.
- `data/contract.txt`: exact UTF-8 contract, without normalization or an added newline.
- `data/frozen-plan.json`: extracted frozen hash declarations, 60 evaluated case IDs, source declarations and numeric limits.
- `scorer.py`: ten pure scorer functions copied verbatim; only standard-library imports and the original numeric size limits precede them. No notebook driver is included.
- `analysis_helpers.py`: descriptive row-lineage and overlapping-tag analysis, kept separate from the frozen scorer.
- `analyze.py`: offline integrity checks, replay, aggregation and output writing.
- `manifest.json`: SHA-256 and byte count for every distributed file except itself; safe public provenance links and hash limitations.
- `expected/`: checked-in deterministic reference outputs for comparison. These include the full 120-case analysis, summaries by model/group/category/recipe, complete case ledger, all overlapping tag counts, and reproduction receipt.
- `tests/test_offline.py`: standard-library test suite.
- `PROVENANCE.md` and `AUDIT.md`: source chain and verification/security/portability scope.

The output files are `analysis.json`, `model-summary.csv`, `group-summary.csv`, `category-summary.csv`, `recipe-summary.csv`, `overlapping-failure-tags.csv`, `case-ledger.csv`, and `reproduction-receipt.json`.

The full JSON retains every primary/posthoc verdict, request/response hash, failure flag and row-level explanation. Category summaries include all six original families and six composition recipes; the recipe table separately exposes the six four-transformation recipes for each model.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

Windows: `py -3 -B -m unittest discover -s tests -v`.

Tests copy the package into a fresh directory containing spaces and invoke it from a different working directory. They verify complete reference-output byte equality, deterministic outputs across Python hash seeds, safe reruns, corruption and missing-file rejection, safe output locations, and integrity checks under `python -O`. Tests make no external calls. Temporary copies are automatically removed.

Any corrupted/missing listed input, code, or reference artifact makes the runner fail explicitly with a nonzero exit status before writing new results. Integrity checks use explicit exceptions, not assertions, and remain enabled with `python -O`. Existing output files from an earlier successful run are not proof that a later run succeeded; check the current exit status.

## Hashes: what is and is not proved

- Independently recomputed: exact contract bytes, exact frozen case payload, all 120 serialized contract/input request hashes, and all four original report file hashes.
- Reproduced: all 120 saved primary verdicts and all 120 posthoc outcomes, including null/ineligible diagnostics; all 72 expected answers pass scorer self-consistency checks.
- Separately fingerprinted: the exact ten extracted scorer-function source segments. The recipe is recorded in the manifest.
- **Original frozen grader hash: declaration-aligned only.** Its declaration agrees between the frozen source constant and both reports. The original serialization/hash recipe was unavailable, so it was not independently reconstructed. The extracted-source fingerprint is not a substitute for that original hash.
- Historical `original_sha256` and `composition_oracle_sha256` entries remain source declarations; the underlying historical assets are not bundled or independently rehashed here.

The manifest detects accidental edits/corruption, not authorship or a malicious party who changes both the manifest and its files. The source notebook's recorded hash is provenance only because the executable notebook is intentionally excluded.

## Safety and limitations

All included inputs and raw outputs come from the already-public synthetic fixture runs. Byte-identical raw reports retain their public case/chat identifiers, timestamps, usage and pricing metadata. No account credentials, signed download links, private notes, full provider traces, executable notebook, model SDK, or benchmark driver is included. Synthetic Unicode edge cases (including normalization differences and a bidi-control substitution in a saved response) remain unchanged because they are evidence.

This is local-only analysis; it does not publish, upload or contact a service. Public links are documentation only. One run per model and correlated fixture transformations do not establish a population-wide model ranking, repeatability estimate or causal explanation. Oracle checks are self-consistency checks, not independent proof of every label. This supplement follows the public Kaggle source’s Apache License 2.0; see `LICENSE` and `NOTICE` for the license, attribution and modification notice.
