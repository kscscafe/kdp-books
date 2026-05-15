# 林小雨「気持ちを伝える中国語フレーズ50」PDF生成プロジェクト

## 概要

KDP（Kindle Direct Publishing）向けA5サイズのPDF書籍を生成するプロジェクト。
著者キャラクター・林小雨（リン）が中国語フレーズ50個を解説する日本語書籍。

## クイックスタート

```bash
# 初回のみ
./setup.sh

# PDF生成
python3 build_phrases.py

# 生成物確認
open output/lin_phrases.pdf
```

## ファイル構成

```
lin-phrases/
├── CLAUDE.md           ← このファイル（Claude Codeが自動で読む）
├── README.md
├── requirements.txt
├── setup.sh            ← 初回セットアップ（フォント検出・依存関係）
├── build_phrases.py    ← メインスクリプト
├── assets/
│   └── cover.png       ← 表紙画像（要配置）
└── output/             ← 生成PDF出力先（gitignore済み）
```

## フォント構成（重要）

### 使用フォント

| 変数 | フォント | 用途 | 取得方法 |
|------|----------|------|----------|
| F_CH | STSong-Light (CID) | 中国語フレーズ表示 | reportlab内蔵 |
| F_JA | HeiseiKakuGo-W5 (CID) | 日本語本文・漢字 | reportlab内蔵 |
| F_JA_M | HeiseiMin-W3 (CID) | 日本語見出し | reportlab内蔵 |
| F_PY | DejaVuSans (TTF) | ピンイン声調記号 | システムフォント |

### フォントの鉄則

- **CJK漢字（U+4E00〜U+9FFF）は全てF_JA**で描画する
  → F_CHを使うと日本語の漢字が中国語書体になる
- **"PHRASE"等のASCII文字列はF_PY**を使う
  → F_JAで描画すると全角/半角が混在して見える
- **コメント本文（リンのひとこと）は`draw_line_mixed()`**を使う
  → 1文字ずつフォントを自動判定して描画する

### font_for_char の判定ロジック

```
ひらがな・カタカナ (U+3040-30FF) → F_JA
CJK記号「」 (U+3000-303F)       → F_JA
全角文字（） (U+FF00-FFEF)       → F_JA
漢字 (U+4E00-9FFF)              → F_JA  ← F_CHにしてはいけない
ラテン拡張 ā á ǎ (U+0100-024F)  → F_PY  ← 声調記号
ASCII (U+0020-007E)             → F_PY
```

## ページ構成

| ページ | 内容 |
|--------|------|
| 1 | 表紙（assets/cover.png） |
| 2 | はじめに |
| 3 | 目次 |
| 4 | 声調・発音ガイド |
| 5, 11, 22, 33, 44 | 各章扉ページ |
| 6–10 | PHRASE 01–05（第1章） |
| 12–21 | PHRASE 06–15（第2章） |
| 23–32 | PHRASE 16–25（第3章） |
| 34–43 | PHRASE 26–35（第4章） |
| 45–59 | PHRASE 36–50（第5章） |
| 60〜 | フレーズ一覧（動的ページ数） |
| 最終 | おわりに |

## フレーズページのレイアウト

```
┌──────────────────────────────────┐ y=H
│ PHRASE 01 (F_PY)  ｜ 章タイトル  │ ← 34pt ストリップ（薄ピンク）
│                          ０１    │ ← 装飾番号（背景・薄色）
│                                  │
│        你好！                     │ ← F_CH, 24-38pt（文字数で自動調整）
│        Nǐ hǎo!                   │ ← F_PY, 13pt, ローズ色
│   ◆──────────────◆              │ ← 区切り線
│        こんにちは！               │ ← F_JA_M, 15pt
├──────────────────────────────────┤
│ リンのひとこと ●                  │ ← ピンクヘッダーバー
│                                  │
│ コメント本文...                   │ ← draw_line_mixed(), 11pt
│ （高さはコメント行数で動的計算）   │   ボックス高さ = 行数×17 + 50
├──────────────────────────────────┤ y=MB
│              [ページ番号]         │
└──────────────────────────────────┘
```

## フレーズ一覧のレイアウト（バグが出やすい部分）

```python
# 列x座標
X_NO = ML           # No.列
X_ZH = ML + 20      # 中国語
X_PY = ML + 108     # ピンイン
X_JA = ML + 224     # 日本語訳

# 行高さ
ROW_H1 = 19   # 1行の場合
ROW_H2 = 32   # 2行の場合（ピンイン・日本語訳が長い場合）
LINE2_OFFSET = 13  # 2行目のyオフセット

# 行背景矩形（PDFはy上向き座標なので注意）
# ✓ 正: c.rect(ML-2, y - row_h + 4, CW+4, row_h)
# ✗ 誤: c.rect(ML-2, y - row_h + ROW_H1, ...)  ← 2行行でズレる
```

ピンイン・日本語訳は**省略禁止、最大2行で折り返し**。

## 混合文字列の描画（「PHRASE 01」「HanYuAI 公式...」など）

ASCII + 日本語が混在する文字列は**必ず分割して描画**する。

```python
# 例: "HanYuAI公式キャラクターブック"
w1 = stringWidth('HanYuAI', F_PY, 9)
c.setFont(F_PY, 9); c.drawString(x, y, 'HanYuAI')
c.setFont(F_JA, 9); c.drawString(x + w1 + 4, y, '公式キャラクターブック')

# 例: 章扉の「PHRASE 01 - 05  （５フレーズ）」
c.setFont(F_PY, 10); c.drawString(x, y, 'PHRASE 01 - 05')
c.setFont(F_JA, 10); c.drawString(x + w, y, '  （５フレーズ）')
# ※ 数字は to_fullwidth(n) で全角変換してから渡す
```

## 既知の残課題

- [ ] コメント内の簡体字（吗・爱・开など）がF_JAにないため表示されない可能性
- [ ] フレーズ一覧の行レイアウト精度（ユーザー確認中）
- [ ] その他ユーザーから指摘される修正事項

## よく使うコマンド

```bash
make build    # PDF生成
make check    # フォント確認
make clean    # outputディレクトリをクリア
make open     # 生成したPDFを開く
```
