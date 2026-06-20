# MCP 题材套件配置

> 按题材选用 MCP + Skill 组合。MCP 写入 `.cursor/mcp.json`；Skill 单独安装。

---

## 题材对照表

| 题材 | MCP 套件 | 配置文件 |
|---|---|---|
| 网文（玄幻/都市） | Novelcrafter + mem0 + Recraft + Tavily | `wangwen-xuanhuan-dushi.json` |
| 言情/古风 | Sudowrite + Ideogram + Obsidian | `yanqing-gufeng.json` |
| 科幻硬核 | World Anvil + arXiv + Midjourney | `kehua-yinghe.json` |
| 儿童/绘本 | Storybird + Recraft + baoyu-comic | `ertong-huiben.json` |
| 悬疑/推理 | World Anvil + Lex + Acontext | `xuanyi-tuili.json` |
| 出版级长篇 | Lex + mem0 + Notion + baoyu-translate | `chuban-changpian.json` |

切换命令：`./工具/switch-mcp-profile.sh <配置文件名（不含 .json）>`

---

## 各套件用途

### 网文（玄幻/都市）

| 工具 | 类型 | 作用 |
|---|---|---|
| **mem0** | MCP ✅ | 长篇人设/伏笔/已写章节记忆 |
| **Tavily** | MCP ✅ | 查资料、热词、竞品标题 |
| **Recraft** | MCP ✅ | 封面、人设图、宣传图 |
| **Novelcrafter** | ⚠️ 无官方 MCP | 用本仓库 `设定/` `大纲/` `章节/` 替代；可选 [novelcrafter-mcp](https://github.com/deadshot465/novelcrafter-mcp) 实验客户端 |

### 言情/古风

| 工具 | 类型 | 作用 |
|---|---|---|
| **Obsidian** | MCP ✅ | 人物关系、时间线、番外笔记（vault → `vault/`） |
| **Ideogram** | MCP ✅ | 古风插画、场景氛围图 |
| **Sudowrite** | ⚠️ 无原生 MCP | 浏览器写作；或通过 [viaSocket Sudowrite MCP](https://viasocket.com/mcp/sudowrite) 自配 |

### 科幻硬核

| 工具 | 类型 | 作用 |
|---|---|---|
| **World Anvil** | MCP ✅ | 世界观、星图、年表、势力 |
| **arXiv** | MCP ✅ | 论文检索（硬科幻设定参考） |
| **Midjourney** | MCP ⚠️ 第三方代理 | 概念图；需 `ACEDATACLOUD_API_TOKEN` 或改用 Recraft |

### 儿童/绘本

| 工具 | 类型 | 作用 |
|---|---|---|
| **Recraft** | MCP ✅ | 绘本插图、角色一致性 |
| **Storybird** | ❌ 无 MCP | 网页排版；本仓库用 Markdown + Recraft 出图 |
| **baoyu-comic** | Skill ✅ | 知识漫画条漫流程 → `./工具/install-writing-skills.sh` |

### 悬疑/推理

| 工具 | 类型 | 作用 |
|---|---|---|
| **World Anvil** | MCP ✅ | 案件时间线、地图、人物档案 |
| **Lex** | MCP ✅ | 写作策略/禁忌/风格策略记忆 |
| **Acontext** | ⚠️ 自托管 | [memodb-io/Acontext](https://github.com/memodb-io/Acontext) Docker；可用 Lex+mem0 暂代 |

### 出版级长篇

| 工具 | 类型 | 作用 |
|---|---|---|
| **Lex** | MCP ✅ | 风格与修改策略持久化 |
| **mem0** | MCP ✅ | 跨卷人物与伏笔 |
| **Notion** | MCP ✅ | 出版进度、责编批注、章节状态 |
| **baoyu-translate** | Skill ✅ | 翻译/双语对照 → `./工具/install-writing-skills.sh` |

---

## 环境变量

复制仓库根目录 `.env.mcp.example` → `.env.mcp`，填入密钥后：

```bash
set -a && source .env.mcp && set +a
```

或在 `~/.cursor/.env` 中配置（Cursor 全局可读）。

---

## 首次安装

```bash
# 1. 选题材
./工具/switch-mcp-profile.sh wangwen-xuanhuan-dushi

# 2. 配置密钥
cp .env.mcp.example .env.mcp
# 编辑 .env.mcp

# 3. 安装 Skill（按需）
./工具/install-writing-skills.sh comic      # 儿童/绘本
./工具/install-writing-skills.sh translate  # 出版长篇
./工具/install-writing-skills.sh all

# 4. 言情题材：初始化 Obsidian vault
mkdir -p vault

# 5. 出版/悬疑：初始化 Lex（可选）
npx @smartergpt/lex init
```

---

## Cursor 限制

- 全部 MCP 工具合计约 **40 个**上限；按题材只启用对应 profile，不要全开。
- 项目级配置：`.cursor/mcp.json`（可提交，不含密钥）
- 个人密钥：`~/.cursor/mcp.json` 或环境变量 `${env:KEY}`

---

## 与仓库目录的配合

| 目录 | 配合工具 |
|---|---|
| `设定/` `大纲/` | mem0、Lex、World Anvil |
| `章节/` | mem0（已写内容记忆） |
| `vault/` | Obsidian MCP |
| `素材/` | Tavily 检索结果归档 |
| Notion 数据库 | 出版进度（外部同步） |
