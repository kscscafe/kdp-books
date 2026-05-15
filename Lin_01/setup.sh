#!/bin/bash
# setup.sh — 初回セットアップスクリプト
set -e

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "🔍 Checking for DejaVu font (needed for pinyin tone marks)..."
python3 - <<'EOF'
import glob, sys, os

search_paths = [
    # Mac (Homebrew / system)
    "/Library/Fonts/DejaVuSans.ttf",
    os.path.expanduser("~/Library/Fonts/DejaVuSans.ttf"),
    "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]

found = next((p for p in search_paths if os.path.exists(p)), None)

if found:
    print(f"  ✓ Found: {found}")
else:
    print("  ✗ DejaVuSans.ttf not found.")
    import platform
    if platform.system() == "Darwin":
        print("\n  Install with:")
        print("    brew install --cask font-dejavu")
        print("  or:")
        print("    brew install font-dejavu-sans")
    else:
        print("\n  Install with:")
        print("    sudo apt-get install -y fonts-dejavu")
    sys.exit(1)
EOF

echo ""
echo "🔍 Checking for cover image..."
if [ -f "assets/cover.png" ]; then
    echo "  ✓ assets/cover.png found"
else
    echo "  ⚠ assets/cover.png not found"
    echo "    → Place your cover image at assets/cover.png"
fi

echo ""
echo "🧪 Testing reportlab CID fonts..."
python3 - <<'EOF'
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
for name in ['STSong-Light', 'HeiseiKakuGo-W5', 'HeiseiMin-W3']:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(name))
        print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ {name}: {e}")
EOF

echo ""
mkdir -p output
echo "✅ Setup complete. Run: python3 build_phrases.py"
