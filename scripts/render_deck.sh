#!/bin/bash
# 把 pptx 渲染成逐页 PNG，用于视觉校对。
# 用法: render_deck.sh deck.pptx [输出目录]
#
# 必须在沙箱之外跑（Claude 的 terminal 工具 / 用户自己的终端）：
# Chrome 无头模式在沙箱内会因 process singleton / unix socket 被拒而失败。

set -e
DECK="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUT="${2:-$PWD/.pptx_render}"
SK="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

rm -rf "$OUT"
mkdir -p "$OUT/unpacked" "$OUT/pages" "$OUT/pngs"

python3 - "$DECK" "$OUT/unpacked" <<'PY'
import sys, zipfile
zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])
PY

SPLIT_DIR="$OUT/pages" python3 "$SK/render_slides.py" "$OUT/unpacked" "$OUT/preview.html"

for f in "$OUT"/pages/slide*.html; do
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --virtual-time-budget=800 --window-size=1280,720 \
    --screenshot="$OUT/pngs/$(basename "$f" .html).png" "file://$f" >/dev/null 2>&1
done

echo "rendered -> $OUT/pngs"
ls "$OUT/pngs" | wc -l
