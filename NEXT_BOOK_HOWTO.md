# 次キャラ本 作成手順

## 事前準備（ハックと一緒に）
1. キャラクター設定を決める
   - 名前・出身・設定
   - 本のテーマ（例：仕事のフレーズ、旅行フレーズ等）
2. フレーズ50個を決める
3. カラーテーマを決める

---

## Claude Codeへの指示

### Step 1: 新キャラ用ディレクトリ作成
cp -r /Users/ksugizaki/Documents/60_KDP/book_template/ /Users/ksugizaki/Documents/60_KDP/Wei_01/

### Step 2: data/phrases.csv を差し替え
50フレーズを以下の形式で記入：
No, 中国語, ピンイン, 日本語訳, リンのひとこと, 補足ピンイン

### Step 3: config/book_config.py を編集
以下を差し替え：
- キャラ名・著者名
- カラーテーマ12色
- 章タイトル・章の説明文
- App Store URL / QRコード用URL
- キャラクター紹介文（はじめに・おわりに）

### Step 4: assets/ を差し替え
- cover.png（表紙画像）
- キャラクター写真

### Step 5: ビルド＆検証
python3 build.py
→ ✅ 検証OK を確認

### Step 6: 目視確認
output/ のPDFを開いて確認：
- 表紙・はじめに・目次
- 各フレーズページのレイアウト
- フレーズ一覧・おわりに・QRコード
- ページ番号整合

問題があれば報告してください。
