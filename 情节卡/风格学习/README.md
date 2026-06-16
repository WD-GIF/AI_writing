# 风格学习模块

> 这是让 AI 真正"学会"《蓉颜小厨》写法的核心工具集。
> AI 每次写《蓉颜小厨》前，必读本目录全部 3 个文件。

---

## 📚 文件

| 文件 | 作用 | 何时读 |
|---|---|---|
| **00-蓉颜小厨专用风格指令包.md** | 硬性指标 + 黑白名单 + 句式模板 | 写之前必读 |
| **01-检索使用指南.md** | 怎么找最相关的真实样本 | 写之前必读 |
| **_选中样本_15个.json** | 已检索好的 15 个最相关 DramaBench 剧本 | 写之前抽 1-3 个细读 |

---

## 🔄 完整工作流（每次写《蓉颜小厨》某节）

```
Step 1. 读情节卡 (情节卡/节卡/第NN节-XX.md)
        ↓
Step 2. 读涉及角色的人物卡 (人物库/角色XX-X.md)
        ↓
Step 3. 读风格指令包 (情节卡/风格学习/00-XX.md)
        ↓
Step 4. 检索 1-3 个最相关样本细读
        - 题材最近: script_5431 (丧女母亲复仇)
        - 重生爽文: script_3488 (重生女继承人复仇)  
        - 妯娌斗争: script_4481 (婚姻交换后姐妹后悔)
        ↓
Step 5. 写
        ↓
Step 6. 跑数值自查脚本
        ↓
Step 7. 不过关 → 重写
        过关 → 给你
```

---

## 🎯 已经做的

### v6 是第一次完整跑这套流水线的产物

**对比 v5**：

| 维度 | v5 | v6 |
|---|---|---|
| 开篇钩子 | 散文式叙述 | "他应该死。这一世，必须的。"（仿 script_5431） |
| 念念语言真实度 | 偏成熟（"豆豆是周家的根"） | 找词模式（"看到我就...就皱眉"） |
| 蓉蓉对白 | 无 | 微信原话+表情包（Type C 阴阳怪气） |
| 周文博炸怒 | 一长句 | 四短句分段 |
| 数值核查 | 凭感觉 | 脚本自动核查 |

### 自查脚本

跑：
```bash
cd /workspace && python3 -c "
import re
from pathlib import Path
txt = Path('蓉颜小厨/第01节-出租车后座的重生-v6.md').read_text(encoding='utf-8')
body = txt.split('## 📐')[0]
print('中文字数:', sum(1 for c in body if '\u4e00' <= c <= '\u9fff'))
"
```

更完整的自查脚本将在后续节中复用。

---

## 📊 当前指令包来源

从以下 15 部真实 DramaBench 剧本统计：

1. **script_5431** ⭐ 主参考: Revenge of a Grieving Mother (丧女母亲复仇)
2. script_0585: Revenge of the Betrayed General's Daughter  
3. script_0655: The Marquis Lady's Rebirth
4. script_2095: Million Dollar Bride
5. script_2308: The Devil by My Side
6. script_2605: A String, A Pillar, Remembering the Years
7. script_2612: A Dream Recalled
8. script_2633: Rebirth of the Villain Ex-Wife
9. script_2927: Temptation by Design (Episode 51)
10. script_3488: Reborn Heiress Seeks Revenge
11. script_3675: The Female Scholar
12. script_3773: Betrayal and Revenge
13. script_4481: After the Marriage Swap, My Sister Regrets Everything
14. script_5326: The Transmigrated Princess's Counterattack Strategy
15. script_5432: After My Husband Cheated, I Became a Matchmaker

统计指标：
- 总对白 290 句
- 总动作描述 340 句
- 总情绪标记 154 个
- 对白平均 15.4 字（中位数 12）

---

## 🔮 下一步建议

1. **第 1 节确认 v6 之后**：
   - 你标出 v6 里"哪些是人话 / 哪些是 AI 腔"
   - 我把你的标注**沉淀到风格指令包黑名单**
   - 这是 fine-tune 的替代方案

2. **写第 2 节之前**：
   - 重做一次检索（题材可能不一样：第 2 节是"妯娌发布会现场"）
   - 可能要新抽 3-5 个"豪门发布会/婆媳直面冲突"题材剧本

3. **写完全部 12 节之后**：
   - 风格指令包会迭代到 v3
   - 那时再回过头看，第 1 节会想重写

---

## 🚨 风险提示

| 风险 | 缓解 |
|---|---|
| 检索样本质量 | 只用 15 个最相关，不混入 485 个不相关 |
| 翻译质量损失 | 关键对白可对照 `DramaBench真实剧本_英文/单文件/` 看原文 |
| AI 仍可能"伪人" | 自查表 + 你的反馈循环是最终防线 |
| 风格指令包过拟合到 5431 | 写第 3 节前重做检索，引入新样本 |
