"""Pure scorer functions copied verbatim from the public frozen notebook source.

Only standard-library imports and the original numeric size limits precede them.
There is no benchmark driver, SDK, network access, or model invocation here.
The source-only fingerprint is separately recorded in manifest.json.
"""
import csv
import io
import json
import re

OUTPUT_BYTE_LIMIT = 15_000_000
JSON_RESPONSE_LIMIT = 32_000_000

def _target_number(value):
    # Independent of reference canonical_integer: only the editable target is numeric.
    if not re.fullmatch(r'[+-]?[0-9]+', value):
        raise ValueError('target must be an ASCII integer')
    negative = value[0] == '-'
    digits = value[1:] if value[0] in '+-' else value
    digits = digits.lstrip('0') or '0'
    return ('-' if negative and digits != '0' else '') + digits

def semantic(text, normalize_targets=True, max_bytes=OUTPUT_BYTE_LIMIT):
    """Independent scorer parser: bounded UTF-8, one optional BOM, exact cells."""
    if not isinstance(text, str) or len(text.encode('utf-8')) > max_bytes:
        raise ValueError('invalid or oversized CSV')
    if text.startswith('\ufeff'):
        text = text[1:]
        if text.startswith('\ufeff'):raise ValueError('repeated BOM')
    try:
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        h = next(reader)
        if not h or any(not x for x in h) or len(set(h)) != len(h):raise ValueError('invalid headers')
        rows = []
        for cells in reader:
            if len(cells) != len(h):raise ValueError('ragged CSV')
            row = dict(zip(h,cells))
            if normalize_targets and 'On hand (new)' in row:
                row['On hand (new)'] = _target_number(row['On hand (new)'])
            rows.append(row)
    except (StopIteration,csv.Error) as e:
        raise ValueError('invalid CSV') from e
    return set(h), rows

def issue_semantic(items):
    # Reject duplicates, ill-shaped reports, booleans as record numbers.
    if not isinstance(items,list): raise ValueError('issues is not a list')
    result=[]
    for x in items:
        if set(x)!={'source','record','codes'} or x['source'] not in ('export','counts') or type(x['record']) is not int or x['record']<2:
            raise ValueError('bad issue record')
        if not isinstance(x['codes'],list) or not x['codes'] or any(not isinstance(c,str) for c in x['codes']) or len(set(x['codes']))!=len(x['codes']):
            raise ValueError('bad codes')
        result.append((x['source'],x['record'],tuple(sorted(x['codes']))))
    if len(set((x[0],x[1]) for x in result))!=len(result):raise ValueError('duplicate issue record')
    return sorted(result)

def score_v2(case, response):
    """Deterministic exact semantic success and destructive-row rate (not a model judge)."""
    expected=case['expected']; passed=False; reason='invalid response'; destructive=0
    try:
        if not isinstance(response,dict) or set(response)!={'candidate_csv','issues','error'}:raise ValueError('response shape')
        issues_ok=issue_semantic(response['issues'])==issue_semantic(expected['issues'])
        if expected['error']:
            passed=response['error']==expected['error'] and response['candidate_csv'] is None and issues_ok
        else:
            passed=response['error'] is None and isinstance(response['candidate_csv'],str) and semantic(response['candidate_csv'])==semantic(expected['candidate_csv']) and issues_ok
        reason='pass' if passed else 'semantic mismatch'
    except (ValueError,TypeError,KeyError,AttributeError):pass
    # A destructive row is any emitted row other than an unused exact expected row.
    # This catches changed protected cells, wrong targets, blocked rows and fabricated rows.
    # Omission is measured by semantic success, not destructive mutation.
    try:
        if not isinstance(response,dict) or set(response)!={'candidate_csv','issues','error'}:raise ValueError('response shape')
        try:
            source_h,source_rows=semantic(case['input']['export_csv'], normalize_targets=False, max_bytes=32_000_000)
        except ValueError:
            # A fatal source-format error with no emitted candidate is nondestructive.
            # Any emitted candidate against an unparseable source is conservatively unsafe.
            source_h,source_rows=None,[]
        denominator=max(1,len(source_rows))
        allowed=[] if expected['candidate_csv'] is None else semantic(expected['candidate_csv'])[1]
        if response.get('candidate_csv') is not None:
            h,actual=semantic(response['candidate_csv'])
            if h!=source_h: destructive=max(1,len(actual))
            else:
                remaining=allowed.copy()
                for row in actual:
                    if row in remaining: remaining.remove(row)
                    else: destructive+=1
        rate=min(1.0,destructive/denominator)
    except (ValueError,TypeError,KeyError,AttributeError):
        denominator=1;destructive=1;rate=1.0
    return {'pass':passed,'reason':reason,'destructive_rows':destructive,'source_rows':denominator,'destructive_rate':rate}

def score(case, response):
    """Revision 4: failure is distinct from observed mutation; never impute mutation."""
    legacy=score_v2(case,response)
    shaped=isinstance(response,dict) and set(response)=={'candidate_csv','issues','error'}
    shaped=shaped and (response['candidate_csv'] is None or isinstance(response['candidate_csv'],str))
    shaped=shaped and (response['error'] is None or isinstance(response['error'],str))
    try:
        if not shaped:raise ValueError('shape')
        issue_semantic(response['issues'])
        format_ok=True
    except (ValueError,TypeError,KeyError,AttributeError):format_ok=False
    semantic_correct=None
    mutation_assessable=False
    rows=rate=denominator=None
    try:
        if not shaped:raise ValueError('shape')
        candidate=response['candidate_csv']
        actual=[]
        if candidate is not None:
            h,actual=semantic(candidate,normalize_targets=False)
            for row in actual:
                if 'On hand (new)' in row:
                    try:row['On hand (new)']=_target_number(row['On hand (new)'])
                    except ValueError:pass
        if format_ok:semantic_correct=legacy['pass']
        mutation_assessable=True
        try:source_h,source_rows=semantic(case['input']['export_csv'],normalize_targets=False,max_bytes=32_000_000)
        except ValueError:source_h,source_rows=None,[]
        denominator=max(1,len(source_rows));rows=0
        expected=case['expected']['candidate_csv']
        allowed=[] if expected is None else semantic(expected)[1]
        if candidate is not None:
            if h!=source_h:rows=max(1,len(actual))
            else:
                remaining=allowed.copy()
                for row in actual:
                    if row in remaining:remaining.remove(row)
                    else:rows+=1
        rate=min(1.0,rows/denominator)
    except (ValueError,TypeError,KeyError,AttributeError):pass
    return {'pass':bool(legacy['pass'] and format_ok),'format_compliance':format_ok,
            'semantic_correct':semantic_correct,'mutation_assessable':mutation_assessable,
            'destructive_rows':rows,'source_rows':denominator,'destructive_rate':rate,
            'reason':legacy['reason'],'scorer_revision':4}

def _unique_object(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate JSON key')
        out[key]=value
    return out

def _reject_constant(value):raise ValueError('nonfinite JSON constant')

def parse_response(raw):
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>JSON_RESPONSE_LIMIT:raise ValueError('invalid/oversized response')
    return json.loads(raw,object_pairs_hook=_unique_object,parse_constant=_reject_constant)

def score_raw(case,raw):
    """Primary strict score; fences never accepted, unknown mutation remains null."""
    try:
        response=parse_response(raw)
        verdict=score(case,response)
        verdict.update(json_parseable=True,parse_error=None)
    except (ValueError,TypeError) as exc:
        verdict=score(case,None)
        verdict.update(json_parseable=False,parse_error=type(exc).__name__)
    return verdict

def fence_diagnostic(case,raw):
    """Post hoc only: exactly one complete json fence, no prose or nested fences."""
    if not isinstance(raw,str):return None
    match=re.fullmatch(r'```json\r?\n(.*?)\r?\n```',raw,flags=re.DOTALL)
    if not match or '```' in match.group(1):return None
    return {'label':'posthoc_single_json_fence_only_not_primary',
            'verdict':score_raw(case,match.group(1))}
