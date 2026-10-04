"""Offline reproducibility, integrity, and portability tests; standard library only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAMES = {
    'analysis.json', 'model-summary.csv', 'group-summary.csv',
    'category-summary.csv', 'recipe-summary.csv', 'overlapping-failure-tags.csv',
    'case-ledger.csv', 'reproduction-receipt.json',
}


class OfflinePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='CSV offline test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'unpacked supplement with spaces'
        shutil.copytree(ROOT, self.package, ignore=shutil.ignore_patterns(
            '__pycache__', 'results', '*.pyc'))
        self.cwd = self.root / 'another working directory'
        self.cwd.mkdir()

    def run_cli(self, *args, optimized=False, seed='42'):
        script = self.package / 'analyze.py'
        self.assertTrue(script.is_file(), 'portable offline runner is not implemented')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED=seed,
                   PYTHONUTF8='1')
        command = [sys.executable, '-B']
        if optimized:
            command.append('-O')
        return subprocess.run(command + [str(script), *map(str, args)], cwd=self.cwd,
                              env=env, encoding='utf-8', capture_output=True)

    def assert_integrity_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('ERROR:', result.stderr)
        self.assertFalse((self.package / 'results').exists(),
                         'integrity failure must happen before writing results')

    def test_reproduces_all_saved_verdicts_and_prompt_hashes(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = self.package / 'results'
        self.assertEqual({p.name for p in outputs.iterdir()}, OUTPUT_NAMES)
        receipt = json.loads((outputs / 'reproduction-receipt.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['case_requests_hash_verified'], 120)
        self.assertEqual(receipt['saved_primary_verdicts_reproduced'], 120)
        self.assertEqual(receipt['saved_posthoc_verdicts_reproduced'], 120)
        self.assertEqual(receipt['expected_oracle_self_consistency_checks'], 72)
        self.assertEqual(receipt['original_grader_hash_verification'], 'declaration-aligned only')
        for name in OUTPUT_NAMES:
            self.assertEqual((outputs / name).read_bytes(),
                             (self.package / 'expected' / name).read_bytes(), name)
        analysis = json.loads((outputs / 'analysis.json').read_text(encoding='utf-8'))
        self.assertEqual(len(analysis['cases']), 120)
        by_model = {r['model']: r for r in analysis['summary']}
        self.assertEqual(by_model['gemini']['adapted_pass'], 59)
        self.assertEqual(by_model['haiku']['adapted_pass'], 14)
        self.assertEqual(by_model['haiku']['parsed_wrong'], 38)
        self.assertEqual(by_model['haiku']['diagnostic_destructive_rows'], 55)
        self.assertTrue(all(r['strict_pass'] == 0 for r in analysis['summary']))
        tags = {(r['model'], r['tag']): r['case_count'] for r in analysis['overlapping_failure_tags']}
        self.assertEqual(tags['haiku', 'emitted_blocked_source_row'], 31)
        self.assertEqual(tags['haiku', 'protected_cell_change'], 8)
        self.assertEqual(tags['haiku', 'protected_string_value_change'], 7)
        self.assertEqual(tags['haiku', 'omitted_eligible_source_row'], 12)
        self.assertEqual(len(analysis['recipe_summary']), 12)

    def test_deterministic_across_cwd_paths_and_hash_seeds(self):
        first = self.root / 'results one'
        second = self.root / 'results two'
        a = self.run_cli('--output-dir', first, seed='1')
        b = self.run_cli('--output-dir', second, seed='987654')
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()},
                         {p.name: p.read_bytes() for p in second.iterdir()})
        c = self.run_cli('--output-dir', first, seed='2')
        self.assertEqual(c.returncode, 0, c.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()},
                         {p.name: p.read_bytes() for p in second.iterdir()})

    def test_corrupted_primary_report_is_rejected(self):
        path = self.package / 'data' / 'gemini' / 'primary-report.json'
        self.assertTrue(path.is_file(), 'packaged primary evidence is missing')
        path.write_bytes(path.read_bytes() + b' ')
        self.assert_integrity_failure(self.run_cli())

    def test_corruption_is_rejected_with_python_optimization(self):
        path = self.package / 'data' / 'haiku' / 'posthoc-diagnostics.json'
        self.assertTrue(path.is_file(), 'packaged posthoc evidence is missing')
        path.write_bytes(path.read_bytes() + b' ')
        self.assert_integrity_failure(self.run_cli(optimized=True))

    def test_missing_frozen_payload_is_rejected(self):
        path = self.package / 'data' / 'frozen-cases.json'
        self.assertTrue(path.is_file(), 'frozen payload is missing')
        path.unlink()
        self.assert_integrity_failure(self.run_cli())

    def test_changed_scorer_source_is_rejected(self):
        path = self.package / 'scorer.py'
        self.assertTrue(path.is_file(), 'extracted scorer is missing')
        path.write_bytes(path.read_bytes() + b'\n# changed\n')
        self.assert_integrity_failure(self.run_cli(optimized=True))

    def test_missing_manifest_is_rejected(self):
        path = self.package / 'manifest.json'
        self.assertTrue(path.is_file(), 'manifest is missing')
        path.unlink()
        self.assert_integrity_failure(self.run_cli())

    def test_manifest_cannot_escape_package(self):
        path = self.package / 'manifest.json'
        self.assertTrue(path.is_file(), 'manifest is missing')
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['files']['../outside'] = {'sha256': '0' * 64, 'bytes': 0}
        path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assert_integrity_failure(self.run_cli())

    def test_output_cannot_overwrite_inputs(self):
        result = self.run_cli('--output-dir', self.package / 'data')
        self.assert_integrity_failure(result)

    def test_output_cannot_overwrite_unrelated_files(self):
        target = self.root / 'occupied output'
        target.mkdir()
        (target / 'important.txt').write_text('retain', encoding='utf-8')
        result = self.run_cli('--output-dir', target)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ERROR:', result.stderr)
        self.assertEqual((target / 'important.txt').read_text(encoding='utf-8'), 'retain')
        self.assertEqual(len(list(target.iterdir())), 1)

    def test_standard_library_and_no_network_or_dynamic_code(self):
        import ast
        allowed = {'argparse', 'ast', 'collections', 'csv', 'hashlib', 'io', 'json',
                   'pathlib', 're', 'sys', 'unicodedata', 'scorer', 'analysis_helpers'}
        for name in ('analyze.py', 'analysis_helpers.py', 'scorer.py'):
            path = self.package / name
            self.assertTrue(path.is_file(), 'offline code is missing')
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(n.name in allowed for n in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, allowed)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {'exec', 'eval', '__import__', 'compile'})


if __name__ == '__main__':
    unittest.main()
