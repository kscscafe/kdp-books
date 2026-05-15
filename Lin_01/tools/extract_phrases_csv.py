#!/usr/bin/env python3
"""
Lin_01/build_phrases.py の CHAPTERS から phrases.csv を書き出す。

列：
  no,chapter,chinese,pinyin,japanese,comment,supplemental_pinyin
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIN_ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, LIN_ROOT)

from build_phrases import CHAPTERS  # noqa: E402

DEST = os.path.abspath(os.path.join(LIN_ROOT, '..', 'book_template', 'data', 'phrases.csv'))


def main():
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    rows = []
    for ch in CHAPTERS:
        for num, zh, py, ja, cmt in ch['phrases']:
            rows.append({
                'no': num,
                'chapter': ch['num'],
                'chinese': zh,
                'pinyin': py,
                'japanese': ja,
                'comment': cmt,
                'supplemental_pinyin': '',  # reserved for future use
            })
    rows.sort(key=lambda r: r['no'])

    fieldnames = ['no', 'chapter', 'chinese', 'pinyin', 'japanese',
                  'comment', 'supplemental_pinyin']
    with open(DEST, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f'Wrote {len(rows)} rows → {DEST}')


if __name__ == '__main__':
    main()
