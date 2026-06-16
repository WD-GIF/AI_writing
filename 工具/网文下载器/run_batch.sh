#!/bin/bash
# 一键批量爬取脚本
# 用法：bash run_batch.sh [urls文件] [输出目录]

set -e

# 默认值
URLS_FILE="${1:-../../待爬取/urls.txt}"
OUTPUT_DIR="${2:-../../素材/范文库/$(date +%Y-%m-%d)}"
MIN_CHARS="${MIN_CHARS:-8000}"
MAX_CHARS="${MAX_CHARS:-12000}"

# 进入脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 urls 文件
if [ ! -f "$URLS_FILE" ]; then
    echo "❌ URL 文件不存在: $URLS_FILE"
    exit 1
fi

# 检查依赖
python3 -c "import requests, bs4" 2>/dev/null || {
    echo "📦 安装依赖..."
    pip install -q -r requirements.txt
}

# 输出目录
mkdir -p "$OUTPUT_DIR"

echo "📋 URL 文件:   $URLS_FILE"
echo "📂 输出目录:   $OUTPUT_DIR"
echo "📏 字数范围:   $MIN_CHARS - $MAX_CHARS"
echo ""

# 跑
python3 novel_downloader.py \
    --batch "$URLS_FILE" \
    --min "$MIN_CHARS" \
    --max "$MAX_CHARS" \
    --out "$OUTPUT_DIR"

# 生成汇总
echo "📝 生成汇总文件..."
SUMMARY_FILE="$OUTPUT_DIR/汇总.md"
{
    echo "# 爬取批次汇总"
    echo ""
    echo "**时间**: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "**来源**: \`$URLS_FILE\`"
    echo ""
    echo "## 已下载文件"
    echo ""
    for f in "$OUTPUT_DIR"/*.{txt,md}; do
        [ -e "$f" ] || continue
        name=$(basename "$f")
        size=$(wc -c < "$f")
        chars=$(python3 -c "
with open('$f','r',encoding='utf-8') as fp:
    t = fp.read()
print(sum(1 for c in t if '\u4e00' <= c <= '\u9fff'))
" 2>/dev/null || echo "?")
        echo "- \`$name\` — $chars 字（文件 $size 字节）"
    done

    if [ -d "$OUTPUT_DIR/_筛除" ]; then
        echo ""
        echo "## 被筛除（字数不符）"
        echo ""
        for f in "$OUTPUT_DIR/_筛除"/*; do
            [ -e "$f" ] || continue
            name=$(basename "$f")
            chars=$(python3 -c "
with open('$f','r',encoding='utf-8') as fp:
    t = fp.read()
print(sum(1 for c in t if '\u4e00' <= c <= '\u9fff'))
" 2>/dev/null || echo "?")
            echo "- \`$name\` — $chars 字"
        done
    fi
} > "$SUMMARY_FILE"

echo "✅ 汇总文件: $SUMMARY_FILE"
echo ""
echo "🎉 完成。下一步:"
echo "  cd /workspace && git add . && git commit -m '爬取批次 $(date +%Y-%m-%d)' && git push"
