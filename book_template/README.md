# book_template — キャラクター中国語フレーズ集 生成エンジン

KDP 向け A5 中国語フレーズ集 PDF を、データ + 設定 + アセットの差し替えで量産するためのテンプレート。
オリジナルは `../Lin_01/`（林小雨 の本）。エンジン部分のみ抽出してデータ外出し化済み。

## ディレクトリ構成

```
book_template/
├── build.py                  ← エンジン本体（触らなくてOK）
├── data/
│   └── phrases.csv           ← フレーズ50件のデータ
├── config/
│   └── book_config.py        ← キャラ・タイトル・色・本文ナラティブ
├── assets/
│   ├── cover.png             ← 表紙画像（A5縦、推奨2000×2800以上）
│   └── qr_appstore.png       ← QR画像（おわりに用、任意）
├── fonts/
│   └── STHeitiSC-Medium-subset.ttf   ← 簡体字フォールバック（共通、触らなくてOK）
├── output/                   ← phrases.pdf と page_map.json が生成される
└── README.md
```

## 新キャラ本を作る最短手順

### 1. ディレクトリをコピー

```bash
cp -r book_template/ Mei_01/    # 例：キャラ名「Mei」
cd Mei_01
```

### 2. `data/phrases.csv` を編集

50フレーズを CSV で記述。列は以下：

| no | chapter | chinese | pinyin | japanese | comment | supplemental_pinyin |
|---|---|---|---|---|---|---|
| 1 | 1 | 你好！ | Nǐ hǎo! | こんにちは！ | キャラのコメント本文 | （予約・空でOK） |

- `no`: 1〜50 通し番号
- `chapter`: 1〜5（章番号、`book_config.py` の `CHAPTERS_META` と一致させる）
- `comment`: リンのひとこと（キャラのコメント本文）

### 3. `config/book_config.py` を編集

- `CHARACTER_NAME` / `CHARACTER_NICKNAME`：著者名と短名
- `BOOK_TITLE`：書名
- `APP_NAME` / `APP_STORE_URL`：宣伝するアプリ情報
- `CHAPTERS_META`：5つの章タイトルと引用
- `INTRO_TEXT` / `AFTERWORD_TEXT`：はじめに・おわりに本文（リスト、空文字列＝改行）
- `AFTERWORD_CHINESE_SENDOFF`：おわりに末尾の中国語別れ文
- `QR_CAPTION`：QR下のキャプション
- `COLORS`：12色のテーマカラー（HEX）
- `OUTPUT_FILENAME`：出力PDFファイル名

### 4. `assets/cover.png` と `assets/qr_appstore.png` を差し替え

表紙は A5 縦比率の高解像度 PNG。QR は以下で生成：

```bash
pip3 install 'qrcode[pil]'
python3 -c "
import qrcode
qr = qrcode.make('https://apps.apple.com/...')
qr.save('assets/qr_appstore.png')
"
```

### 5. ビルド

```bash
python3 build.py
open output/phrases.pdf  # macOS
```

64ページの A5 PDF が `output/phrases.pdf` に生成される。

## 設計のポイント（次に拡張するときの備忘）

- **フォント振り分け**：日本語は HeiseiKakuGo-W5（CID, 非埋め込み）、簡体字は STHeiti subset（埋め込み）、ピンイン声調符号は DejaVuSans（埋め込み）、メイン中国語表示は STSong-Light（CID）
- **`（pinyin）` 検出**：コメント本文中、`（...）` の直前 CJK は中国語引用扱いで STHeiti レンダリング
- **行頭/行末禁則**：`。、！？）」` は行頭に置かない、`（「『【〔` は行末に置かない
- **単語単位 wrap**：ピンイン単語と中国語引用ランは途中改行しない
- **ページ番号**：`_split_index_rows()` でフレーズ一覧の実ページ数を予測してから TOC を描画

## 検証

`../Lin_01/validate_pdf.py` を流用すれば、64ページ確認・全フレーズ存在確認・ピンイン桁混入チェック・TOC整合チェックが走る。
