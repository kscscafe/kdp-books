# KDP キャラクター本 制作ガイド
作成日：2026-05-15

---

## 1. 完成形の仕様

| 項目 | 仕様 |
|---|---|
| 入稿形式 | EPUB3 Fixed Layout（pre-paginated） |
| ビューポート | 1749 × 2481 px（A5 @ 300dpi） |
| フォント | 埋め込み済みTTF/OTFのみ（emb=yes必須） |
| 表紙画像 | JPEG、幅1000px以上、縦長（比率1.6推奨） |
| 言語メタデータ | ja |

---

## 2. 使用フォント

| 変数 | フォント | 用途 |
|---|---|---|
| F_JA_M | NotoSerifJP | 日本語見出し |
| F_JA | NotoSansJP | 日本語本文 |
| F_CH | NotoSansSC | 中国語フレーズ・簡体字 |
| F_PY | DejaVuSans | ピンイン |

禁止：HeiseiMin-W3 / HeiseiKakuGo-W5 / STSong-Light（CIDフォント→KDP文字化け）

---

## 3. 事前準備（ハックと一緒に）

1. キャラクター設定を決める（名前・出身・設定）
2. 本のテーマを決める（例：仕事・旅行・恋愛フレーズ等）
3. フレーズ50個を決める
4. カラーテーマ12色を決める

---

## 4. 制作工程

### Step 1: 新キャラ用ディレクトリ作成
```
cp -r /Users/ksugizaki/Documents/60_KDP/book_template/ /Users/ksugizaki/Documents/60_KDP/Wei_01/
```

### Step 2: data/phrases.csv を差し替え
50フレーズを以下の形式で記入：
```
No, 中国語, ピンイン, 日本語訳, キャラのひとこと, 補足ピンイン
```

### Step 3: config/book_config.py を編集
- キャラ名・著者名
- カラーテーマ12色
- 章タイトル・章の説明文
- App Store URL / QRコード用URL
- キャラクター紹介文（はじめに・おわりに）

### Step 4: assets/ を差し替え
- cover.png（表紙画像）
- キャラクター画像

### Step 5: ビルド・検証
```
python3 build.py
pdffonts output/*.pdf  # 全行 emb=yes を確認
```

### Step 6: FXL EPUB生成
```
mkdir -p fxl_pages
pdftoppm -r 300 -png output/*.pdf fxl_pages/page
# FXL EPUB生成スクリプト実行
# → output/*.epub を生成
```

### Step 7: EPUBバリデーション
```
java -jar /usr/local/Cellar/epubcheck/$(ls /usr/local/Cellar/epubcheck)/libexec/epubcheck.jar output/*.epub
# → エラーゼロを確認
```

### Step 8: 目視確認
output/のPDFを開いて確認：
- 表紙・はじめに・目次
- 各フレーズページのレイアウト
- フレーズ一覧・おわりに・QRコード
- ページ番号整合

### Step 9: KDPアップロード
1. KDPダッシュボード →「本のコンテンツを編集」
2. 表紙：cover.jpg をアップロード
3. 原稿：*.epub をアップロード
4. プレビューアーで全ページ確認
5. 審査提出

---

## 5. トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| KDPプレビューで文字化け | フォント未埋め込み | pdffontsで確認、Noto系に差し替え |
| KDPプレビューでレイアウト崩れ | PDF直接入稿 | FXL EPUBに変換 |
| epubcheck実行エラー | Javaパスバグ | java -jarで直接実行 |
| 表紙サイズ不足 | 解像度不足 | 元PNGから再書き出し |
