# MCP 配置说明

本仓库按**题材**预置 MCP 套件，配置文件在 `mcp.profiles/`。

## 快速切换

```bash
# 查看可用题材
./工具/switch-mcp-profile.sh

# 切换到指定题材（示例：言情/古风）
./工具/switch-mcp-profile.sh yanqing-gufeng
```

切换后：**Cursor → Reload Window**（或重启 Cursor），使 MCP 生效。

## 当前激活

默认题材：**网文（玄幻/都市）** → `mcp.profiles/wangwen-xuanhuan-dushi.json`

完整对照表见：`工具/MCP题材套件.md`

## 密钥

1. 复制 `.env.mcp.example` 为 `.env.mcp`（勿提交）
2. 填入 API Key
3. 在 shell 或 `~/.cursor/.env` 中 export，或在 Cursor 系统环境变量中配置

## Skills（非 MCP）

部分工具是 **Agent Skill**，不在 `mcp.json` 里：

```bash
./工具/install-writing-skills.sh
```

- `baoyu-comic` → 儿童/绘本
- `baoyu-translate` → 出版级长篇

## 无官方 MCP 的工具

| 工具 | 替代方案 |
|---|---|
| Novelcrafter | 本地 Codex 导出 + 仓库 `设定/`/`大纲/` |
| Sudowrite | 浏览器插件；或 viaSocket 桥接（需自配） |
| Storybird | 网页创作；配图用 Recraft MCP |
| Acontext | 自托管 Docker；悬疑项目可用 Lex + mem0 暂代 |
