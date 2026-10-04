# Offline supplement audit receipt

Date: 2026-10-04. Scope: local-only preparation and verification; no model inference, benchmark rerun, upload or publication.

## Verification result

- All 11 standard-library tests passed on Linux, Python 3.12.14.
- Tests were written before the portable runner and integrity layer; the initial red run had 11 expected failures because the new runner/data package did not yet exist. After implementation, all 11 passed.
- The frozen primary metric remains unchanged: 0/60 for each model. All 120 primary mutation outcomes remain unknown.
- All 120 prompt hashes, 120 primary verdicts and 120 posthoc outcomes reproduce exactly, including ineligible diagnostics. All 72 expected answers pass scorer self-consistency checks.
- All 120 full detailed case records and every original model/group/category/overlapping-tag table match the preserved prior analysis. The new recipe table groups the same composition results.
- All four bundled raw reports match the original evidence byte-for-byte. The 33 original evidence/analysis files were rehashed and remained unchanged.
- An independent fresh-directory audit also reproduced the outputs while a Python audit hook denied socket, subprocess and external-process operations.

## Portability and integrity

The test suite invokes the copied package from a different working directory, with spaces in both package and output paths. Byte outputs match across different Python hash seeds and repeated invocations. Integrity failures are explicit and nonzero for altered raw evidence, altered scorer source, a missing frozen payload, and a missing manifest. Tests also verify corruption detection under `python -O`, manifest traversal rejection, and protection against overwriting packaged inputs or unrelated output-directory files.

Python 3.8 is the intended minimum supported API level. The executed test environment was Python 3.12.14 on Linux. Windows and macOS were not directly executed; portability there is structural (standard library, pathlib, explicit UTF-8/LF, no shell commands in the runner) and tested through working-directory/path variation on Linux. An existing Python interpreter is required; no setup download or third-party package is required by the supplement.

## Security/content review

The release inventory is allowlisted to public synthetic evidence, frozen input/oracle bytes, extracted pure offline functions, deterministic derived analysis and public documentation. No full notebook, executable benchmark driver, original output ZIP, provider traces, private notes, machine-specific absolute paths, credentials, signed download URLs, bytecode cache or temporary test files are included. Source links are stable public Kaggle/article links; no code opens them.

Production code uses only standard-library imports plus the two bundled local modules. It contains no network, provider SDK, subprocess, dynamic execution or package-install calls. Content/pattern checks are a review aid, not a guarantee against adversarially disguised secrets. The exact saved synthetic Unicode edge cases are intentionally retained as evidence.

The manifest covers every distributed file except itself. File checksums establish identity to that manifest, not authenticity against a malicious simultaneous manifest edit. The original frozen grader hash is declaration-aligned only because its original hashing recipe was unavailable. The independently computed pure-function fingerprint is separate and never presented as reconstruction of that original hash.

## Recheck

From the unpacked package directory:

```sh
python3 -B analyze.py
python3 -B -m unittest discover -s tests -v
```

Both commands must exit 0. Inspect `results/reproduction-receipt.json` and compare all files under `results/` with `expected/`. The release archive itself is accompanied by a separate SHA-256 sidecar because an archive cannot contain its own final hash.
