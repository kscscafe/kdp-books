#!/usr/bin/env python3
"""
キャラクター中国語フレーズ集 PDF 生成エンジン（book_template 版）

データは data/phrases.csv、キャラ・本のメタ情報は config/book_config.py から
読み込みます。新キャラ本を作るときは原則この2ファイルだけ書き換えればOK。
"""
import csv, math, os, re
from config import book_config as CFG
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as RL
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── FONTS ──────────────────────────────────────────────────────────────────
from reportlab.pdfbase.ttfonts import TTFont
import platform

def find_dejavu_font():
    """Cross-platform DejaVuSans.ttf locator."""
    candidates = [
        # Mac (Homebrew / system)
        "/Library/Fonts/DejaVuSans.ttf",
        os.path.expanduser("~/Library/Fonts/DejaVuSans.ttf"),
        "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/dejavu/DejaVuSans.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "DejaVuSans.ttf not found.\n"
        "  Mac:   brew install --cask font-dejavu\n"
        "  Linux: sudo apt-get install fonts-dejavu"
    )

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))      # Chinese Song serif — main phrase display
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))   # Japanese Gothic — comment body
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))      # Japanese Mincho — elegant headings

# STHeiti subset for simplified Chinese characters that don't exist in HeiseiKakuGo
# (你/吗/爱/开 etc.). Chinese Gothic style → matches Japanese Gothic body.
STHEI_SUBSET = os.path.join(os.path.dirname(__file__), CFG.FONT_CH_GB_SUBSET)
pdfmetrics.registerFont(TTFont('STHeitiSC-GB', STHEI_SUBSET))

pdfmetrics.registerFont(TTFont('DejaVu', find_dejavu_font()))  # Pinyin Latin

F_CH    = 'STSong-Light'        # Main Chinese phrase display (classical Song serif)
F_CH_GB = 'STHeitiSC-GB'        # Simplified-Chinese fallback in mixed text (Chinese Gothic)
F_JA    = 'HeiseiKakuGo-W5'     # Japanese body (Gothic)
F_JA_M  = 'HeiseiMin-W3'        # Japanese elegant/headings (Mincho)
F_PY    = 'DejaVu'              # Pinyin (full Unicode Latin for tone marks)

# ── COLORS (from config) ────────────────────────────────────────────────────
C_BG         = HexColor(CFG.COLORS['C_BG'])
C_PINK_LIGHT = HexColor(CFG.COLORS['C_PINK_LIGHT'])
C_PINK_MED   = HexColor(CFG.COLORS['C_PINK_MED'])
C_PINK_DARK  = HexColor(CFG.COLORS['C_PINK_DARK'])
C_ROSE       = HexColor(CFG.COLORS['C_ROSE'])
C_DARK_ROSE  = HexColor(CFG.COLORS['C_DARK_ROSE'])
C_BROWN      = HexColor(CFG.COLORS['C_BROWN'])
C_BROWN_MED  = HexColor(CFG.COLORS['C_BROWN_MED'])
C_LINE       = HexColor(CFG.COLORS['C_LINE'])
C_BOX_BG     = HexColor(CFG.COLORS['C_BOX_BG'])
C_BOX_BD     = HexColor(CFG.COLORS['C_BOX_BD'])
C_CHAPTER_BG = HexColor(CFG.COLORS['C_CHAPTER_BG'])
C_WHITE      = white

# ── PAGE SETUP ──────────────────────────────────────────────────────────────
W, H   = A5                   # 419.53 x 595.28 pt
ML, MR = 18*mm, 18*mm
MT, MB = 15*mm, 15*mm
CW     = W - ML - MR          # content width ≈ 306pt

OUTPUT = os.path.join(os.path.dirname(__file__), 'output', CFG.OUTPUT_FILENAME)

# ── DATA (loaded from CSV + config) ──────────────────────────────────────────
def _load_chapters():
    """data/phrases.csv からフレーズを読み込み、章メタは book_config.CHAPTERS_META
    から組み合わせて、本エンジンの内部表現 (list of {num,title,quote,phrases})
    を返す。phrases は (no, chinese, pinyin, japanese, comment) のタプル。"""
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'phrases.csv')
    with open(csv_path, encoding='utf-8') as fp:
        rows = list(csv.DictReader(fp))
    by_ch = {}
    for r in rows:
        ch_num = int(r['chapter'])
        by_ch.setdefault(ch_num, []).append((
            int(r['no']),
            r['chinese'],
            r['pinyin'],
            r['japanese'],
            r['comment'],
        ))
    chapters = []
    for meta in CFG.CHAPTERS_META:
        chapters.append({
            'num':     meta['num'],
            'title':   meta['title'],
            'quote':   meta['quote'],
            'phrases': sorted(by_ch.get(meta['num'], []), key=lambda p: p[0]),
        })
    return chapters

CHAPTERS = _load_chapters()

# ── HELPERS ─────────────────────────────────────────────────────────────────

# 行頭禁則：これらの文字は行頭に置かない（前の行末にぶら下げる）
_NO_LINE_START = set(
    '。、，．！？）」』】〕》〉］｝・…ー'
    'ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ'
)
# 行末禁則：開き括弧は行末に取り残さず、次行の頭へ持ち越す
_NO_LINE_END = set('（「『【〔《〈［｛')

def wrap_text(text, font, size, max_w):
    """Character-by-character wrapping with kinsoku (line-head punctuation hangs
    on the previous line so 。 ！ ？ never appear at the start of a wrapped line)."""
    lines, current = [], ""
    for ch in text:
        test = current + ch
        if stringWidth(test, font, size) > max_w and current:
            if ch in _NO_LINE_START:
                current = test            # hang on current line (slight overflow allowed)
            else:
                lines.append(current)
                current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines

_NEEDS_CH_GB = {}  # cache: char → bool
def _missing_from_japanese_font(ch):
    """True if char is a CJK ideograph NOT in JIS X 0208 (= not in HeiseiKakuGo).
    Typically simplified Chinese: 你/吗/爱/开/见/说/欢…  Result cached."""
    cached = _NEEDS_CH_GB.get(ch)
    if cached is not None:
        return cached
    try:
        ch.encode('shift_jis')
        result = False
    except UnicodeEncodeError:
        result = True
    _NEEDS_CH_GB[ch] = result
    return result

def _is_cjk_ideograph(cp):
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF)

def font_for_char(ch):
    """Per-char font lookup (used for non-CJK and as a fallback).
    For CJK ideographs the run-aware fonts_for_text() is preferred — within a
    run, if any char is simplified-Chinese-only, the whole run uses F_CH_GB so
    that phrases like 你是学生吗 don't mix fonts mid-word."""
    cp = ord(ch)
    if 0x3040 <= cp <= 0x30FF:  return F_JA   # Hiragana / Katakana
    if 0x3000 <= cp <= 0x303F:  return F_JA   # CJK punctuation「」など
    if 0xFF00 <= cp <= 0xFFEF:  return F_JA   # Fullwidth forms（）
    if _is_cjk_ideograph(cp):                  # CJK Unified + Ext A
        return F_CH_GB if _missing_from_japanese_font(ch) else F_JA
    if 0x00A0 <= cp <= 0x024F:  return F_PY   # Latin-1 Supplement + Extended (á é í ó ú / à è ì ò ù / ā ǎ …)
    if 0x0020 <= cp <= 0x007E:  return F_PY   # Basic ASCII
    return F_JA

# Matches a (pinyin) parenthesised marker: full-width or half-width parens
# containing at least one Latin letter (with or without tone marks) and no CJK.
_PINYIN_PARENS = re.compile(
    r'[（(]'
    r'[^（）()一-鿿]*'
    r'[A-Za-z -ɏ]'
    r'[^（）()一-鿿]*'
    r'[）)]'
)

def _pinyin_marked_indices(text):
    """Set of char indices in `text` that are CJK chars immediately preceding
    a （pinyin）marker — treated as Chinese references regardless of JIS coverage."""
    marked = set()
    for m in _PINYIN_PARENS.finditer(text):
        i = m.start() - 1  # last char before （
        while i >= 0 and _is_cjk_ideograph(ord(text[i])):
            marked.add(i)
            i -= 1
    return marked

def fonts_for_text(text):
    """Return a list of (char, font) tuples with run-aware font assignment.

    A CJK ideograph run uses F_CH_GB (Chinese Gothic) when any of:
      - the run contains a simplified-Chinese-only char (你/吗/爱…), OR
      - the run is part of a Chinese reference, detected by an adjacent
        （pinyin）marker (covers JIS-shared cases like 重要/保重/就).
    Otherwise the run uses F_JA (Japanese Gothic). Non-CJK chars use font_for_char()."""
    pinyin_idx = _pinyin_marked_indices(text)
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if _is_cjk_ideograph(ord(ch)):
            j = i
            while j < n and _is_cjk_ideograph(ord(text[j])):
                j += 1
            run = text[i:j]
            is_zh = (
                any(_missing_from_japanese_font(c) for c in run) or
                any(k in pinyin_idx for k in range(i, j))
            )
            run_font = F_CH_GB if is_zh else F_JA
            out.extend((c, run_font) for c in run)
            i = j
        else:
            out.append((ch, font_for_char(ch)))
            i += 1
    return out

# Tighten ASCII space in mixed-text rendering: DejaVu's space (3.5pt @ 11pt)
# plus the surrounding sidebearings made inter-syllable gaps in pinyin (ní hǎo)
# look as wide as a full-width space.
SPACE_SCALE_MIXED = 0.6

def _advance(ch, font, size):
    w = stringWidth(ch, font, size)
    if ch == ' ':
        w *= SPACE_SCALE_MIXED
    return w

def wrap_mixed_text(text, size, max_w):
    """Wrap mixed-language text. Returns a list of lines, each a list of (char, font) tuples.

    Word-aware: a pinyin word (consecutive F_PY non-space) and a Chinese reference
    run (consecutive F_CH_GB) are kept on the same line if they fit. Japanese kana
    and shared kanji wrap char-by-char as usual. Applies line-head kinsoku.

    If a single unit is wider than max_w (e.g. pathologically long pinyin), it
    falls back to char-by-char for that unit only."""
    annotated = fonts_for_text(text)

    # Group annotated chars into atomic units that should not be split mid-line.
    units = []
    i, n = 0, len(annotated)
    while i < n:
        ch, f = annotated[i]
        if f == F_PY and ch != ' ':
            j = i
            while j < n and annotated[j][1] == F_PY and annotated[j][0] != ' ':
                j += 1
            units.append(annotated[i:j])
            i = j
        elif f == F_CH_GB:
            j = i
            while j < n and annotated[j][1] == F_CH_GB:
                j += 1
            units.append(annotated[i:j])
            i = j
        else:
            units.append([annotated[i]])
            i += 1

    lines, current, current_w = [], [], 0.0
    for unit in units:
        unit_w = sum(_advance(ch, f, size) for ch, f in unit)
        if current_w + unit_w > max_w and current:
            first_ch = unit[0][0]
            if unit_w > max_w:
                # Pathological case — fall back to char-by-char for this unit
                for ch, f in unit:
                    cw = _advance(ch, f, size)
                    if current_w + cw > max_w and current:
                        if ch in _NO_LINE_START:
                            current.append((ch, f)); current_w += cw
                        else:
                            lines.append(current)
                            current = [(ch, f)]; current_w = cw
                    else:
                        current.append((ch, f)); current_w += cw
            elif len(unit) == 1 and first_ch in _NO_LINE_START:
                current.extend(unit); current_w += unit_w  # hang punctuation
            else:
                # Pull trailing opener brackets along to the new line
                pull = []
                while current and current[-1][0] in _NO_LINE_END:
                    last = current.pop()
                    current_w -= _advance(last[0], last[1], size)
                    pull.insert(0, last)
                lines.append(current)
                current = pull + list(unit)
                current_w = sum(_advance(ch, f, size) for ch, f in current)
        else:
            current.extend(unit); current_w += unit_w
    if current:
        lines.append(current)
    return lines

def draw_line_mixed(c, x, y, line, size, color):
    """Draw one line of (char, font) tuples produced by wrap_mixed_text()."""
    c.setFillColor(color)
    cx = x
    for ch, f in line:
        c.setFont(f, size)
        c.drawString(cx, y, ch)
        cx += _advance(ch, f, size)

def measure_tight(text, font, size):
    """Width with SPACE_SCALE_MIXED applied to ASCII spaces."""
    if ' ' not in text:
        return stringWidth(text, font, size)
    w = 0.0
    for ch in text:
        cw = stringWidth(ch, font, size)
        if ch == ' ':
            cw *= SPACE_SCALE_MIXED
        w += cw
    return w

def draw_string_tight(c, x, y, text, font, size):
    """drawString equivalent that tightens ASCII space advance.
    Returns the rendered width."""
    c.setFont(font, size)
    if ' ' not in text:
        c.drawString(x, y, text)
        return stringWidth(text, font, size)
    cx = x
    for ch in text:
        c.drawString(cx, y, ch)
        cw = stringWidth(ch, font, size)
        if ch == ' ':
            cw *= SPACE_SCALE_MIXED
        cx += cw
    return cx - x

def draw_centred_tight(c, x_center, y, text, font, size):
    """drawCentredString equivalent with tightened ASCII spaces."""
    w = measure_tight(text, font, size)
    c.setFont(font, size)
    if ' ' not in text:
        c.drawString(x_center - w/2, y, text)
        return
    draw_string_tight(c, x_center - w/2, y, text, font, size)

def to_fullwidth(n):
    """Convert integer to full-width digit string （15 → １５）."""
    fw = '０１２３４５６７８９'
    return ''.join(fw[int(d)] for d in str(n))

def draw_blossom(c, cx, cy, r, petal=None, center=None):
    if petal is None:  petal  = HexColor('#EDAFC0')
    if center is None: center = HexColor('#F9D4DC')
    c.saveState()
    c.translate(cx, cy)
    c.setFillColor(petal)
    c.setStrokeColor(HexColor('#D8849A'))
    c.setLineWidth(0.3)
    for i in range(5):
        c.saveState()
        c.rotate(72 * i)
        c.ellipse(-r*.22, r*.08, r*.22, r*.88, fill=1, stroke=1)
        c.restoreState()
    c.setFillColor(center)
    c.setStrokeColor(HexColor('#E8A0B0'))
    c.setLineWidth(0.5)
    c.circle(0, 0, r*.2, fill=1, stroke=1)
    c.restoreState()

def draw_diamond_line(c, x, y, width, col):
    c.setStrokeColor(col)
    c.setLineWidth(0.8)
    gap = 12
    c.line(x, y, x + width/2 - gap, y)
    c.line(x + width/2 + gap, y, x + width, y)
    c.saveState()
    c.setFillColor(col)
    c.translate(x + width/2, y)
    c.rotate(45)
    c.rect(-4, -4, 8, 8, fill=1, stroke=0)
    c.restoreState()

def draw_footer(c, page_num):
    c.setFont(F_JA, 9)
    c.setFillColor(C_ROSE)
    c.drawCentredString(W/2, MB - 5, str(page_num))
    # footer line
    c.setStrokeColor(C_PINK_MED)
    c.setLineWidth(0.5)
    c.line(ML, MB + 3, W - MR, MB + 3)

def draw_page_bg(c):
    c.setFillColor(C_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

def draw_corner_blossoms(c, size=12, opacity_factor=0.7):
    col = HexColor('#F0C0CE')
    draw_blossom(c, ML + 5,    H - MT - 5,  size, col)
    draw_blossom(c, W - MR - 5, H - MT - 5, size, col)

# ── PAGE BUILDERS ────────────────────────────────────────────────────────────

def page_cover(c):
    """Page 1: cover image"""
    try:
        img = ImageReader(os.path.join(os.path.dirname(__file__), CFG.COVER_IMAGE_PATH))
        c.drawImage(img, 0, 0, width=W, height=H, preserveAspectRatio=False)
    except Exception:
        # Fallback if image unavailable
        c.setFillColor(C_PINK_MED)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFont(F_CH, 28)
        c.setFillColor(C_BROWN)
        c.drawCentredString(W/2, H*0.6, CFG.BOOK_TITLE)
    c.showPage()

def page_intro(c, pg):
    """はじめに"""
    intro_text = ["はじめに", ""] + list(CFG.INTRO_TEXT) + ["", CFG.CHARACTER_NAME]
    SIGNATURE = CFG.CHARACTER_NAME
    draw_page_bg(c)
    draw_corner_blossoms(c)
    # Title bar
    c.setFillColor(C_PINK_LIGHT)
    c.rect(0, H - MT - 40, W, 40, fill=1, stroke=0)
    c.setFont(F_JA_M, 18)
    c.setFillColor(C_DARK_ROSE)
    c.drawCentredString(W/2, H - MT - 28, 'はじめに')
    draw_diamond_line(c, ML, H - MT - 50, CW, C_ROSE)
    # Body text
    y = H - MT - 75
    for line in intro_text:
        if line == "はじめに":
            continue
        if line == "":
            y -= 10
            continue
        c.setFont(F_JA, 11)
        c.setFillColor(C_BROWN)
        if line == SIGNATURE:
            c.drawRightString(W - MR, y, line)
        else:
            c.drawString(ML, y, line)
        y -= 18
        if y < MB + 20:
            break
    draw_footer(c, pg)
    c.showPage()

def page_toc(c, page_map, pg):
    """目次"""
    draw_page_bg(c)
    draw_corner_blossoms(c)
    c.setFillColor(C_PINK_LIGHT)
    c.rect(0, H - MT - 40, W, 40, fill=1, stroke=0)
    c.setFont(F_JA_M, 18)
    c.setFillColor(C_DARK_ROSE)
    c.drawCentredString(W/2, H - MT - 28, '目  次')
    draw_diamond_line(c, ML, H - MT - 50, CW, C_ROSE)

    y = H - MT - 80
    # Front matter
    items = [
        ("はじめに", page_map['intro']),
        ("声調・発音ガイド", page_map['pronunciation']),
    ]
    c.setFont(F_JA, 11)
    c.setFillColor(C_BROWN_MED)
    for title, pn in items:
        c.drawString(ML + 8, y, title)
        c.drawRightString(W - MR, y, str(pn))
        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.4)
        tw = stringWidth(title, F_JA, 11)
        c.line(ML + 8 + tw + 5, y + 3, W - MR - 20, y + 3)
        y -= 20

    y -= 10
    # Chapters
    for ch in CHAPTERS:
        key = f'ch{ch["num"]}'
        # Chapter header
        c.setFillColor(C_ROSE)
        c.setFont(F_JA_M, 12)
        ch_label = f'第{ch["num"]}章　{ch["title"]}'
        c.drawString(ML, y, ch_label)
        c.drawRightString(W - MR, y, str(page_map[key]))
        y -= 22
        # Phrase range
        pnums = [p[0] for p in ch['phrases']]
        c.setFillColor(C_BROWN_MED)
        range_txt = f'PHRASE {pnums[0]:02d} - {pnums[-1]:02d}'
        draw_string_tight(c, ML + 16, y, range_txt, F_PY, 10)
        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.4)
        c.line(ML + 16 + measure_tight(range_txt, F_PY, 10) + 5, y + 3, W - MR - 20, y + 3)
        y -= 18

    y -= 10
    # Back matter
    back = [
        ("フレーズ一覧", page_map['index']),
        ("おわりに", page_map['afterword']),
    ]
    for title, pn in back:
        c.setFont(F_JA, 11)
        c.setFillColor(C_BROWN_MED)
        c.drawString(ML + 8, y, title)
        c.drawRightString(W - MR, y, str(pn))
        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.4)
        tw = stringWidth(title, F_JA, 11)
        c.line(ML + 8 + tw + 5, y + 3, W - MR - 20, y + 3)
        y -= 20

    draw_footer(c, pg)
    c.showPage()

def page_pronunciation(c, pg):
    """声調・発音ガイド"""
    draw_page_bg(c)
    draw_corner_blossoms(c)
    c.setFillColor(C_PINK_LIGHT)
    c.rect(0, H - MT - 40, W, 40, fill=1, stroke=0)
    c.setFont(F_JA_M, 16)
    c.setFillColor(C_DARK_ROSE)
    c.drawCentredString(W/2, H - MT - 28, '声調・発音ガイド')
    draw_diamond_line(c, ML, H - MT - 52, CW, C_ROSE)

    y = H - MT - 78
    # Tone section
    c.setFont(F_JA_M, 13)
    c.setFillColor(C_ROSE)
    c.drawString(ML, y, '四声（4つの声調）')
    y -= 24

    tones = [
        ("第1声", "ā  ē  ī  ō  ū", "高く平らに伸ばす。「ア〜」と伸ばす感じ。"),
        ("第2声", "á  é  í  ó  ú", "低から高へ上げる。日本語の「えっ？」みたい。"),
        ("第3声", "ǎ  ě  ǐ  ǒ  ǔ", "低く落として上げる。「はぁ〜い」の「い」の動き。"),
        ("第4声", "à  è  ì  ò  ù", "高から低へ落とす。日本語の「あっ！」みたい。"),
    ]
    for tone_num, tone_marks, explanation in tones:
        c.setFillColor(C_BOX_BG)
        c.roundRect(ML, y - 16, CW, 32, 4, fill=1, stroke=0)
        c.setStrokeColor(C_BOX_BD)
        c.setLineWidth(0.6)
        c.roundRect(ML, y - 16, CW, 32, 4, fill=0, stroke=1)
        # "第X声" in Japanese font
        c.setFont(F_JA_M, 11)
        c.setFillColor(C_DARK_ROSE)
        c.drawString(ML + 10, y + 4, tone_num)
        tw = stringWidth(tone_num, F_JA_M, 11)
        # tone marks in DejaVu
        c.setFont(F_PY, 12)
        c.setFillColor(C_ROSE)
        c.drawString(ML + 10 + tw + 8, y + 4, tone_marks)
        # explanation
        c.setFont(F_JA, 10)
        c.setFillColor(C_BROWN)
        c.drawString(ML + 10, y - 10, explanation)
        y -= 42

    y -= 10
    c.setFont(F_JA_M, 13)
    c.setFillColor(C_ROSE)
    c.drawString(ML, y, '軽声（5声）')
    y -= 20
    c.setFont(F_JA, 10)
    c.setFillColor(C_BROWN)
    # Draw mixed text: Japanese + Chinese chars for 吗 了 的
    # Chinese refs use F_CH_GB (gothic) to match the style used in comments.
    parts = [
        ('声調のない軽い音。「', F_JA, 10, C_BROWN),
        ('吗', F_CH_GB, 10, C_BROWN),
        ('（ma）」「', F_JA, 10, C_BROWN),
        ('了', F_CH_GB, 10, C_BROWN),
        ('（le）」「', F_JA, 10, C_BROWN),
        ('的', F_CH_GB, 10, C_BROWN),
        ('（de）」など助詞に多い。', F_JA, 10, C_BROWN),
    ]
    mx = ML + 8
    for text, font, size, color in parts:
        c.setFillColor(color)
        mx += draw_string_tight(c, mx, y, text, font, size)
    y -= 28

    c.setFont(F_JA_M, 13)
    c.setFillColor(C_ROSE)
    c.drawString(ML, y, '3声が2つ続く場合')
    y -= 20
    # Mixed: Japanese + Chinese ref + pinyin
    c.setFillColor(C_BROWN)
    p3_parts = [
        ('前の音が2声に変わる。', F_JA,    10, C_BROWN),
        ('你好',                 F_CH_GB, 10, C_BROWN),
        ('（',                   F_JA,    10, C_BROWN),
        ('nǐ hǎo',               F_PY,    10, C_DARK_ROSE),
        ('）→「',                F_JA,    10, C_BROWN),
        ('ní hǎo',               F_PY,    10, C_DARK_ROSE),
        ('」と発音する。',         F_JA,    10, C_BROWN),
    ]
    mx = ML + 8
    for text, font, size, color in p3_parts:
        c.setFillColor(color)
        mx += draw_string_tight(c, mx, y, text, font, size)
    y -= 28

    c.setFont(F_JA_M, 13)
    c.setFillColor(C_ROSE)
    c.drawString(ML, y, 'ポイント')
    y -= 20
    c.setFont(F_JA, 10)
    c.setFillColor(C_BROWN)
    tips = [
        '声に出すことが一番の上達法。恥ずかしさは捨てて！',
        '音楽のメロディーのように声調を体で覚える。',
        '最初は大きく声調の動きをつけてから、徐々に自然に。',
    ]
    for tip in tips:
        c.drawString(ML + 8, y, '◆ ' + tip)
        y -= 16

    draw_footer(c, pg)
    c.showPage()

def page_chapter_divider(c, chapter, pg):
    """章区切りページ"""
    # Gradient-like bg using rectangles
    c.setFillColor(HexColor('#F2C8D4'))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(HexColor('#EDB5C3'))
    c.rect(0, 0, W, H * 0.45, fill=1, stroke=0)

    # Decorative blossoms - scattered
    blossom_positions = [
        (ML - 5,      H - 30,    18, HexColor('#F8D0DA'), HexColor('#FDEEF2')),
        (W - MR + 5,  H - 20,    22, HexColor('#F0B0C0'), HexColor('#FADDE4')),
        (ML + 20,     H - 60,    12, HexColor('#F8D0DA'), HexColor('#FDEEF2')),
        (W/2 - 60,    H - 45,    10, HexColor('#F0B0C0'), HexColor('#FADDE4')),
        (W/2 + 70,    H - 40,    14, HexColor('#F8D0DA'), HexColor('#FDEEF2')),
        (ML,          H*0.35,    16, HexColor('#F0B0C0'), HexColor('#FADDE4')),
        (W - MR,      H*0.30,    20, HexColor('#F8D0DA'), HexColor('#FDEEF2')),
        (W*0.3,       H*0.1,     11, HexColor('#F0B0C0'), HexColor('#FADDE4')),
        (W*0.75,      H*0.15,    15, HexColor('#F8D0DA'), HexColor('#FDEEF2')),
    ]
    for bx, by, br, pc, cc in blossom_positions:
        draw_blossom(c, bx, by, br, pc, cc)

    # Chapter number (large, decorative)
    ch_num_str = f'第{chapter["num"]}章'
    c.setFont(F_JA_M, 13)
    c.setFillColor(HexColor('#A05070'))
    c.drawCentredString(W/2, H * 0.75, ch_num_str)

    # Chapter title
    c.setFont(F_JA_M, 26)
    c.setFillColor(HexColor('#5C1A2A'))
    c.drawCentredString(W/2, H * 0.63, chapter['title'])

    # Decorative line
    draw_diamond_line(c, ML + 10, H * 0.57, CW - 20, HexColor('#C07090'))

    # Quote box
    qbox_h = 80
    qbox_y = H * 0.57 - 20 - qbox_h
    c.setFillColor(HexColor('#FAE0E8'))
    c.setStrokeColor(HexColor('#E0A0B4'))
    c.setLineWidth(0.8)
    c.roundRect(ML + 15, qbox_y, CW - 30, qbox_h, 8, fill=1, stroke=1)

    # Quote text — vertically centered within the box (leaving room for signature)
    quote = f'「{chapter["quote"]}」'
    qlines = wrap_text(quote, F_JA, 12, CW - 60)
    line_h = 18
    content_top    = qbox_y + qbox_h - 8   # padding from box top
    content_bottom = qbox_y + 22           # padding above signature
    v_center = (content_top + content_bottom) / 2
    qy = v_center - 3 + (len(qlines) - 1) * (line_h / 2)  # first baseline
    c.setFillColor(HexColor('#6B2840'))
    for ql in qlines:
        c.setFont(F_JA, 12)
        c.drawCentredString(W/2, qy, ql)
        qy -= line_h

    # Author label  (inside right edge of box)
    c.setFont(F_JA, 10)
    c.setFillColor(HexColor('#A06070'))
    c.drawRightString(ML + 15 + CW - 30 - 10, qbox_y + 8, f'— {CFG.CHARACTER_NICKNAME}')

    # Phrase count — split fonts: F_PY for "PHRASE xx - xx", F_JA for "（Nフレーズ）"
    n = len(chapter['phrases'])
    p_start = chapter['phrases'][0][0]
    p_end   = chapter['phrases'][-1][0]
    lbl_py = f'PHRASE {p_start:02d} - {p_end:02d}'
    lbl_ja = f'  （{to_fullwidth(n)}フレーズ）'
    w_py = measure_tight(lbl_py, F_PY, 10)
    w_ja = stringWidth(lbl_ja, F_JA, 10)
    sx = W/2 - (w_py + w_ja) / 2
    c.setFillColor(HexColor('#905060'))
    draw_string_tight(c, sx, qbox_y - 20, lbl_py, F_PY, 10)
    c.setFont(F_JA, 10)
    c.drawString(sx + w_py, qbox_y - 20, lbl_ja)

    c.showPage()

def page_phrase(c, chapter, phrase_tuple, pg):
    """フレーズページ (1フレーズ = 1ページ)"""
    num, chinese, pinyin, japanese, comment = phrase_tuple
    ch_title = chapter['title']

    draw_page_bg(c)

    # ── Top accent strip ──────────────────────────────────────
    strip_h = 34
    c.setFillColor(C_PINK_LIGHT)
    c.rect(0, H - strip_h, W, strip_h, fill=1, stroke=0)
    c.setStrokeColor(C_PINK_MED)
    c.setLineWidth(0.7)
    c.line(0, H - strip_h, W, H - strip_h)

    # Phrase label (left)
    c.setFillColor(C_DARK_ROSE)
    lbl_phrase = f'PHRASE {num:02d}'
    draw_string_tight(c, ML, H - strip_h + 12, lbl_phrase, F_PY, 9)

    # Chapter name (right)
    c.setFont(F_JA, 8)
    c.setFillColor(C_ROSE)
    c.drawRightString(W - MR, H - strip_h + 12, ch_title)

    # Chapter number dot
    c.setFillColor(C_ROSE)
    c.circle(ML + measure_tight(lbl_phrase, F_PY, 9) + 8,
             H - strip_h + 15, 3, fill=1, stroke=0)

    # Shift main content down for better vertical balance (was top-heavy)
    TOP_PAD = 30

    # ── Large phrase number (decorative background) — kept at original pos
    c.setFont(F_JA_M, 68)
    c.setFillColor(HexColor('#F9E4E9'))
    num_x = W - MR - stringWidth(f'{num:02d}', F_JA_M, 68)
    c.drawString(num_x - 2, H - strip_h - 78, f'{num:02d}')

    # ── Chinese characters ────────────────────────────────────
    ch_size = min(38, max(22, int(360 / max(len(chinese), 1))))
    ch_size = min(38, max(24, ch_size))
    c.setFont(F_CH, ch_size)
    c.setFillColor(C_BROWN)
    # STSong places 。 ， ！ ？ near the top of the em-box at display sizes,
    # which reads as "floating high" next to the kanji. Split off the trailing
    # punctuation and drop it ~10% of the font size to align visually.
    ch_y = H - strip_h - 65 - TOP_PAD
    if chinese and chinese[-1] in '。，！？':
        body, punct = chinese[:-1], chinese[-1]
        body_w  = stringWidth(body,  F_CH, ch_size)
        punct_w = stringWidth(punct, F_CH, ch_size)
        start_x = W/2 - (body_w + punct_w) / 2
        c.drawString(start_x, ch_y, body)
        c.drawString(start_x + body_w, ch_y - ch_size * 0.10, punct)
    else:
        c.drawCentredString(W/2, ch_y, chinese)

    # ── Pinyin ────────────────────────────────────────────────
    pin_size = 13
    c.setFillColor(C_DARK_ROSE)
    draw_centred_tight(c, W/2, H - strip_h - 95 - TOP_PAD, pinyin, F_PY, pin_size)

    # ── Divider ───────────────────────────────────────────────
    div_y = H - strip_h - 112 - TOP_PAD
    draw_diamond_line(c, ML + 20, div_y, CW - 40, C_LINE)

    # ── Japanese translation ──────────────────────────────────
    ja_size = 15
    ja_lines = wrap_text(japanese, F_JA, ja_size, CW - 20)
    ja_y = div_y - 22
    for jl in ja_lines:
        c.setFont(F_JA_M, ja_size)
        c.setFillColor(C_BROWN)
        c.drawCentredString(W/2, ja_y, jl)
        ja_y -= 21

    # ── リンのひとこと box ────────────────────────────────────
    hdr_h   = 22
    cmt_size = 11
    cmt_lines = wrap_mixed_text(comment, cmt_size, CW - 32)
    line_h   = 17
    box_content_h = hdr_h + 14 + len(cmt_lines) * line_h + 14
    box_h    = max(box_content_h, 60)

    box_top    = ja_y - 16
    box_bottom = box_top - box_h
    # Clamp to stay above footer
    if box_bottom < MB + 20:
        box_bottom = MB + 20
        box_h = box_top - box_bottom
    box_x = ML + 4
    box_w = CW - 8

    c.setFillColor(C_BOX_BG)
    c.setStrokeColor(C_BOX_BD)
    c.setLineWidth(0.8)
    c.roundRect(box_x, box_bottom, box_w, box_h, 6, fill=1, stroke=1)

    # Header bar inside box
    hdr_h = 22
    c.setFillColor(C_PINK_MED)
    c.roundRect(box_x, box_top - hdr_h, box_w, hdr_h, 4, fill=1, stroke=0)
    c.setFillColor(C_BOX_BG)
    c.rect(box_x, box_top - hdr_h, box_w, hdr_h / 2, fill=1, stroke=0)
    c.setFillColor(C_PINK_MED)
    c.roundRect(box_x, box_top - hdr_h, box_w, hdr_h, 4, fill=1, stroke=0)

    c.setFont(F_JA_M, 10)
    c.setFillColor(C_DARK_ROSE)
    c.drawString(box_x + 10, box_top - 15, f'{CFG.CHARACTER_NICKNAME}のひとこと')
    # Small star/dot
    c.setFillColor(C_ROSE)
    c.circle(box_x + 10 + stringWidth(f'{CFG.CHARACTER_NICKNAME}のひとこと', F_JA_M, 10) + 8,
             box_top - 11, 2.5, fill=1, stroke=0)

    # Comment text — mixed font rendering (Japanese + Chinese chars + pinyin)
    cmt_y = box_top - hdr_h - 14
    for cl in cmt_lines:
        if cmt_y < box_bottom + 6:
            break
        draw_line_mixed(c, box_x + 12, cmt_y, cl, cmt_size, C_BROWN)
        cmt_y -= line_h

    draw_footer(c, pg)
    c.showPage()

def _split_index_rows(all_phrases):
    """Split index rows into pages based on actual row heights.
    Returns list of page batches; each batch is list of (num, zh_lines, py_lines, ja_lines, row_h).

    Extracted so build_pdf can predict the page count BEFORE rendering (page_map
    needs to know where the afterword starts before the TOC is drawn)."""
    X_ZH = ML + 20
    X_PY = ML + 108
    X_JA = ML + 224
    MAX_ZH_W = X_PY - X_ZH - 4
    MAX_PY_W = X_JA - X_PY - 4
    MAX_JA_W = W - MR - X_JA - 3
    Y_HEADERS    = H - MT - 72
    Y_DATA_START = Y_HEADERS - 18
    Y_DATA_STOP  = MB + 22
    AVAIL_H      = Y_DATA_START - Y_DATA_STOP
    ROW_H1, ROW_H2 = 19, 32

    rows = []
    for num, zh, py, ja, _ in all_phrases:
        zh_lines = wrap_text(zh, F_CH, 9, MAX_ZH_W)[:2]
        py_lines = wrap_text(py, F_PY, 8, MAX_PY_W)[:2]
        ja_lines = wrap_text(ja, F_JA, 9, MAX_JA_W)[:2]
        n_lines  = max(len(zh_lines), len(py_lines), len(ja_lines))
        row_h    = ROW_H2 if n_lines > 1 else ROW_H1
        rows.append((num, zh_lines, py_lines, ja_lines, row_h))

    pages, batch, used_h = [], [], 0
    for row in rows:
        rh = row[4]
        if used_h + rh > AVAIL_H and batch:
            pages.append(batch)
            batch, used_h = [], 0
        batch.append(row)
        used_h += rh
    if batch:
        pages.append(batch)
    return pages

def page_index(c, all_phrases, start_pg):
    """フレーズ一覧 — ピンイン・日本語訳は最大2行、省略なし"""
    X_NO = ML
    X_ZH = ML + 20
    X_PY = ML + 108
    X_JA = ML + 224

    # Exact y positions (PDF y increases upward)
    Y_TITLE_TEXT = H - MT - 28     # "フレーズ一覧" baseline
    Y_DIAMOND    = H - MT - 52     # decorative line
    Y_HEADERS    = H - MT - 72     # "No. 中国語 …" baseline
    Y_DATA_START = Y_HEADERS - 18  # first data row baseline

    LINE2_OFFSET = 13              # y-offset for 2nd line

    pages = _split_index_rows(all_phrases)
    n_pages = len(pages)

    # ── Render each page ─────────────────────────────────────
    for pi, page_batch in enumerate(pages):
        draw_page_bg(c)
        draw_corner_blossoms(c)

        # Title bar
        c.setFillColor(C_PINK_LIGHT)
        c.rect(0, H - MT - 40, W, 40, fill=1, stroke=0)
        c.setFont(F_JA_M, 16)
        c.setFillColor(C_DARK_ROSE)
        suffix = f'  {pi+1} / {n_pages}' if n_pages > 1 else ''
        c.drawCentredString(W/2, Y_TITLE_TEXT, f'フレーズ一覧{suffix}')
        draw_diamond_line(c, ML, Y_DIAMOND, CW, C_ROSE)

        # Column headers
        y = Y_HEADERS
        c.setFont(F_PY, 9);  c.setFillColor(C_ROSE);  c.drawString(X_NO, y, 'No.')
        c.setFont(F_JA, 9);  c.drawString(X_ZH, y, '中国語')
        c.drawString(X_PY, y, 'ピンイン')
        c.drawString(X_JA, y, '日本語訳')
        # Header underline — same x-extent as row separators below
        c.setStrokeColor(C_PINK_MED); c.setLineWidth(0.6)
        c.line(ML - 2, y - 3, W - MR + 2, y - 3)

        y = Y_DATA_START

        for row_i, (num, zh_lines, py_lines, ja_lines, row_h) in enumerate(page_batch):
            # No background, no separator — rows separated by whitespace only.

            # No.
            c.setFont(F_PY, 9); c.setFillColor(C_ROSE)
            c.drawString(X_NO, y, f'{num:02d}')

            # Chinese — up to 2 lines, no truncation
            c.setFont(F_CH, 9); c.setFillColor(C_BROWN)
            for li, zl in enumerate(zh_lines):
                c.drawString(X_ZH, y - li * LINE2_OFFSET, zl)

            # Pinyin — up to 2 lines, no truncation
            c.setFillColor(C_DARK_ROSE)
            for li, pl in enumerate(py_lines):
                draw_string_tight(c, X_PY, y - li * LINE2_OFFSET, pl, F_PY, 8)

            # Japanese — up to 2 lines, no truncation
            c.setFont(F_JA, 9); c.setFillColor(C_BROWN_MED)
            for li, jl in enumerate(ja_lines):
                c.drawString(X_JA, y - li * LINE2_OFFSET, jl)

            y -= row_h

        draw_footer(c, start_pg + pi)
        c.showPage()

    return n_pages

def page_afterword(c, pg):
    """おわりに"""
    draw_page_bg(c)
    # Decorative blossoms
    for bx, by, br in [(ML-8, H*0.85, 20), (W-MR+8, H*0.82, 16),
                        (ML+15, H*0.72, 12), (W*0.6, H*0.78, 9)]:
        draw_blossom(c, bx, by, br)

    c.setFillColor(C_PINK_LIGHT)
    c.rect(0, H - MT - 40, W, 40, fill=1, stroke=0)
    c.setFont(F_JA_M, 18)
    c.setFillColor(C_DARK_ROSE)
    c.drawCentredString(W/2, H - MT - 28, 'おわりに')
    draw_diamond_line(c, ML, H - MT - 52, CW, C_ROSE)

    text_lines = (list(CFG.AFTERWORD_TEXT)
                  + ["", CFG.AFTERWORD_CHINESE_SENDOFF, "", CFG.CHARACTER_NAME])
    SIGNATURE = CFG.CHARACTER_NAME

    y = H - MT - 80
    for line in text_lines:
        if line == "":
            y -= 10
            continue
        if line == SIGNATURE:
            c.setFont(F_JA, 11)
            c.setFillColor(C_BROWN)
            c.drawRightString(W - MR, y, line)
        elif any(_is_cjk_ideograph(ord(ch)) and _missing_from_japanese_font(ch) for ch in line):
            # Contains simplified-Chinese chars: render with run-aware fonts
            draw_line_mixed(c, ML, y, fonts_for_text(line), 11, C_BROWN)
        else:
            c.setFont(F_JA, 11)
            c.setFillColor(C_BROWN)
            c.drawString(ML, y, line)
        y -= 18

    # ── App Store QR code (HanYuAI) ──────────────────────────
    # Footer decorative line sits at MB + 3 = 45.5pt. Keep QR bottom 15pt+ above
    # it and ensure caption (qr_y - 14) also clears the footer line.
    qr_size = 80
    qr_x = W / 2 - qr_size / 2
    qr_y = 70
    qr_path = os.path.join(os.path.dirname(__file__), CFG.QR_IMAGE_PATH)
    if os.path.exists(qr_path):
        c.drawImage(
            ImageReader(qr_path),
            qr_x, qr_y,
            width=qr_size, height=qr_size,
            preserveAspectRatio=True,
        )
    # Caption below QR
    c.setFont(F_JA, 8)
    c.setFillColor(C_BROWN_MED)
    c.drawCentredString(W / 2, qr_y - 14, CFG.QR_CAPTION)

    draw_footer(c, pg)
    c.showPage()

# ── MAIN ─────────────────────────────────────────────────────────────────────

def build_pdf():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    c = RL.Canvas(OUTPUT, pagesize=A5)
    c.setTitle(CFG.PDF_TITLE)
    c.setAuthor(CFG.PDF_AUTHOR)
    c.setSubject(CFG.PDF_SUBJECT)

    # ── Pre-compute page numbers ─────────────────────────────
    pg = 1  # cover
    pg_cover = 1

    pg_intro = 2
    pg += 1  # intro = 1 page (simplified)

    pg_toc = pg + 1
    pg += 1

    pg_pron = pg + 1
    pg += 1

    page_map = {'intro': pg_intro, 'toc': pg_toc, 'pronunciation': pg_pron}
    phrase_pages = {}

    pg = pg_pron + 1
    for ch in CHAPTERS:
        key = f'ch{ch["num"]}'
        page_map[key] = pg
        pg += 1  # chapter divider
        for phrase in ch['phrases']:
            phrase_pages[phrase[0]] = pg
            pg += 1

    # Index — predict actual page count from the same split logic page_index uses,
    # otherwise the afterword page number drifts and two pages end up labelled 63.
    all_phrases = [p for ch in CHAPTERS for p in ch['phrases']]
    n_idx = len(_split_index_rows(all_phrases))
    page_map['index'] = pg
    pg += n_idx
    page_map['afterword'] = pg

    # ── Render ──────────────────────────────────────────────
    page_cover(c)
    page_intro(c, pg_intro)
    page_toc(c, page_map, pg_toc)
    page_pronunciation(c, pg_pron)

    current_pg = pg_pron + 1
    for ch in CHAPTERS:
        page_chapter_divider(c, ch, current_pg)
        current_pg += 1
        for phrase in ch['phrases']:
            page_phrase(c, ch, phrase, current_pg)
            current_pg += 1

    page_index(c, all_phrases, page_map['index'])
    page_afterword(c, page_map['afterword'])

    c.save()
    total_pages = page_map['afterword']
    print(f'Done! {total_pages} pages → {OUTPUT}')

    # Optional: write page_map for downstream validation
    import json as _json
    map_path = os.path.join(os.path.dirname(OUTPUT), 'page_map.json')
    with open(map_path, 'w', encoding='utf-8') as _f:
        _json.dump(page_map, _f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    build_pdf()
