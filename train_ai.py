#!/usr/bin/env python3
"""自然言語 → 3種類のロボット動作を学習する最小の教師あり分類器。

外部ライブラリ不要。文字1〜3gramのTF-IDFとクラス中心ベクトルを使う。
学習データを読み、モデルを保存し、未学習のテストデータで評価する。
"""
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
LABELS = ("greeting", "polite", "rest", "unknown")
MODEL = BASE / "model.json"


def normalize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def ngrams(text):
    s = normalize(text)
    return Counter(s[i:i+n] for n in (1, 2, 3) for i in range(len(s) - n + 1))


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row.get("label") not in LABELS or not row.get("text", "").strip():
            raise ValueError(f"不正なデータ行: {row}")
    return rows


def tfidf(counts, idf):
    vec = {term: (1 + math.log(c)) * idf[term] for term, c in counts.items() if term in idf}
    norm = math.sqrt(sum(v * v for v in vec.values()))
    return {k: v / norm for k, v in vec.items()} if norm else {}


def train(rows):
    docs = [ngrams(r["text"]) for r in rows]
    df = Counter()
    for c in docs:
        df.update(c.keys())
    idf = {term: 1 + math.log((1 + len(rows)) / (1 + freq)) for term, freq in df.items()}
    # 各学習例を単位長にし、同じラベルの文の平均を取る
    centers = {label: Counter() for label in LABELS}
    label_counts = Counter(r["label"] for r in rows)
    for row, doc in zip(rows, docs):
        centers[row["label"]].update(tfidf(doc, idf))
    for label, vec in centers.items():
        n = label_counts[label]
        norm = math.sqrt(sum((v / n)**2 for v in vec.values()))
        centers[label] = {term: (v / n) / norm for term, v in vec.items()} if norm else {}
    return {
        "method": "character_ngram_tfidf_centroid",
        "labels": list(LABELS),
        "n_train": len(rows),
        "train_counts": dict(label_counts),
        "idf": idf,
        "centers": centers,
        # 近似的な判定基準。スコアは確率ではない。
        "min_similarity": 0.16,
        "min_margin": 0.035,
        "min_coverage": 0.20,
    }


def classify(text, model):
    counts = ngrams(text)
    v = tfidf(counts, model["idf"])
    scores = {label: sum(val * model["centers"][label].get(term, 0)
                         for term, val in v.items()) for label in model["labels"]}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best, top = ranked[0]
    margin = top - ranked[1][1]
    # 未知の単語列を無理に既存3クラスへ押し込まない
    coverage = (sum(n for term, n in counts.items() if term in model["idf"])
                / max(1, sum(counts.values())))
    accepted = (top >= model["min_similarity"] and
                margin >= model["min_margin"] and
                coverage >= model["min_coverage"])
    return {
        "label": best if accepted else "unknown",
        "candidate": best,
        "scores": {k: round(v, 3) for k,v in scores.items()},
        "similarity": round(top, 3),
        "margin": round(margin, 3),
        "coverage": round(coverage, 3),
    }


def evaluate(rows, model):
    n_correct = 0
    matrix = {label: Counter() for label in LABELS}
    errors = []
    for row in rows:
        pred = classify(row["text"], model)["label"]
        matrix[row["label"]][pred] += 1
        n_correct += (pred == row["label"])
        if pred != row["label"]:
            errors.append((row["text"], row["label"], pred))
    print(f"テスト結果: {n_correct}/{len(rows)} 正解 ({n_correct/len(rows):.1%})")
    print("正解ラベル → 予測結果 (greeting / polite / rest / unknown)")
    for label in LABELS:
        print(f"  {label:8s}: " + " / ".join(f"{matrix[label][p]:2d}" for p in LABELS))
    if errors:
        print("誤判定・保留の例:")
        for text, target, pred in errors[:20]:
            print(f"  {text!r} 正解:{target} → 予測:{pred}")


def main():
    train_rows = read_rows(BASE / "train.csv")
    test_rows = read_rows(BASE / "test.csv")
    common = {normalize(r["text"]) for r in train_rows} & {normalize(r["text"]) for r in test_rows}
    if common:
        raise ValueError("訓練とテストに重複文があります: " + str(common))
    model = train(train_rows)
    MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"学習完了: {len(train_rows)}文、モデル保存: {MODEL}")
    evaluate(test_rows, model)


if __name__ == "__main__":
    main()
