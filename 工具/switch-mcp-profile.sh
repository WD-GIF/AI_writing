#!/usr/bin/env bash
# 切换 Cursor MCP 题材配置
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILES_DIR="$ROOT/.cursor/mcp.profiles"
TARGET="$ROOT/.cursor/mcp.json"

usage() {
  cat <<'EOF'
用法: switch-mcp-profile.sh [profile]

可用 profile（题材）:
  wangwen-xuanhuan-dushi   网文（玄幻/都市）
  yanqing-gufeng           言情/古风
  kehua-yinghe             科幻硬核
  ertong-huiben            儿童/绘本
  xuanyi-tuili             悬疑/推理
  chuban-changpian         出版级长篇

示例:
  ./工具/switch-mcp-profile.sh yanqing-gufeng

切换后请在 Cursor 中 Reload Window。
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "${#}" -eq 0 ]]; then
  usage
  exit 0
fi

PROFILE="$1"
SRC="$PROFILES_DIR/${PROFILE}.json"

if [[ ! -f "$SRC" ]]; then
  echo "错误: 找不到 profile: $SRC" >&2
  usage
  exit 1
fi

# 去掉 $comment 行（Cursor 虽会忽略未知键，保持 mcp.json 干净）
python3 - "$SRC" "$TARGET" <<'PY'
import json, pathlib, sys
src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
data = json.loads(src.read_text())
data.pop("$comment", None)
out = {"mcpServers": data["mcpServers"]}
dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(f"已切换 MCP profile → {src.name}")
PY

echo "请 Reload Cursor 窗口使配置生效。"
