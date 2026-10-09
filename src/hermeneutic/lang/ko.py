"""Experimental Korean trigger mapping, ported from the Korean prototype.

One English gate; local vocabulary maps to its canonical triggers, without
translating the draft. Digits, punctuation and unmapped text remain intact.
Past-tense completion and planned work deliberately map differently.
See ``evals/languages/README.md`` for synthetic validation and limitations.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import substitute

# (korean_pattern, canonical_english_trigger) — most-specific first.
_MAP: list[tuple[str, str]] = [
    # Unicode letters next to digits defeat the English gate's word boundary.
    (r"(?<=[가-힣])(\d+(?:\.\d+)?)", r" \1"),
    # Expose the English gate's existing contrast guard to Korean partials.
    (r"(했|됐|되었|하였)지만", r"\1 but "),
    (r"하지만|그러나|그런데|지만", " but "),
    (r"아직|나머지|남아|남았|진행 중|작업 중|테스트 중", " remaining "),
    # --- number + counter: Korean counters attach directly to digits (8개,
    # 47건) and Hangul is a word character, so the gate's \d+\b never ends a
    # match there. Strip the counter, keep the digit.
    (r"(\d+(?:\.\d+)?)\s*(개의|개|건|번|명|줄|가지|차례)", r"\1 "),
    # --- code-switched completion: real Korean dev chat conjugates English
    # stems ("patch했으니", "fixed 됐어요", "merge 완료").
    (
        r"(patch|fix(?:ed)?|merge[d]?|deploy(?:ed)?|refactoring|release[d]?|ship(?:ped)?)"
        r"\s*(했|됐|되었|돼 ?있|해 ?놨|해 ?뒀)",
        " completed ",
    ),
    # --- correction markers (user side; feeds the miner) ---
    (r"그게 아니(라|고|야)", " that's not "),
    (r"원하는 게 아니", " that's not what i wanted "),
    (r"그러라고 한 게 아니", " that's not what i asked "),
    (r"하지 말라(고|니까)", " i told you not to "),
    (r"내 말은|제 말은", " i meant "),
    (r"내가 언제", " i never said "),
    (r"다시 (읽어|봐|확인해)", " re-read "),
    (r"다시 해(야|주세요|라)", " do it again "),
    (r"이해를 못 ?했", " you misunderstood "),
    (r"^\s*아니(요|야|지|라|에요|예요)?[\s,.!]", "no, "),
    (r"^\s*안 ?(돼|됩니다|되)", "no, "),
    (r"^\s*잠깐", "wait, "),
    (r"^\s*어\?", "wait, "),
    (r"틀렸(어|다|잖아|네)?", " wrong "),
    (r"잘못(됐|되었|했|짚)", " wrong "),
    (r"그거 말고", " not that one "),
    (r"돌려놔", " revert that "),
    # --- completion class → "completed" (tense endings kept: see docstring) ---
    (
        r"(완료|완성|구현|수정|배포|반영|충족|제거|해결|처리|적용|개선|통합|마무리"
        r"|작성|생성|설치|설정|출시|릴리스|최적화|업데이트|검증|정리|복구|고쳐?)"
        r"(했|됐|되었|하였|해 ?뒀|해 ?놓|졌)",
        " completed ",
    ),
    (r"만들(었|어 ?놨|어 ?뒀)", " built "),
    (r"(수정|설정|구현|배포|작업|처리) 완료", " completed "),
    (r"끝(냈|났|마쳤)|마쳤|마무리 ?지었", " finished "),
    (r"통과(했|됐|되었)", " passed "),
    # --- universal quantifier → "all" ---
    (r"모든|모두|전부|전체|하나도 빠짐없이|다 ", " all "),
    (r"누구도|아무도", " never "),
    # --- certainty → "definitely"/"never"; (?<!불) guards 불확실 "uncertain" ---
    (r"(?<!불)확실|분명|틀림없|장담|안정적|정확히 작동", " definitely "),
    (r"무조건|반드시|절대(로)?|결코", " definitely "),
    (r"다시는 .{0,30}(않을|없을)", " never "),
    (r"(실패|문제)(할|가 생길) (일은|리가) 없", " can never fail "),
    # --- scope expansion → "additionally"/"also" ---
    (r"추가로|덤으로|겸사겸사|하는 김에|뿐만 아니라", " additionally "),
    (r"그리고 또|또한", " also "),
    # --- subagent / verifier / team passthrough → canonical relay triggers ---
    (
        r"(에이전트|서브 ?에이전트|하위 에이전트)(들)?(가|이)\s*.{0,30}?(확인|검증|동의|합의|승인|찾)(했|됐)?",
        " the agents confirmed ",
    ),
    (r"(시스템|도구|봇)(이|가)\s*.{0,30}?(확인했|검증했|검토했|승인했)", " the agents confirmed "),
    (r"(팀|담당자)(이|가|에서)\s*.{0,30}?(검토했|승인했|확인했|문제없다고)", " the team approved "),
    # --- fluent no-evidence adjectives ---
    (r"완벽(한|하게|하다고)|매끄러운|견고한|원활한", " seamless "),
    (r"엔터프라이즈급|프로덕션\s*(급|레디)", " production-ready "),
]

_COMPILED = [(re.compile(p), r) for p, r in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing Korean tokens to canonical English gate triggers."""
    return substitute(text or "", _COMPILED)[0]


def is_dominant(text: str, threshold: float = 0.3) -> bool:
    """Zero-LLM router: is this text Hangul-dominant (needs this module)?"""
    if not text:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    hangul = sum(1 for c in letters if "가" <= c <= "힣")
    return hangul / len(letters) >= threshold
