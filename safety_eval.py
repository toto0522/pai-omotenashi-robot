#!/usr/bin/env python3
"""Compare base classifier against guarded decision on two diagnostic CSVs."""
import csv
import json
from pathlib import Path
from train_ai import classify
from safety_guard import guarded_classify

BASE = Path(__file__).resolve().parent


def evaluate(path, model):
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    count_base = count_guard = 0
    wrong_motion_base = wrong_motion_guard = 0
    missed_guard = 0
    n_unknown = sum(r['label'] == 'unknown' for r in rows)
    n_eligible = len(rows) - n_unknown
    diffs = []
    for row in rows:
        text, expected = row['text'], row['label']
        base = classify(text, model)['label']
        guarded = guarded_classify(text, model)
        final = guarded['label']
        count_base += base == expected
        count_guard += final == expected
        if expected == 'unknown':
            wrong_motion_base += base != 'unknown'
            wrong_motion_guard += final != 'unknown'
        elif final != expected:
            missed_guard += 1
        if base != final or final != expected:
            diffs.append((text, expected, base, final, guarded['reason']))
    print(f'\n[{path.name}] {len(rows)}文 （行動指示{n_eligible}文 / 対象外{n_unknown}文）')
    print(f'  元のAI: {count_base}/{len(rows)} 正解')
    print(f'  安全確認後: {count_guard}/{len(rows)} 正解')
    print(f'  対象外なのに動作候補になった数: {wrong_motion_base} → {wrong_motion_guard}')
    print(f'  正しい行動指示でも保留・誤判定になった数: {missed_guard}')
    print('  変更・誤判定例（最大20件）:')
    for text, expected, base, final, reason in diffs[:20]:
        print(f'    {text}: 正解={expected} 一次={base} 安全後={final} [{reason}]')


def main():
    model_file = BASE / 'model.json'
    if not model_file.exists():
        print('model.json が必要です。先に train_ai.py で学習してください。')
        return
    model = json.loads(model_file.read_text(encoding='utf-8'))
    for fname in ('test.csv', 'safety_challenge.csv'):
        file = BASE / fname
        if file.exists():
            evaluate(file, model)
        else:
            print(f'{fname} が見つかりません。スキップします。')
    print('\n注意：これらは作成者が用意した診断用例文であり、安全性の証明ではありません。')


if __name__ == '__main__':
    main()
