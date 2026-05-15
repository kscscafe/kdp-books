#!/usr/bin/env python3
"""
林小雨「気持ちを伝える中国語フレーズ50」
Fixed Layout EPUB3 (KDP対応) ビルダー

fxl_pages/page-XX.png を1ページずつ配置したFXL EPUBを生成する。
"""
import os, sys, zipfile, glob, struct, uuid
from datetime import datetime, timezone

ROOT     = os.path.dirname(os.path.abspath(__file__))
SRC_DIR  = os.path.join(ROOT, 'fxl_pages')
OUT_PATH = os.path.join(ROOT, 'output', 'lin_phrases.epub')

TITLE    = '気持ちを伝える中国語フレーズ50'
AUTHOR   = '林小雨'
LANG     = 'ja'
BOOK_ID  = f'urn:uuid:{uuid.uuid4()}'
MODIFIED = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def png_size(path):
    """Read PNG width/height from IHDR without external libs."""
    with open(path, 'rb') as f:
        sig = f.read(8)
        if sig != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Not a PNG: {path}')
        f.read(4)              # IHDR length
        if f.read(4) != b'IHDR':
            raise ValueError(f'Missing IHDR: {path}')
        w, h = struct.unpack('>II', f.read(8))
    return w, h


def main():
    images = sorted(glob.glob(os.path.join(SRC_DIR, 'page-*.png')))
    if not images:
        print(f'ERROR: no images in {SRC_DIR}', file=sys.stderr)
        sys.exit(1)

    # Use page 1's dimensions as the rendition viewport.
    # KDP FXL guidelines: all spreads share the same viewport.
    W, H = png_size(images[0])
    print(f'{len(images)} pages, viewport {W}x{H}')

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    # ── container.xml ─────────────────────────────────────────
    container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
'''

    # ── package.opf ───────────────────────────────────────────
    manifest_items = []
    spine_items    = []
    for i, img_path in enumerate(images, start=1):
        img_name  = f'page-{i:02d}.png'
        page_name = f'page-{i:02d}.xhtml'
        manifest_items.append(
            f'    <item id="img{i:02d}" href="images/{img_name}" media-type="image/png"/>'
        )
        cover_props = ' properties="cover-image"' if i == 1 else ''
        # Override manifest entry for page 1 image to mark as cover.
        if i == 1:
            manifest_items[-1] = (
                f'    <item id="img{i:02d}" href="images/{img_name}" '
                f'media-type="image/png" properties="cover-image"/>'
            )
        manifest_items.append(
            f'    <item id="pg{i:02d}" href="xhtml/{page_name}" '
            f'media-type="application/xhtml+xml" properties="svg"/>'
        )
        spine_items.append(
            f'    <itemref idref="pg{i:02d}" properties="rendition:layout-pre-paginated"/>'
        )

    manifest_items.append(
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    )

    package_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
         version="3.0"
         unique-identifier="bookid"
         prefix="rendition: http://www.idpf.org/vocab/rendition/#">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{BOOK_ID}</dc:identifier>
    <dc:title>{TITLE}</dc:title>
    <dc:creator>{AUTHOR}</dc:creator>
    <dc:language>{LANG}</dc:language>
    <meta property="dcterms:modified">{MODIFIED}</meta>
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:orientation">portrait</meta>
    <meta property="rendition:spread">none</meta>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine>
{chr(10).join(spine_items)}
  </spine>
</package>
'''

    # ── nav.xhtml ─────────────────────────────────────────────
    nav_items = '\n'.join(
        f'        <li><a href="xhtml/page-{i:02d}.xhtml">Page {i}</a></li>'
        for i in range(1, len(images) + 1)
    )
    nav_xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      lang="{LANG}" xml:lang="{LANG}">
<head>
  <meta charset="UTF-8"/>
  <title>Navigation</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>目次</h1>
    <ol>
{nav_items}
    </ol>
  </nav>
</body>
</html>
'''

    # ── per-page XHTML template ───────────────────────────────
    def page_xhtml(idx, img_w, img_h):
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      lang="{LANG}" xml:lang="{LANG}">
<head>
  <meta charset="UTF-8"/>
  <title>Page {idx}</title>
  <meta name="viewport" content="width={img_w}, height={img_h}"/>
  <style>
    html, body {{ margin: 0; padding: 0; }}
    svg {{ display: block; }}
  </style>
</head>
<body>
  <svg xmlns="http://www.w3.org/2000/svg"
       xmlns:xlink="http://www.w3.org/1999/xlink"
       width="100%" height="100%"
       viewBox="0 0 {img_w} {img_h}"
       preserveAspectRatio="xMidYMid meet">
    <image width="{img_w}" height="{img_h}"
           xlink:href="../images/page-{idx:02d}.png"/>
  </svg>
</body>
</html>
'''

    # ── Build the EPUB (ZIP) ──────────────────────────────────
    with zipfile.ZipFile(OUT_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype: stored (uncompressed), must be first entry, no extra fields
        zi = zipfile.ZipInfo('mimetype')
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, 'application/epub+zip')

        zf.writestr('META-INF/container.xml', container_xml)
        zf.writestr('OEBPS/package.opf',      package_opf)
        zf.writestr('OEBPS/nav.xhtml',        nav_xhtml)

        for i, img_path in enumerate(images, start=1):
            w, h = png_size(img_path)
            zf.writestr(f'OEBPS/xhtml/page-{i:02d}.xhtml', page_xhtml(i, w, h))
            with open(img_path, 'rb') as f:
                zf.writestr(f'OEBPS/images/page-{i:02d}.png', f.read())

    size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
    print(f'Done! {OUT_PATH} ({size_mb:.2f} MB)')


if __name__ == '__main__':
    main()
