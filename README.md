# AIおもてなしロボット

東京大学 松尾・岩澤研究室「Physical AI 応用編1」最終課題のために制作した、自然言語に応じてロボットの振る舞いを変えるGazeboシミュレーションです。

## 概要

日本語の指示文を小規模な文章分類モデルで分析し、`greeting`（元気な挨拶）、`polite`（丁寧なお辞儀）、`rest`（静かな待機）のいずれかを選択します。判断が曖昧な場合は`unknown`として実行を保留します。動作候補がある場合も人間の承認後にのみROS 2経由でCRANE+ V2を動かします。

```text
日本語の指示文 → 文章分類AI → 保守的な判定（ルール＋スコア） → 人間の承認 → ROS 2 → Gazebo / CRANE+ V2
```

## 使用技術

- Python 3（文章分類部分は標準ライブラリで実装）
- 文字1〜3-gramのTF-IDFとクラス中心ベクトルによる教師あり分類
- ROS 2 Humble / `rclpy` / `trajectory_msgs`
- Gazebo / CRANE+ V2

## 主なファイル

| ファイル | 役割 |
| --- | --- |
| `train_ai.py` | 教師データからモデルを学習し、テストデータを評価する |
| `train.csv` / `test.csv` | 文章分類の学習・テスト用例文 |
| `robot_ai.py` | 基本の文章分類と動作選択 |
| `safety_guard.py` | 否定・説明要求・曖昧さなどを確認して保留する処理 |
| `robot_ai_safe.py` | 判定と承認を経て動作プログラムを呼び出す |
| `safety_eval.py` / `safety_challenge.csv` | 安全確認処理の診断用評価 |
| `gestures_v2.py` | 3種類の関節・グリッパー動作 |

## 実行方法

### 1. AIモデルを学習・評価

```bash
python3 train_ai.py
python3 safety_eval.py
```

これにより`model.json`が生成されます。分類だけならROS 2やGazeboは不要です。

```bash
python3 robot_ai_safe.py "元気に挨拶して！"
python3 robot_ai_safe.py "昨日の天気を教えて"
```

### 2. Gazebo上でロボットを動かす

ROS 2 Humble、CRANE+ V2関連パッケージ、アーム・グリッパーの`joint_trajectory_controller`が動作している環境を準備します。起動手順は環境によって異なります。本制作では講義のDocker環境を使用しました。

操作用のteleopノードを停止したうえで、ROS 2環境を読み込みます。

```bash
source /opt/ros/humble/setup.bash
source ~/pai_ws/install/setup.bash
python3 robot_ai_safe.py "元気に挨拶して！" --execute
```

候補が認識されると確認プロンプトが表示されます。`y`を入力した場合だけロボットを動かします。以下も例です。

```bash
python3 robot_ai_safe.py "初対面なので礼儀正しく迎えて" --execute
python3 robot_ai_safe.py "しばらく静かに待機して" --execute
python3 robot_ai_safe.py "昨日の天気を教えて" --execute
```

## 評価・限界

- 学習用例文180文から分類器を構築。初期の42文テストでは40文正解（95.2%）。
- 保守的な確認処理を加えた開発時の診断用例文では誤反応候補を減らせましたが、実行できる指示を保留する場合もあります。
- 診断用例文は開発時に確認したもので、一般的な未知入力に対する性能や安全性を保証しません。
- 分類結果の類似度は**確率ではありません**。
- 関節軌道は衝突回避や実機安全性を保証しません。**Gazeboでの教育・実演用です。**

## 工夫した点

1. AIの行動選択とROS 2による関節制御を分離したこと。
2. `greeting`、`polite`、`rest`を異なる身体表現として設計したこと。
3. 対象外・曖昧な指示を保留し、実行時には人間の承認を必要としたこと。
4. 初期の関節角度をGazebo上で観察し、動作を改善したこと。
