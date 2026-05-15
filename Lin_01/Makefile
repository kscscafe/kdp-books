.PHONY: build open check clean setup

build:
	python3 build_phrases.py

open: build
	open output/lin_phrases.pdf

check:
	python3 - <<'EOF'
	from reportlab.pdfbase import pdfmetrics
	from reportlab.pdfbase.cidfonts import UnicodeCIDFont
	from reportlab.pdfbase.ttfonts import TTFont
	import sys
	from build_phrases import find_dejavu_font
	ok = True
	for name in ['STSong-Light', 'HeiseiKakuGo-W5', 'HeiseiMin-W3']:
	    try:
	        pdfmetrics.registerFont(UnicodeCIDFont(name))
	        print(f"✓ CID: {name}")
	    except Exception as e:
	        print(f"✗ {name}: {e}"); ok = False
	path = find_dejavu_font()
	if path:
	    print(f"✓ DejaVu: {path}")
	else:
	    print("✗ DejaVuSans.ttf not found"); ok = False
	sys.exit(0 if ok else 1)
	EOF

clean:
	rm -f output/*.pdf

setup:
	bash setup.sh
