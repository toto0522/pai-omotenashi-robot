#!/usr/bin/env python3
"""学習済み文章分類AIから既存の gestures_v2.py を呼び出す。

起動例:
  python3 robot_ai.py "元気に挨拶して"             # 分類のみ（ロボットは動かない）
  python3 robot_ai.py "丁寧にお辞儀して" --execute  # Gazeboのロボットを動かす
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from train_ai import classify

BASE = Path(__file__).resolve().parent
DESCRIPTIONS = {"greeting": "元気な挨拶", "polite": "丁寧なお辞儀", "rest": "静かな待機", "unknown": "保留（対象外または曖昧）"}


def main():
    ap = argparse.ArgumentParser(description="文章分類AI × Gazeboロボット")
    ap.add_argument("text", nargs="?", help="日本語の指示文。省略すると入力待ち")
    ap.add_argument("--execute", action="store_true", help="分類結果に合わせGazeboを動かす")
    args = ap.parse_args()
    model_file = BASE / "model.json"
    if not model_file.exists():
        print("モデルがありません。先に python3 train_ai.py を実行してください。")
        sys.exit(1)
    model = json.loads(model_file.read_text(encoding="utf-8"))
    gesture = BASE / "gestures_v2.py"
    if args.execute and not gesture.exists():
        print("gestures_v2.py が同じフォルダに見つかりません。")
        sys.exit(1)

    def process(text):
        result = classify(text, model)
        label = result["label"]
        print(f"\n入力: {text}")
        print("類似度スコア（確率ではありません）: " + ", ".join(
            f"{k}={v:.3f}" for k, v in result["scores"].items()))
        print(f"AI判定: {label}（{DESCRIPTIONS[label]}）")
        if label == "unknown":
            print("判断が曖昧なので、安全のためロボットには指令しません。")
            return
        if not args.execute:
            print("※確認モードです。実際に動かす場合は --execute を付けてください。")
            return
        print(f"ROS 2の動作プログラムを起動: {gesture.name} {label}", flush=True)
        # shell=Trueは使わず、ラベルは内部の固定値からのみ指定
        subprocess.run([sys.executable, str(gesture), label], cwd=str(BASE), check=True)

    if args.text:
        process(args.text)
    else:
        print("自然言語を入力してください（終了は空Enter）。")
        while True:
            try:
                text = input("指示> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                break
            process(text)


if __name__ == "__main__":
    main()
