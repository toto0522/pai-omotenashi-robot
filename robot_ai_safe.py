#!/usr/bin/env python3
"""Natural language classifier → conservative gate → human consent → Gazebo.

Default is inference only. Even with --execute, a real TTY confirmation is
required. Only the three named gestures may run; unknown never runs.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from safety_guard import guarded_classify

BASE = Path(__file__).resolve().parent
DESCRIPTIONS = {
    'greeting': '元気な挨拶',
    'polite': '丁寧なお辞儀',
    'rest': '静かな待機',
    'unknown': '保留（対象外または曖昧）',
}


def process(text, model, execute=False):
    result = guarded_classify(text, model)
    label = result['label']
    print(f'\n入力: {text}')
    print('AIの一次判定: ' + result['model_label'])
    print('類似度（確率ではありません）: ' + ', '.join(
        f'{k}={v:.3f}' for k, v in result['scores'].items()))
    print(f'安全判定: {label}（{DESCRIPTIONS[label]}）')
    print('理由: ' + result['reason'])

    if label == 'unknown':
        print('保留しました。ロボットには指令を送りません。')
        return False
    if not execute:
        print('確認モードです。実行する場合は --execute を付けてください。')
        return False

    if not sys.stdin.isatty():
        print('実行を拒否しました。対話できるターミナルで承認してください。')
        return False
    try:
        answer = input(f'{label} をロボットに実行しますか？ [y/N]: ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        print('\nキャンセルしました。')
        return False
    if answer not in ('y', 'yes'):
        print('キャンセルしました。')
        return False

    script = BASE / 'gestures_v2.py'
    if not script.is_file():
        print('gestures_v2.py が同じフォルダにありません。')
        return False
    print(f'実行開始: {script.name} {label}', flush=True)
    # The action label can only be one of these internal fixed values.
    subprocess.run([sys.executable, str(script), label], cwd=str(BASE), check=True)
    return True


def main():
    parser = argparse.ArgumentParser(description='自然言語AI + 安全確認 + ROS 2制御')
    parser.add_argument('text', nargs='?', help='日本語の指示（省略すると対話モード）')
    parser.add_argument('--execute', action='store_true', help='実行候補に人間が承認すれば動かす')
    args = parser.parse_args()
    model_file = BASE / 'model.json'
    if not model_file.is_file():
        parser.error('model.json がありません。先に python3 train_ai.py を実行してください。')
    model = json.loads(model_file.read_text(encoding='utf-8'))
    if args.text is not None:
        process(args.text, model, args.execute)
    else:
        print('指示文を入力してください。終了は空Enter／Ctrl+C。')
        while True:
            try:
                text = input('指示> ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                break
            process(text, model, args.execute)


if __name__ == '__main__':
    main()
