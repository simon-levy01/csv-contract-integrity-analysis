"""Secondary descriptive analysis, separate from the unchanged frozen scorer.

Lineage rules and failure tags preserve the prior offline analysis. The sole
assertion is replaced by an explicit exception so python -O keeps validation.
These tags overlap and never change primary or post hoc benchmark scores.
"""
import collections
import re
import unicodedata
import scorer

def normalized_rows(text):
    if text is None:
        return None, []
    headers, rows = scorer.semantic(text, normalize_targets=False)
    for row in rows:
        if 'On hand (new)' in row:
            try:
                row['On hand (new)'] = scorer._target_number(row['On hand (new)'])
            except ValueError:
                pass
    return headers, rows

def protected(row):
    return {k: v for k, v in row.items() if k != 'On hand (new)'}

def frozen_row(row):
    return tuple(sorted(row.items()))

def triples(issues):
    return {(i['source'], i['record'], code) for i in issues for code in i['codes']}

def candidate_details(case, actual):
    """Secondary descriptive tags; these do not change the frozen score.

    Source lineage is exact on all protected cells when possible. Otherwise it
    requires a unique nearest source row with just one changed protected cell.
    No general fuzzy matching is used. Ambiguous mapping stays unresolved.
    Omission means an eligible source row has no emitted counterpart; changes
    to a emitted row's protected cell are counted separately, not as omissions.
    """
    expected = case['expected']
    tags = set()
    details = {}
    if actual['error'] != expected['error']:
        tags.add('false_fatal_error' if expected['error'] is None else
                 'missed_fatal_error' if actual['error'] is None else 'wrong_fatal_error')
    mi = sorted(triples(expected['issues']) - triples(actual['issues']))
    si = sorted(triples(actual['issues']) - triples(expected['issues']))
    details.update(missing_issue_codes=mi, spurious_issue_codes=si)
    if mi or si:
        tags.add('incorrect_issue_report')
    if actual['candidate_csv'] is None and expected['candidate_csv'] is not None:
        tags.add('null_candidate_instead_of_csv')
    try:
        sh, source_rows = scorer.semantic(case['input']['export_csv'], normalize_targets=False, max_bytes=32_000_000)
    except ValueError:
        sh, source_rows = None, []
    eh, erows = normalized_rows(expected['candidate_csv'])
    try:
        ah, arows = normalized_rows(actual['candidate_csv'])
    except ValueError:
        tags.add('malformed_candidate_csv')
        return sorted(tags), details
    if actual['candidate_csv'] is not None and ah != sh:
        tags.add('changed_candidate_headers')
    if ah == eh and collections.Counter(map(frozen_row, arows)) == collections.Counter(map(frozen_row, erows)) and arows != erows:
        tags.add('row_order_only_candidate_mismatch')
    expected_sources = {}
    for erow in erows:
        matches = [i + 2 for i, s in enumerate(source_rows) if protected(s) == protected(erow)]
        if len(matches) != 1:
            raise ValueError('ambiguous expected source lineage: ' + case['id'])
        expected_sources[matches[0]] = erow
    emitted = []
    mapped_source_records = []
    for index, row in enumerate(arows, 2):
        diffs = [{k: {'source': s.get(k), 'emitted': row.get(k)}
                  for k in set(s) | set(row) if k != 'On hand (new)' and s.get(k) != row.get(k)}
                 for s in source_rows]
        exact = [i for i, d in enumerate(diffs) if not d]
        candidates = exact or [i for i, d in enumerate(diffs) if len(d) == 1]
        record = candidates[0] + 2 if len(candidates) == 1 else None
        item = {'candidate_record': index, 'source_record': record, 'source_link':
                'exact_protected_cells' if exact else 'unique_one_protected_cell_difference' if record else 'unresolved'}
        if record is None:
            tags.add('unresolved_emitted_row')
        else:
            mapped_source_records.append(record)
            changed = diffs[record - 2]
            item['changed_protected_cells'] = changed
            if changed:
                tags.add('protected_cell_change')
                if any(k in row and k in source_rows[record - 2] for k in changed):
                    tags.add('protected_string_value_change')
                if any(unicodedata.normalize('NFC', d['source']) == d['emitted'] for d in changed.values() if isinstance(d['source'], str) and isinstance(d['emitted'], str)):
                    tags.add('unicode_nfc_normalization')
                if any('\ufeff' in (d['source'] or '') and '\u202e' in (d['emitted'] or '') for d in changed.values()):
                    tags.add('interior_bom_replaced_with_bidi_control')
            if record not in expected_sources:
                tags.add('emitted_blocked_source_row')
                item['blocked_source_row'] = True
                item['expected_source_issues'] = [i for i in expected['issues'] if i['source'] == 'export' and i['record'] == record]
            elif row.get('On hand (new)') != expected_sources[record].get('On hand (new)'):
                tags.add('incorrect_target_for_eligible_row')
                item['incorrect_target'] = {'expected': expected_sources[record].get('On hand (new)'), 'actual': row.get('On hand (new)')}
            mapping = case['input']['mapping']
            try:
                _, count_rows = scorer.semantic(case['input']['count_csv'], normalize_targets=False)
                src = source_rows[record - 2]
                matches = [c for c in count_rows if c.get(mapping['sku']) == src.get('SKU') and c.get(mapping['location']) == src.get('Location')]
                if len(matches) == 1:
                    original_count = matches[0][mapping['quantity']]
                    if not re.fullmatch(r'[+-]?[0-9]+', original_count) and re.fullmatch(r'[+-]?[0-9]+', row.get('On hand (new)', '')):
                        tags.add('integer_emitted_despite_invalid_count')
                        item['invalid_source_quantity_to_emitted_target'] = {'count': original_count, 'target': row.get('On hand (new)')}
            except (ValueError, TypeError, KeyError):
                pass
        try:
            scorer._target_number(row.get('On hand (new)', ''))
        except (ValueError, TypeError):
            tags.add('invalid_emitted_target')
            item['invalid_emitted_target'] = row.get('On hand (new)')
        emitted.append(item)
    omitted = sorted(set(expected_sources) - set(mapped_source_records))
    if omitted:
        tags.add('omitted_eligible_source_row')
    details.update(expected_candidate_rows=len(erows), emitted_candidate_rows=len(arows),
                   omitted_eligible_source_records=omitted, emitted_row_analysis=emitted)
    return sorted(tags), details

def ineligible_detail(raw):
    # Descriptive only: no extraction or further scoring of ineligible bodies.
    blocks = re.findall(r'```json\r?\n.*?\r?\n```', raw, re.DOTALL)
    if len(blocks) > 1:
        return 'multiple_complete_json_fences_with_surrounding_text'
    if blocks:
        return 'surrounding_text_outside_complete_json_fence'
    if raw.startswith('```json') and not raw.endswith('```'):
        return 'incomplete_json_and_unclosed_fence'
    return 'other_noncanonical_wrapper'

def aggregate(rows, **labels):
    diagnostic = [r['diagnostic'] for r in rows if r['diagnostic'] is not None]
    return dict(labels, n=len(rows), strict_pass=sum(r['primary']['pass'] for r in rows),
                strict_mutation_unknown=sum(not r['primary']['mutation_assessable'] for r in rows),
                **{status: sum(r['diagnostic_status'] == status for r in rows) for status in
                   ['adapted_pass', 'adapter_ineligible', 'eligible_json_unparseable', 'parsed_wrong']},
                diagnostic_mutation_assessable=sum(d['mutation_assessable'] for d in diagnostic),
                diagnostic_mutation_positive_cases=sum(d['destructive_rows'] > 0 for d in diagnostic if d['mutation_assessable']),
                diagnostic_destructive_rows=sum(d['destructive_rows'] for d in diagnostic if d['mutation_assessable']))
