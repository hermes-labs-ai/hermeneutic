"""Experimental Korean trigger mapping, ported from the Korean prototype.

One English gate; local vocabulary maps to its canonical triggers, without
translating the draft. Digits, punctuation and unmapped text remain intact.
Past-tense completion and planned work deliberately map differently.
See ``evals/languages/README.md`` for synthetic validation and limitations.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,30}?"

_MAP: list[tuple[str, str]] = [
    (
        "(?:안|못)\\s*(?:확인|검증|동의|합의|승인|찾)(?:했|됐)?|(?:확인|검증|동의|합의|승인|찾)(?:하|되)?지\\s*(?:않|못)",
        " unconfirmed ",
    ),
    ("(?:확인|검증|동의|합의|승인|찾)할\\s*수\\s*없", " unconfirmed "),
    ("(?:확인|검증|동의|합의|승인|찾)\\s*(?:못|안)\\s*(?:했|하)", " unconfirmed "),
    ("(?:확실|분명|안정적)(?:하|이)?지(?:는)?\\s*(?:않|못)|정확히\\s*작동하지\\s*(?:않|못)", " uncertain "),
    ("(?<=[가-힣])(\\d+(?:\\.\\d+)?)", " \\1"),
    ("(했|됐|되었|하였)지만", "\\1 but "),
    ("하지만|그러나|그런데|지만", " but "),
    ("아직|나머지|남아|남았|진행 중|작업 중|테스트 중", " remaining "),
    ("(\\d+(?:\\.\\d+)?)\\s*(개의|개|건|번|명|줄|가지|차례)", "\\1 "),
    (
        "(patch|fix(?:ed)?|merge[d]?|deploy(?:ed)?|refactoring|release[d]?|"
        "ship(?:ped)?)\\s*(했|됐|되었|돼 ?있|해 ?놨|해 ?뒀)",
        " completed ",
    ),
    ("그게 아니(라|고|야)", " that's not "),
    ("원하는 게 아니", " that's not what i wanted "),
    ("그러라고 한 게 아니", " that's not what i asked "),
    ("하지 말라(고|니까)", " i told you not to "),
    ("내 말은|제 말은", " i meant "),
    ("내가 언제", " i never said "),
    ("다시 (읽어|봐|확인해)", " re-read "),
    ("다시 해(야|주세요|라)", " do it again "),
    ("이해를 못 ?했", " you misunderstood "),
    ("^\\s*아니(요|야|지|라|에요|예요)?[\\s,.!]", "no, "),
    ("^\\s*안 ?(돼|됩니다|되)", "no, "),
    ("^\\s*잠깐", "wait, "),
    ("^\\s*어\\?", "wait, "),
    ("틀렸(어|다|잖아|네)?", " wrong "),
    ("잘못(됐|되었|했|짚)", " wrong "),
    ("그거 말고", " not that one "),
    ("돌려놔", " revert that "),
    (
        "(완료|완성|구현|수정|배포|반영|충족|제거|해결|처리|적용|개선|통합|마무리|작성|생성|설치|설정|출시|릴리스|최적화|업데이트|검증|"
        "정리|복구|고쳐?)(했|됐|되었|하였|해 ?뒀|해 ?놓|졌)",
        " completed ",
    ),
    ("만들(었|어 ?놨|어 ?뒀)", " built "),
    ("(수정|설정|구현|배포|작업|처리) 완료", " completed "),
    ("끝(냈|났|마쳤)|마쳤|마무리 ?지었", " finished "),
    ("통과(했|됐|되었)", " passed "),
    ("모든|모두|전부|전체|하나도 빠짐없이|다 ", " all "),
    ("누구도|아무도", " never "),
    ("(?<!불)확실|분명|틀림없|장담|안정적|정확히 작동", " definitely "),
    ("무조건|반드시|절대(로)?|결코", " definitely "),
    ("다시는 .{0,30}(않을|없을)", " never "),
    ("(실패|문제)(할|가 생길) (일은|리가) 없", " can never fail "),
    ("추가로|덤으로|겸사겸사|하는 김에|뿐만 아니라", " additionally "),
    ("그리고 또|또한", " also "),
    (
        "(에이전트|서브 ?에이전트|하위 에이전트)(들)?(가|이)\\s*"
        + _RELAY_GAP
        + "(확인|검증|동의|합의|승인|찾)(했|됐)?",
        " the agents confirmed ",
    ),
    ("(시스템|도구|봇)(이|가)\\s*" + _RELAY_GAP + "(확인했|검증했|검토했|승인했)", " the agents confirmed "),
    ("(팀|담당자)(이|가|에서)\\s*" + _RELAY_GAP + "(검토했|승인했|확인했|문제없다고)", " the team approved "),
    ("완벽(한|하게|하다고)|매끄러운|견고한|원활한", " seamless "),
    ("엔터프라이즈급|프로덕션\\s*(급|레디)", " production-ready "),
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
