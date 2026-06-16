# 番茄字体密码本缓存

> 这里存放着**番茄小说的字体解密映射表**（俗称"密码本"）。
> 每个 woff2 字体文件对应一份密码本。

---

## 📖 什么是密码本

番茄小说用自定义字体加密正文：
```
浏览器看到："大乾皇朝，疆域亿万里"
爬虫抓到："[PUA字符]乾皇朝，疆域亿[PUA][PUA]" ← 看起来像汉字但其实全错
```

**密码本**就是 `PUA字符 → 真实汉字` 的对照表。

---

## 🔑 当前密码本

| 文件名 | 字体 hash | 字符数 | 生成日期 |
|---|---|---|---|
| `mapping_dc027189e0ba4cd.json` | `dc027189e0ba4cd` | 362 | 2026-06-16 |

格式：
```json
{
  "\uE3E8": "d",
  "\uE3E9": "在",
  "\uE3EA": "主",
  ...
}
```

---

## 🤖 自动生成原理

通过 `fanqie_decoder.py` 实现：

1. 抓取番茄页面 → 提取 `bytetos.com/obj/awesome-font/c/XXX.woff2` 字体 URL
2. 下载 woff2 字体文件
3. 用 fontTools 解析字体，提取 362 个 PUA glyph
4. 把每个 glyph 用 Pillow 渲染成 120x120 PNG
5. 用 ddddocr 自动识别 → 真实汉字
6. 保存映射表到这里

**实测准确率 97.2%+**（与 `tianhuoDD/fanqienovel-decryptor` 对比）

---

## 🔄 字体更新怎么办

番茄会**定期更新字体**（每隔几个月），新字体的 hash 会变（如 `dc027189e0ba4cd` → 新 hash）。

只要 `fanqie_decoder.py` 在运行，它会：
1. 自动检测到新字体 URL
2. 自动下载新字体
3. 自动 OCR 生成新密码本
4. 保存到这个文件夹

**用户不需要做任何事**——下次跑爬虫，新密码本自动出现在这里。

---

## ⚠️ 兼容性

- 字体 hash 不同的密码本**不能互通**——番茄每个字体都是独立的 PUA 编号方案
- 老密码本可以保留（万一以后番茄回滚到老字体能复用）

---

## 🎁 致谢

- **OCR 引擎**：[sml2h3/ddddocr](https://github.com/sml2h3/ddddocr)
- **字体解析**：[fonttools/fonttools](https://github.com/fonttools/fonttools)
- **解密思路启发**：[tianhuoDD/fanqienovel-decryptor](https://github.com/tianhuoDD/fanqienovel-decryptor)、[zhoulianglen/fanqiexiaoshuo-Download](https://github.com/zhoulianglen/fanqiexiaoshuo-Download)
