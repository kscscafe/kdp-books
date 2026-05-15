#!/usr/bin/env python3
"""
build_phrases.py 実行後の自動検証。

チェック内容:
  1. 物理ページ数が期待値（EXPECTED_PAGES = 64）と一致するか
  2. フレーズ一覧に 01〜50 が全件存在するか（ソース側 + PDF側）
  3. ピンインフィールドに数字が混入していないか
  4. TOC のページ番号と実ページの内容が一致するか（page_map 経由）

usage:
  python3 validate_pdf.py [pdf_path] [page_map_json]

  pdf_path       省略時は output/lin_phrases.pdf
  page_map_json  省略時は output/page_map.json
"""
import json
import os
import re
import sys

EXPECTED_PAGES = 64
DEFAULT_PDF = os.path.join(os.path.dirname(__file__), 'output', 'lin_phrases.pdf')
DEFAULT_MAP = os.path.join(os.path.dirname(__file__), 'output', 'page_map.json')


def _load_source_chapters():
    """build_phrases.py の CHAPTERS をモジュールから取得する。
    インポート副作用（フォント登録など）を踏むが、結果は同じファイルから取得できる。"""
    sys.path.insert(0, os.path.dirname(__file__))
    from build_phrases import CHAPTERS  # noqa: F401
    return CHAPTERS


def check_page_count(pdf_path, errors):
    from pypdf import PdfReader
    r = PdfReader(pdf_path)
    n = len(r.pages)
    if n != EXPECTED_PAGES:
        errors.append(f'[ページ数] 実{n}ページ, 期待 {EXPECTED_PAGES}')
    return r


def check_phrase_coverage_source(chapters, errors):
    """ソースデータに 1〜50 が漏れなくあるか。"""
    nums = sorted(p[0] for ch in chapters for p in ch['phrases'])
    expected = list(range(1, 51))
    if nums != expected:
        missing = set(expected) - set(nums)
        extra = set(nums) - set(expected)
        errors.append(f'[フレーズ番号] 欠番 {sorted(missing)}, 余分 {sorted(extra)}')


def check_phrase_coverage_pdf(reader, page_map, errors):
    """フレーズ一覧（index）の各ページから 01〜50 を全件回収できるか。"""
    if 'index' not in page_map:
        errors.append('[index] page_map に index 開始ページが無い')
        return
    start = page_map['index']
    afterword = page_map.get('afterword', len(reader.pages) + 1)
    found = set()
    for pno in range(start, afterword):
        t = reader.pages[pno - 1].extract_text() or ''
        for m in re.finditer(r'\b(\d{1,2})\b', t):
            n = int(m.group(1))
            if 1 <= n <= 50:
                found.add(n)
    missing = set(range(1, 51)) - found
    if missing:
        errors.append(f'[フレーズ一覧] PDF 上で見つからない番号 {sorted(missing)}')


def check_pinyin_digits(chapters, errors):
    """ピンインフィールドに数字が混入していないか。"""
    for ch in chapters:
        for num, zh, py, ja, cmt in ch['phrases']:
            if re.search(r'\d', py):
                errors.append(f'[ピンイン] PHRASE {num:02d} に数字が混入: "{py}"')


# 各セクションが「正しいページか」を判定するための部分文字列
EXPECTED_SUBSTRINGS = {
    'cover':         None,  # 表紙画像のみ、テキストなし → skip
    'intro':         'はじめに',
    'toc':           '目',  # '目  次' は cat -n で分かれることがある
    'pronunciation': '声調',
    'index':         'フレーズ一覧',
    'afterword':     'おわりに',
    'ch1':           '第1章',
    'ch2':           '第2章',
    'ch3':           '第3章',
    'ch4':           '第4章',
    'ch5':           '第5章',
}


def check_toc_pages(reader, page_map, errors):
    """page_map に書かれたページに、期待される内容が載っているか。"""
    for key, expected in EXPECTED_SUBSTRINGS.items():
        if expected is None or key not in page_map:
            continue
        pno = page_map[key]
        if not (1 <= pno <= len(reader.pages)):
            errors.append(f'[TOC] {key}=p.{pno} は範囲外 (総{len(reader.pages)})')
            continue
        t = reader.pages[pno - 1].extract_text() or ''
        if expected not in t:
            errors.append(f'[TOC] p.{pno} に "{expected}" が無い (key={key})')


def validate(pdf_path=None, page_map_path=None) -> bool:
    pdf_path = pdf_path or DEFAULT_PDF
    page_map_path = page_map_path or DEFAULT_MAP

    if not os.path.exists(pdf_path):
        print(f'❌ PDF が見つからない: {pdf_path}')
        return False

    errors = []
    try:
        chapters = _load_source_chapters()
    except Exception as e:
        errors.append(f'[ソース] CHAPTERS の読み込み失敗: {e}')
        chapters = []

    reader = check_page_count(pdf_path, errors)
    check_phrase_coverage_source(chapters, errors)
    check_pinyin_digits(chapters, errors)

    if os.path.exists(page_map_path):
        with open(page_map_path, encoding='utf-8') as f:
            page_map = json.load(f)
        check_phrase_coverage_pdf(reader, page_map, errors)
        check_toc_pages(reader, page_map, errors)
    else:
        errors.append(f'[page_map] {page_map_path} が無いので TOC/index 検証をスキップ')

    if errors:
        print('❌ 検証エラー:')
        for e in errors:
            print(f'  - {e}')
        return False
    print('✅ 検証OK')
    return True


if __name__ == '__main__':
    pdf  = sys.argv[1] if len(sys.argv) > 1 else None
    pmap = sys.argv[2] if len(sys.argv) > 2 else None
    sys.exit(0 if validate(pdf, pmap) else 1)
