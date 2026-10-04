"""Reproduce the public CSV benchmark analysis offline with explicit integrity checks."""
import argparse
import ast
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
MODELS = ('gemini', 'haiku')
STATUSES = ('adapted_pass', 'adapter_ineligible', 'eligible_json_unparseable', 'parsed_wrong')
OUTPUT_NAMES = {
    'analysis.json', 'model-summary.csv', 'group-summary.csv', 'category-summary.csv',
    'recipe-summary.csv', 'overlapping-failure-tags.csv', 'case-ledger.csv',
    'reproduction-receipt.json',
}
REQUIRED = {
    'analyze.py', 'analysis_helpers.py', 'scorer.py', 'data/contract.txt',
    'data/frozen-cases.json', 'data/frozen-plan.json',
    'data/gemini/primary-report.json', 'data/gemini/posthoc-diagnostics.json',
    'data/haiku/primary-report.json', 'data/haiku/posthoc-diagnostics.json',
}
FUNCTION_NAMES = {
    '_target_number', 'semantic', 'issue_semantic', 'score_v2', 'score',
    '_unique_object', '_reject_constant', 'parse_response', 'score_raw', 'fence_diagnostic',
}


class IntegrityError(ValueError):
    """The package or saved evidence failed an explicit validation."""


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(path.read_bytes())


def relative_file(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name,
            'unsafe manifest path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and str(p) == name,
            'unsafe manifest path')
    result = ROOT.joinpath(*p.parts)
    require(not result.is_symlink() and ROOT in result.resolve().parents,
            'manifest path escapes package')
    return result


def validate_manifest():
    manifest = load_json(ROOT / 'manifest.json')
    require(manifest.get('schema_version') == 1, 'unsupported manifest schema')
    files = manifest['files']
    require(REQUIRED <= set(files), 'manifest omits required inputs or code')
    for name, entry in sorted(files.items()):
        path = relative_file(name)
        require(path.is_file(), 'missing packaged file: ' + name)
        data = path.read_bytes()
        require(len(data) == entry['bytes'] and sha(data) == entry['sha256'],
                'SHA-256/size mismatch: ' + name)
    source = (ROOT / 'scorer.py').read_text(encoding='utf-8')
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)]
    require(len(nodes) == 10 and {n.name for n in nodes} == FUNCTION_NAMES,
            'isolated scorer function inventory changed')
    pure = '\n\n'.join(ast.get_source_segment(source, n) for n in nodes)
    require(sha(pure.encode('utf-8')) == manifest['frozen_hashes']['isolated_function_source_sha256'],
            'isolated scorer source fingerprint mismatch')
    require([r['model'] for r in manifest['runs']] == list(MODELS),
            'canonical run inventory changed')
    return manifest


def serialize_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def serialize_csv(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def analyze(manifest):
    # Imports happen only after source bytes pass manifest validation.
    import scorer
    from analysis_helpers import aggregate, candidate_details, ineligible_detail

    plan = load_json(ROOT / 'data' / 'frozen-plan.json')
    case_bytes = (ROOT / 'data' / 'frozen-cases.json').read_bytes()
    contract_bytes = (ROOT / 'data' / 'contract.txt').read_bytes()
    contract = contract_bytes.decode('utf-8')
    cases = json.loads(case_bytes)
    by_id = {c['id']: c for c in cases}
    selected = [c['id'] for c in cases if c['group'] != 'development']
    hashes = manifest['frozen_hashes']
    require(sha(contract_bytes) == plan['FROZEN_PROMPT_SHA256'] == hashes['contract_sha256'],
            'frozen contract hash mismatch')
    require(sha(case_bytes) == plan['SOURCE_MANIFEST']['portable_cases_sha256'] == hashes['case_payload_sha256'],
            'frozen case payload hash mismatch')
    require(len(cases) == len(by_id) == 72, 'frozen cases must contain 72 unique cases')
    require(selected == plan['FROZEN_EVALUATION_IDS'] and len(selected) == 60,
            'frozen evaluation case selection mismatch')
    require(scorer.OUTPUT_BYTE_LIMIT == plan['OUTPUT_BYTE_LIMIT'] and
            scorer.JSON_RESPONSE_LIMIT == plan['JSON_RESPONSE_LIMIT'], 'scorer limit mismatch')
    for case in cases:
        require(scorer.score_raw(case, json.dumps(case['expected'], ensure_ascii=False))['pass'],
                'frozen expected answer fails scorer: ' + case['id'])
    records, sources = [], []
    for run in manifest['runs']:
        model = run['model']
        primary_name = 'data/' + model + '/primary-report.json'
        posthoc_name = 'data/' + model + '/posthoc-diagnostics.json'
        require(run['primary_report'] == primary_name and run['posthoc_diagnostics'] == posthoc_name,
                'canonical report location mismatch')
        report = load_json(ROOT / primary_name)
        post = load_json(ROOT / posthoc_name)
        require(report['plan']['case_ids'] == selected, model + ': planned case IDs mismatch')
        require([r['case_id'] for r in report['rows']] == selected, model + ': primary case IDs mismatch')
        require([r['case_id'] for r in post['rows']] == selected, model + ': posthoc case IDs mismatch')
        require(report['abort'] is None, model + ': saved run aborted')
        require(report['plan']['model_key'] == post['model_key'] == run['model_key'],
                model + ': model identity mismatch')
        require(report['plan']['prompt_sha256'] == plan['FROZEN_PROMPT_SHA256'],
                model + ': contract declaration mismatch')
        require(report['plan']['grader_sha256'] == plan['FROZEN_GRADER_SHA256'] ==
                hashes['original_grader_sha256_declared'], model + ': grader declaration mismatch')
        require(report['plan']['source_manifest'] == plan['SOURCE_MANIFEST'],
                model + ': historical source declarations mismatch')
        source = {
            'model': model, 'model_key': run['model_key'],
            'primary_path': primary_name, 'primary_sha256': manifest['files'][primary_name]['sha256'],
            'posthoc_path': posthoc_name, 'posthoc_sha256': manifest['files'][posthoc_name]['sha256'],
            'source_url': run['source_url'],
        }
        sources.append(source)
        saved_diagnostics = {r['case_id']: r['diagnostic'] for r in post['rows']}
        for row in report['rows']:
            case = by_id[row['case_id']]
            raw = row['response_text']
            require(row['status'] == 'response_received' and isinstance(raw, str) and bool(raw),
                    model + ': missing response: ' + row['case_id'])
            require(row['group'] == case['group'] and row['recipe'] == case.get('recipe') and
                    row['transformation'] == case.get('transformation') and row['model_key'] == run['model_key'],
                    model + ': case metadata mismatch: ' + row['case_id'])
            request = json.dumps({'contract': contract, 'input': case['input']}, ensure_ascii=False)
            require(sha(request.encode('utf-8')) == row['prompt_sha256'],
                    model + ': request hash mismatch: ' + row['case_id'])
            primary = scorer.score_raw(case, raw)
            diagnostic = scorer.fence_diagnostic(case, raw)
            require(primary == row['primary'], model + ': primary verdict mismatch: ' + row['case_id'])
            require(diagnostic == saved_diagnostics[row['case_id']],
                    model + ': posthoc verdict mismatch: ' + row['case_id'])
            verdict = diagnostic['verdict'] if diagnostic else None
            status = ('adapter_ineligible' if diagnostic is None else
                      'eligible_json_unparseable' if not verdict['json_parseable'] else
                      'adapted_pass' if verdict['pass'] else 'parsed_wrong')
            result = {
                'model': model, 'model_key': row['model_key'], 'case_id': row['case_id'],
                'group': row['group'],
                'category': row['case_id'].rsplit('-', 1)[0] if row['recipe'] is None else
                            'composition_recipe_' + str(row['recipe']),
                'recipe': row['recipe'], 'transformation': row['transformation'],
                'request_sha256': row['prompt_sha256'], 'response_sha256': sha(raw.encode('utf-8')),
                'primary_report_sha256': source['primary_sha256'], 'source_url': source['source_url'],
                'chat_id': row['chat_id'], 'started_utc': row['started_utc'], 'ended_utc': row['ended_utc'],
                'response_characters': len(raw), 'reported_output_tokens': row['usage'].get('output_tokens'),
                'primary': primary, 'diagnostic': verdict, 'diagnostic_status': status,
                'adapter_ineligible_reason': ineligible_detail(raw) if diagnostic is None else None,
                'failure_tags': [], 'detail': None,
            }
            if verdict and verdict['json_parseable']:
                body = re.fullmatch(r'```json\r?\n(.*?)\r?\n```', raw, flags=re.DOTALL).group(1)
                actual = scorer.parse_response(body)
                tags, detail = candidate_details(case, actual)
                result.update(failure_tags=tags, detail=detail)
                require((not tags) == bool(verdict['pass']),
                        model + ': descriptive tags disagree with verdict: ' + row['case_id'])
                if not verdict['pass']:
                    result['expected'] = case['expected']
                    result['actual'] = actual
            records.append(result)
        # Validate the stored primary aggregate, without replacing the frozen score.
        model_rows = [r for r in records if r['model'] == model]
        strict_count = sum(r['primary']['pass'] for r in model_rows)
        require(report['summary']['strict_passes'] == strict_count and
                report['summary']['planned'] == report['summary']['received'] == 60 and
                report['summary']['missing'] == 0 and
                report['aggregate_strict_mean'] == report['summary']['strict_rate_planned'] == strict_count / 60,
                model + ': stored primary aggregate mismatch')
    require(len(records) == 120, 'expected exactly 120 response records')
    summary = [aggregate([r for r in records if r['model'] == m], model=m) for m in MODELS]
    group_summary = [aggregate([r for r in records if r['model'] == m and r['group'] == g], model=m, group=g)
                     for m in MODELS for g in ['original-evaluation-public', 'composition-evaluation-public']]
    categories = list(dict.fromkeys(r['category'] for r in records))
    category_summary = [aggregate([r for r in records if r['model'] == m and r['category'] == c], model=m, category=c)
                        for c in categories for m in MODELS]
    recipe_summary = [aggregate([r for r in records if r['model'] == m and r['recipe'] == recipe], model=m, recipe=recipe)
                      for recipe in sorted({r['recipe'] for r in records if r['recipe'] is not None}) for m in MODELS]
    failure_summary = [
        {'model': m, 'tag': tag, 'case_count': sum(r['model'] == m and tag in r['failure_tags'] for r in records)}
        for m in MODELS for tag in sorted({t for r in records for t in r['failure_tags']} |
                                         {'incorrect_target_for_eligible_row'})
    ]
    receipt = {
        'result': 'pass', 'offline_only': True,
        'case_requests_hash_verified': len(records), 'saved_primary_verdicts_reproduced': len(records),
        'saved_posthoc_verdicts_reproduced': len(records), 'expected_oracle_self_consistency_checks': len(cases),
        'contract_sha256_recomputed': sha(contract_bytes), 'portable_cases_sha256_recomputed': sha(case_bytes),
        'source_notebook_sha256_declared': manifest['source_notebook']['sha256'],
        'grader_sha256_declared': plan['FROZEN_GRADER_SHA256'],
        'original_grader_hash_verification': 'declaration-aligned only',
        'isolated_function_source_sha256': hashes['isolated_function_source_sha256'],
        'original_reports_byte_preserved': True,
        'grader_hash_caveat': 'Frozen grader hash agrees between the frozen declaration and both reports; its original serialization/hash recipe was unavailable, so that original hash was not independently recomputed. All saved verdicts were reproduced with extracted pure functions. The isolated-function fingerprint is separate, not a substitute.',
        'primary_report_sha256': {s['model']: s['primary_sha256'] for s in sources},
        'posthoc_report_sha256': {s['model']: s['posthoc_sha256'] for s in sources},
    }
    analysis = dict(proof=receipt, sources=sources, summary=summary, group_summary=group_summary,
                    category_summary=category_summary, recipe_summary=recipe_summary,
                    overlapping_failure_tags=failure_summary, cases=records)
    columns = ['model', 'model_key', 'case_id', 'group', 'category', 'recipe', 'transformation',
               'diagnostic_status', 'adapter_ineligible_reason', 'failure_tags', 'request_sha256',
               'response_sha256', 'primary_report_sha256', 'chat_id', 'started_utc', 'ended_utc',
               'response_characters', 'reported_output_tokens', 'source_url']
    ledger = [{k: ';'.join(r[k]) if isinstance(r[k], list) else r[k] for k in columns} for r in records]
    return {
        'analysis.json': serialize_json(analysis), 'model-summary.csv': serialize_csv(summary),
        'group-summary.csv': serialize_csv(group_summary), 'category-summary.csv': serialize_csv(category_summary),
        'recipe-summary.csv': serialize_csv(recipe_summary),
        'overlapping-failure-tags.csv': serialize_csv(failure_summary), 'case-ledger.csv': serialize_csv(ledger),
        'reproduction-receipt.json': serialize_json(receipt),
    }


def write_outputs(output_dir, outputs, manifest):
    out = output_dir.resolve()
    protected_paths = [ROOT / 'manifest.json'] + [relative_file(name) for name in manifest['files']]
    require(out != ROOT and all(out != p and out not in p.parents for p in protected_paths),
            'output directory overlaps protected package files')
    if out.exists():
        require(out.is_dir(), 'output destination is not a directory')
        require(all(p.name in OUTPUT_NAMES and p.is_file() and not p.is_symlink() for p in out.iterdir()),
                'output directory contains unrelated files; choose an empty directory')
    out.mkdir(parents=True, exist_ok=True)
    for name in sorted(outputs):
        (out / name).write_bytes(outputs[name])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'results',
                        help='dedicated output directory; default: results beside this script')
    args = parser.parse_args(argv)
    try:
        manifest = validate_manifest()
        outputs = analyze(manifest)
        write_outputs(args.output_dir, outputs, manifest)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        # Do not emit host-specific paths in normal result files or receipts.
        message = str(exc) if not isinstance(exc, OSError) else 'required file unavailable or filesystem write failed'
        print('ERROR: ' + message, file=sys.stderr)
        return 1
    print('Verified 120 prompt hashes, 120 primary verdicts, 120 posthoc verdicts, and 72 oracle cases.')
    print('Wrote 8 deterministic offline analysis artifacts. Original grader hash: declaration-aligned only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
