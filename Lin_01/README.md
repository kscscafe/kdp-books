# 気持ちを伝える中国語フレーズ50

林小雨（リン）による中国語フレーズ集のKDP出版用PDF生成プロジェクト。

## セットアップ

```bash
# 1. リポジトリをクローン後
cd lin-phrases

# 2. 表紙画像を配置
cp /path/to/your/cover.png assets/cover.png

# 3. 初回セットアップ（依存関係 + フォント確認）
bash setup.sh

# 4. PDF生成
python3 build_phrases.py
# または
make build

# 5. 確認（Mac）
make open
```

## 必要な環境

- Python 3.9+
- DejaVu Sans フォント（ピンイン声調記号用）
  - Mac: `brew install --cask font-dejavu`
  - Linux: `sudo apt-get install fonts-dejavu`

## 出力

`output/lin_phrases.pdf` に生成されます（約63ページ）。

## Claude Codeでの作業

このリポジトリには `CLAUDE.md` が含まれており、Claude Codeが自動的に読み込みます。
フォント設計・レイアウトの詳細はそちらを参照してください。
