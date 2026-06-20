#!/usr/bin/env bash
# 安装写作相关 Agent Skills（非 MCP）
set -euo pipefail

MODE="${1:-all}"

install_comic() {
  echo ">>> 安装 baoyu-comic（儿童/绘本）"
  npx skills add jimliu/baoyu-skills --skill baoyu-comic
}

install_translate() {
  echo ">>> 安装 baoyu-translate（出版级长篇）"
  npx skills add jimliu/baoyu-skills --skill baoyu-translate
}

case "$MODE" in
  comic) install_comic ;;
  translate) install_translate ;;
  all)
    install_comic
    install_translate
    ;;
  -h|--help)
    echo "用法: install-writing-skills.sh [comic|translate|all]"
    exit 0
    ;;
  *)
    echo "未知模式: $MODE" >&2
    exit 1
    ;;
esac

echo ">>> Skills 安装完成"
