#!/usr/bin/env python3
"""Small, conservative command gate on top of the lecture project's learned classifier.

This is NOT a certified safety system. It uses model similarities and a few
transparent linguistic rules to defer ambiguous/unsupported commands.
"""
import re
from train_ai import classify, normalize

ACTIONS = frozenset(('greeting', 'polite', 'rest'))
# Margin over the unknown-class similarity. Similarities are NOT probabilities.
MIN_KNOWN_OVER_UNKNOWN = 0.09

EXPLANATION = re.compile(
    r'教えて|解説|説明|意味(?:は|を|が)?|由来|とは(?:何|どう)|'
    r'って何|は何|何(?:ですか|でしょう|なの)|'
    r'(?:(?:どんな|どういう)(?:こと|意味))'
)
NEGATED_GESTURE = re.compile(
    r'(?:挨拶|お辞儀|会釈|一礼|歓迎|お迎え|手を振|頭を下げ).{0,7}'
    r'(?:しないで|しなくて|せずに|しない|は禁止|やめて)'
)
GREET_WORDS = ('挨拶', '歓迎', '手を振', 'お迎え')
BOW_WORDS = ('お辞儀', '一礼', '会釈', '頭を下げ')
COMPOUND_CONNECTORS = ('してから', 'それから', 'その後', '次に', '両方')


def guarded_classify(text, model):
    """Return model result + a conservative final label and reason.

    Initial model label is preserved as `model_label` for honest reporting.
    When uncertain, final label becomes unknown. No side effects occur here.
    """
    result = classify(text, model)
    result['model_label'] = result['label']
    s = normalize(text)
    reasons = []
    if not s:
        reasons.append('空の指示')
    if EXPLANATION.search(s):
        reasons.append('説明・質問の可能性')
    if NEGATED_GESTURE.search(s):
        reasons.append('動作の否定が含まれる')
    if (any(x in s for x in COMPOUND_CONNECTORS)
            and any(x in s for x in GREET_WORDS)
            and any(x in s for x in BOW_WORDS)):
        reasons.append('複数動作を一度に要求')
    if result['label'] not in ACTIONS:
        reasons.append('AIが対象外または曖昧と判定')
    else:
        difference = result['scores'][result['label']] - result['scores']['unknown']
        if difference < MIN_KNOWN_OVER_UNKNOWN:
            reasons.append(f'対象外クラスとの差が小さい ({difference:.3f})')
    result['label'] = 'unknown' if reasons else result['label']
    result['reason'] = ' / '.join(reasons) if reasons else '実行候補（承認待ち）'
    return result
