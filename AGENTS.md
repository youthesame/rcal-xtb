## 1. プロジェクトの目的
このプロジェクトは、外部プログラムとして **xTB** を Python から実行し、得られた各状態のエネルギーから **再配列エネルギー** を計算することを目的とする。
対象は以下の2種類。
- **P型（hole, cation）再配列エネルギー**
- **N型（electron, anion）再配列エネルギー**

## 2. 必須運用ルール
1. Python環境は必ず **uv** を使う。
2. xTBを使う前に必ず `module load xtb` を実行し、有効化確認を行う。
3. すべての実装作業は、計画時点と完了時点の記録を `docs/YYYY-MM-DD_<plan-log-title>.md` に残す。
4. 計画立案とエラー原因調査ではWeb検索を使い、参照URLをログに残す。
5. Pythonコードはできるだけシンプルに保ち、報告前に簡素化余地を再点検する。
6. ディレクトリ/ファイルを追加・削除・移動した場合は、同一作業内で `AGENTS.md` の「6.1 ディレクトリ構成」を更新する。

## 3. 再配列エネルギーの定義
記号:
- `R0`: 中性最適化構造
- `R+`: カチオン最適化構造
- `R-`: アニオン最適化構造
- `E0(Rx)`: 構造 `Rx` での中性エネルギー
- `E+(Rx)`: 構造 `Rx` でのカチオンエネルギー
- `E-(Rx)`: 構造 `Rx` でのアニオンエネルギー

P型（hole）再配列エネルギー:
- `lambda_p = [E+(R0) - E+(R+)] + [E0(R+) - E0(R0)]`

N型（electron）再配列エネルギー:
- `lambda_n = [E-(R0) - E-(R-)] + [E0(R-) - E0(R0)]`

注記:
- xTBの出力エネルギーは通常Eh（Hartree）なので、必要に応じてeVへ変換する。

## 4. xTB実行ポリシー
- 推奨: GFN2-xTB（`--gfn 2`）
- 電荷・スピンは必ず明示する（例）:
  - neutral: `--chrg 0 --uhf 0`
  - cation radical: `--chrg 1 --uhf 1`
  - anion radical: `--chrg -1 --uhf 1`
- 構造最適化:
  - `xtb input.xyz --opt --gfn 2 --chrg <q> --uhf <u>`
- single-point:
  - `xtb input.xyz --gfn 2 --chrg <q> --uhf <u>`
- エネルギー抽出:
  - xTB標準出力の `TOTAL ENERGY`（または`total energy`）をパースする。

## 5. uv実行ポリシー
- 依存同期: `uv sync`
- 実行: `uv run <command>`
- 例:
  - `uv run python -m rcal_xtb.cli --help`

## 6. ディレクトリ構成更新ルール
- この章は固定の構成例を置く場所ではなく、変更履歴を管理する場所とする。
- 追加/削除/移動のたびに、「6.1 ディレクトリ構成」を更新する。

### 6.1 ディレクトリ構成
```text
.
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── AGENTS.md
├── LICENSE
├── README.md
├── docs/
│   └── YYYY-MM-DD_*.md
├── mols/
│   └── *.xyz
├── output/
│   ├── <molecule>/<generated-workdir>/...
│   ├── gfn2/<molecule>/<generated-workdir>/...
│   └── gxtb/<molecule>/<generated-workdir>/...
├── pyproject.toml
├── results/
│   ├── gfn2/
│   │   └── *_p.csv
│   ├── gxtb/
│   │   └── *_p.csv, AN3_n.csv
│   ├── _tmp_reorg_runs/
│   │   └── *_p.csv, AN3_n.csv
│   └── ... .csv, benchmark_gfn2_gxtb.csv
├── src/
│   └── rcal_xtb/
│       ├── __init__.py
│       ├── cli.py
│       ├── energy_parser.py
│       ├── reorg_n.py
│       ├── reorg_p.py
│       └── xtb_runner.py
├── tests/
│   └── test_*.py
└── uv.lock
```

## 7. 標準ワークフロー（毎回必須）
1. `docs/YYYY-MM-DD_<plan-log-title>.md` を作成し、目的・前提・調査計画を記録する。
2. 必要なWeb調査を行い、URLと採用理由を記録する。
3. 実行環境を準備する（`uv sync` → `module load xtb` → `which xtb`/`xtb --version`）。
4. Python から xTB を実行し、必要な各エネルギーを取得する。
5. `lambda_p` と `lambda_n` を計算する。
6. テスト/検証（最低限: 計算式・パーサ・異常系）を実施する。
7. ログに実行コマンド、結果、エラー原因、対処、再現手順を追記する。
8. ディレクトリ/ファイルの追加・削除・移動がある場合は、`AGENTS.md` の「6.1 ディレクトリ構成」を更新する。
9. ユーザーへ報告し、必要なら簡素化修正を行う。

## Notifications
When you complete a task, or before you request approval, send me a push notification in 日本語:

curl -s -X POST https://api.getmoshi.app/api/webhook \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$MOSHI_TOKEN\",\"title\":\"Status\",\"message\":\"Brief summary\"}"
