# Public evidence and extraction provenance

The two canonical output versions are separate completed runs. The later notebook source snapshot is a source-only save, not a third completed run.

- [Gemini canonical completed output, version 354731097](https://www.kaggle.com/code/simonlevy42/csv-inventory-contract-benchmark/output?scriptVersionId=354731097)
- [Haiku canonical completed output, version 354732397](https://www.kaggle.com/code/simonlevy42/csv-inventory-contract-benchmark/output?scriptVersionId=354732397)
- [Frozen source snapshot, version 354740677](https://www.kaggle.com/code/simonlevy42/csv-inventory-contract-benchmark?scriptVersionId=354740677)
- [Benchmark article](https://dev.to/simon_levy_e0b34a39073843/a-csv-benchmark-with-two-zero-scores-and-a-useful-diagnostic-n9e)

These are public permalink-style URLs without credentials or expiring download signatures. Offline reproduction does not open them. Source-site access policies can change; the bundled evidence is sufficient to reproduce the analysis without fetching anything.

## Raw evidence, unchanged bytes

| Bundled file | Bytes | SHA-256 |
|---|---:|---|
| data/gemini/primary-report.json | 107680 | 1db779322fa5cf93e0dae218842c8ac1188e94252f08d4b4bb40136fcf749263 |
| data/gemini/posthoc-diagnostics.json | 31560 | 4b0489a19be6d33f0fa98bcbab06a4fd96472311d251d23fa3b892a27281cc57 |
| data/haiku/primary-report.json | 110414 | 0653bda45621a01a742cb1ca21fa0c54569a01e10366176c5ebc3df1ba917d7d |
| data/haiku/posthoc-diagnostics.json | 29128 | b75c380f876d4f4ee3b8af842d88badba4642a330910313cb88dc9d7a0a2c201 |

The completed outputs were previously downloaded from each version's Kaggle output interface, extracted without modification, and retained as source evidence. This package copies only the primary report and separate posthoc diagnostics for each run. Full output archives, provider traces and run/task wrappers are unnecessary for offline reproduction and are excluded.

## Frozen input and scorer provenance

The retained source notebook had SHA-256 `90bd6d974edd82fcd68b9d428163c05ad4a1d2cf5d776f82a6acc0e60917e261`. Its driver cells were not executed. Literal constants and exact decoded case bytes were inspected/extracted, along with an explicit allowlist of pure function definitions. The notebook itself is not distributed here.

| Verified extracted material | SHA-256 |
|---|---|
| Exact contract UTF-8 bytes | fd05304bb5187c7f2c5ce7f03d8020a7721ada236971b44b7c2d7e04f9d843e2 |
| Exact decoded 72-case payload | a08a7b2d3d2f6426098f83137e5de9bf5ac2ba13954af8fb831d6baf695371f9 |
| Ten pure function source segments | 31f1d417f9e2be27d87127369b6af05f5bb112aeb7455c524eb0317f9fc8da89 |

The source-segment fingerprint joins the exact function source strings in source order with two LF characters and no final LF, then hashes UTF-8 bytes. The full `scorer.py` file has its own separate ordinary file hash in the manifest.

The frozen original grader hash `099985418bba51d1762e46bb86afed66f177f4d98bf2dadd02630674f8b11c3d` is **declaration-aligned only**. Its original hashing recipe was not available. No claim of independent reconstruction is made.

## Derived analysis

The portable runner independently recomputes every primary and posthoc verdict from the saved raw response text and frozen input/oracle. Each request uses the original serialization: `json.dumps({'contract': contract, 'input': case['input']}, ensure_ascii=False)` encoded as UTF-8. Preserving key order and default JSON separators matters for these hashes.

The descriptive helper preserves the earlier local analysis's row-linking rules: exact protected-cell match first, otherwise a unique match with exactly one changed protected cell; ambiguous links remain unresolved. Eligible omissions exclude changed-but-emitted counterparts. Tags overlap and never modify the frozen benchmark score. Its former assertion is an explicit exception in this portable version so optimization cannot bypass it.

All 120 detailed case records, original model/group/category tables and overlapping-tag tables were compared structurally against the preserved earlier analysis and matched. The separate recipe table is a deterministic projection of existing composition categories. The original evidence and earlier analysis were read only throughout packaging.
