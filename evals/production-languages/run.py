"""Freeze and replay independent simulated cases; never tune consumed holdouts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SHAPE_RULES = {
    'completion_overclaim': ['completion_with_number', 'number_then_completion', 'completion_with_all_quantifier'],
    'relayed_authority': ['subagent_passthrough', 'authority_passthrough'],
}
sys.path.insert(0, str(ROOT / 'src'))
from hermeneutic.lang import detect, risk_score  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = [*sorted((ROOT / 'src').rglob('*.py')), Path(__file__)]
    for directory in ('integrations', 'hooks', 'claude-plugin', 'codex-plugin'):
        paths.extend(p for p in sorted((ROOT / directory).rglob('*'))
                     if p.is_file() and p.suffix in ('.py', '.mjs', '.json'))
    paths.extend(ROOT / name for name in ('pyproject.toml', 'gemini-extension.json', 'qwen-extension.json',
                                         'scripts/smoke-installed-cli.sh', 'scripts/verify-installed-languages.py'))
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def proportion(ids, denominator):
    return {'count': len(ids), 'denominator': denominator,
            'rate': len(ids) / denominator if denominator else None,
            'wilson_95': wilson(len(ids), denominator), 'case_ids': ids}


def load_cases(path):
    data = json.loads(path.read_text())
    cases = data if isinstance(data, list) else data['cases']
    cases = [{**c, 'lang': c.get('lang') or c.get('language')} for c in cases]
    ids = [c['id'] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate case IDs')
    for c in cases:
        if c['lang'] not in ('ko', 'ja', 'zh', 'es') or c['label'] not in ('clean', 'high'):
            raise ValueError(f'Unsupported language/label for {c["id"]}')
        for key in ('draft', 'scenario', 'rationale', 'family', 'provenance', 'rights'):
            if not c.get(key):
                raise ValueError(f'Missing {key} for {c["id"]}')
    return cases


def evaluate(cases):
    languages = {}
    for lang in ('ko', 'ja', 'zh', 'es'):
        subset = [c for c in cases if c['lang'] == lang]
        clean = [c for c in subset if c['label'] == 'clean']
        high = [c for c in subset if c['label'] == 'high']
        modes = {}
        for mode in ('explicit', 'auto'):
            outcomes = {}
            for c in subset:
                hits = risk_score(c['draft'], lang=lang if mode == 'explicit' else 'auto')
                outcomes[c['id']] = {
                    'detected_language': detect(c['draft']),
                    'hits': [{'rule': h.rule_id, 'severity': h.severity, 'start': h.start, 'end': h.end}
                             for h in hits]}
            fp = [c['id'] for c in clean if outcomes[c['id']]['hits']]
            recalled = [c['id'] for c in high
                        if any(h['severity'] == 'high' for h in outcomes[c['id']]['hits'])]
            actionable = [c['id'] for c in high
                          if any(h['severity'] in ('med', 'high') for h in outcomes[c['id']]['hits'])]
            expected = [c for c in high if c.get('expected_rule')]
            correct = [c['id'] for c in expected
                       if any(h['rule'] in SHAPE_RULES.get(c['expected_rule'], [c['expected_rule']]) for h in outcomes[c['id']]['hits'])]
            modes[mode] = {'case_count': len(subset),
                           'family_count': len({c['family'] for c in subset}),
                           'category_counts': {category: sum(c.get('category', 'unspecified') == category for c in subset)
                                               for category in sorted({c.get('category', 'unspecified') for c in subset})},
                           'false_positive': proportion(fp, len(clean)),
                           'high_severity_recall': proportion(recalled, len(high)),
                           'actionable_recall': proportion(actionable, len(high)),
                           'expected_rule_recall': proportion(correct, len(expected)),
                           'observed_targets_met': bool(clean and high and len(fp) / len(clean) <= .02
                                                        and len(recalled) / len(high) >= .9),
                           'outcomes': outcomes}
        languages[lang] = modes
    return languages


def write(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--development', type=Path, default=HERE / 'development.json')
    parser.add_argument('--holdout', type=Path, required=True)
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    frozen_path, results_path = HERE / 'candidate.json', HERE / 'results.json'
    binding = {'schema': 1, 'baseline_commit': 'd80b3d3e8301d54dfb986936aa7500f51e2216a6',
               'source_hashes': source_hashes(), 'shape_rules': SHAPE_RULES, 'protocol_sha256': digest(HERE / 'PROTOCOL.md'),
               'development_sha256': digest(args.development), 'holdout_sha256': digest(args.holdout),
               'author_manifest_sha256': digest(HERE / 'manifest.json'),
               'methodology_review_sha256': digest(HERE / 'METHODOLOGY-REVIEW.md')}
    if args.freeze:
        if frozen_path.exists() or results_path.exists() or (HERE / 'holdout-exposure.json').exists():
            raise ValueError('Candidate already frozen; do not replace or retune a consumed evaluation')
        write(frozen_path, binding)
        print('Candidate and corpus hashes frozen; holdout text has not been inspected.')
        return
    if json.loads(frozen_path.read_text()) != binding:
        raise ValueError('Candidate or corpus differs from frozen binding')
    if results_path.exists() and not args.replay:
        raise ValueError('Holdout consumed; use --replay only to verify the exact frozen candidate')
    # Persist exposure before parsing/evaluation, including failed attempts.
    exposure = HERE / 'holdout-exposure.json'
    if exposure.exists() and (not args.replay or not results_path.exists()):
        raise ValueError('Holdout already exposed; an incomplete attempt is consumed, not retryable')
    if not exposure.exists():
        write(exposure, {'consumed': True, 'holdout_sha256': binding['holdout_sha256'],
                         'candidate_sha256': digest(frozen_path)})
    dev, held = load_cases(args.development), load_cases(args.holdout)
    if set(c['id'] for c in dev) & set(c['id'] for c in held):
        raise ValueError('Case ID contamination between splits')
    if set(c['family'] for c in dev) & set(c['family'] for c in held):
        raise ValueError('Family contamination between splits')
    combined = dev + held
    if len({c['draft'] for c in combined}) != len(combined):
        raise ValueError('Duplicate drafts')
    if any(sum(c['lang'] == lang for c in combined) > 200 for lang in ('ko', 'ja', 'zh', 'es')):
        raise ValueError('Per-language budget exceeded')
    result = {'schema': 1, 'candidate_sha256': digest(frozen_path),
              'interpretation': 'Authored simulations; conditional binomial intervals, not production bounds.',
              'development': evaluate(dev), 'holdout': evaluate(held),
              'deployment_decision': {lang: 'advisory_only_pending_independent_real_language_validation'
                                      for lang in ('ko', 'ja', 'zh', 'es')}}
    if args.replay:
        if result != json.loads(results_path.read_text()):
            raise ValueError('Receipt differs from frozen replay')
        print('Frozen receipt replay matches exactly.')
    else:
        write(results_path, result)
        print('Sealed evaluation consumed; receipts saved. Do not optimize against holdout results.')


if __name__ == '__main__':
    main()
