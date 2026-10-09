"""Verify wheel/source parity and deterministic integration mechanics without a provider."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import hermeneutic
from hermeneutic import Router
from hermeneutic.hermes_agent_plugin import check_outgoing_claims

SAMPLES = {'ko': '5개 파일을 수정했습니다.', 'ja': '5件の修正が完了しました。',
           'zh': '已完成 5 个文件。', 'es': 'He completado 5 archivos.'}
ENGLISH = 'Done — shipped 14 files and all 92 tests pass.'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    installed = Path(hermeneutic.__file__).resolve().parent
    bundled = args.source_root / 'src/hermeneutic'
    source_files = sorted(bundled.rglob('*.py'))
    assert source_files
    for source in source_files:
        assert digest(source) == digest(installed / source.relative_to(bundled)), source
    clean_env = dict(os.environ)
    clean_env.pop('PYTHONPATH', None)
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix='hermeneutic-integration-mechanics-') as directory:
        os.environ['HERMENEUTIC_QWEN_STATE_DIR'] = str(Path(directory) / 'qwen')
        hooks = {}
        for name, relative in [('gemini', 'integrations/gemini-cli/hermeneutic_after_agent.py'),
                               ('qwen', 'integrations/qwen-code/hermeneutic_stop.py')]:
            spec = importlib.util.spec_from_file_location(name, args.source_root / relative)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            hooks[name] = module
        for code, draft in SAMPLES.items():
            for selector in (code, 'auto'):
                result = subprocess.run([sys.executable, '-I', '-m', 'hermeneutic.cli', 'gate', '--lang', selector],
                                        input=draft, text=True, capture_output=True, env=clean_env)
                assert result.returncode == 0 and 'ADVISORY' in result.stdout, (code, selector, result.stdout)
                mixed = subprocess.run([sys.executable, '-I', '-m', 'hermeneutic.cli', 'gate', '--lang', selector],
                                       input=draft + '\n' + ENGLISH, text=True, capture_output=True, env=clean_env)
                assert mixed.returncode == 1, (code, selector, mixed.stdout)

            class ForbiddenProbe:
                def review(self, *args):
                    raise AssertionError('Mapping-only draft must not call a reviewer')

            assert Router(probe=ForbiddenProbe(), use_rubric=False, lang=code).gate('check', draft).final_output == draft
            assert check_outgoing_claims(draft).startswith(draft + '\n\n[Hermeneutic evidence check:')
            for name, key in [('gemini', 'prompt_response'), ('qwen', 'last_assistant_message')]:
                response = hooks[name].evaluate({key: draft, 'session_id': code})
                assert response.get('decision', 'allow') == 'allow' and 'language advisory' in response['systemMessage']
                mixed = hooks[name].evaluate({key: draft + '\n' + ENGLISH, 'session_id': code})
                assert mixed['decision'] == ('deny' if name == 'gemini' else 'block')
            outcomes[code] = 'CLI explicit/auto advisory, raw English enforcement, Router and response-hook mechanics pass'
    result = {'version': hermeneutic.__version__, 'wheel_source_python_files_equal': len(source_files),
              'languages': outcomes, 'boundary': 'Installed artifact and simulated hook payloads; no running third-party host delivery claim.'}
    content = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(content)
    print(content)


if __name__ == '__main__':
    main()
