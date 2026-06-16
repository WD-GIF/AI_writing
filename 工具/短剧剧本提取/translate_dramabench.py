#!/usr/bin/env python3
"""
把 DramaBench 500 个英文 Fountain 剧本翻译成中文 Markdown 剧本

输入：素材/范文库/短剧资源/DramaBench真实剧本_英文/dramabench_continuation_500.jsonl
输出：素材/范文库/短剧资源/DramaBench中文剧本/

策略：
- 场景标题(INT./EXT./DAY/NIGHT)用规则映射
- 角色名 ALL_CAPS 行保留原文 + 简单音译
- 括号注释 (V.O.) 等用规则映射
- 动作描述、对白由 opus-mt 模型翻译
- 行级 batch 翻译加速

依赖：transformers, sentencepiece, sacremoses
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import List, Tuple


# 场景类型映射
INT_EXT_MAP = {
    "INT.": "内景",
    "EXT.": "外景",
    "INT./EXT.": "内/外景",
    "I/E.": "内/外景",
}

# 时间映射
TIME_MAP = {
    "DAY": "日",
    "NIGHT": "夜",
    "MORNING": "晨",
    "EVENING": "傍晚",
    "AFTERNOON": "午后",
    "DAWN": "黎明",
    "DUSK": "黄昏",
    "LATER": "稍后",
    "CONTINUOUS": "连续",
    "MOMENTS LATER": "片刻后",
    "SAME": "同一时间",
    "FLASHBACK": "闪回",
    "PRESENT DAY": "现在",
}

# 角色注释（括号内的） - 比如 (V.O.), (O.S.), (CONT'D)
PAREN_MAP = {
    "V.O.": "画外音",
    "O.S.": "场外",
    "O.C.": "镜头外",
    "CONT'D": "续",
    "BEAT": "停顿",
    "PAUSE": "停顿",
    "SOFTLY": "轻声",
    "WHISPERING": "低语",
    "SHOUTING": "大喊",
    "CRYING": "哭泣",
    "LAUGHING": "笑",
    "ANGRY": "愤怒",
    "ANGRILY": "愤怒地",
    "QUIETLY": "安静地",
    "COLDLY": "冷冷地",
    "WARMLY": "温暖地",
    "SARCASTIC": "讽刺",
    "SARCASTICALLY": "讽刺地",
    "CALMLY": "冷静地",
    "FURIOUSLY": "怒火中烧",
    "DESPERATE": "绝望",
    "DESPERATELY": "绝望地",
    "FRIGHTENED": "惊恐",
    "TERRIFIED": "极度恐惧",
    "TEARFULLY": "含泪地",
    "TREMBLING": "颤抖",
    "SMILING": "微笑",
    "GRINNING": "咧嘴笑",
    "MOCKINGLY": "嘲弄地",
    "CONTEMPTUOUS": "轻蔑",
    "AGONIZED": "痛苦",
    "STERNLY": "严厉地",
    "GENTLY": "温柔地",
    "EXCITED": "兴奋",
    "EXCITEDLY": "兴奋地",
    "SARCASTIC": "讽刺",
    "SURPRISED": "吃惊",
    "CONFUSED": "困惑",
    "HESITANT": "犹豫",
    "HESITANTLY": "犹豫地",
    "MUTTERING": "嘟囔",
    "UNDER HER BREATH": "压低声音",
    "UNDER HIS BREATH": "压低声音",
    "READING": "读",
    "REPEATED": "重复",
    "ON THE PHONE": "电话中",
    "INTO PHONE": "对着电话",
    "ON PHONE": "电话中",
    "TO HERSELF": "自言自语",
    "TO HIMSELF": "自言自语",
}

# 整行 fountain 标记
TRANSITION_MAP = {
    "FADE IN:": "淡入：",
    "FADE OUT:": "淡出：",
    "FADE OUT.": "淡出。",
    "FADE TO:": "淡入到：",
    "FADE TO BLACK.": "淡出黑场。",
    "FADE TO BLACK:": "淡出黑场：",
    "CUT TO:": "切至：",
    "CUT TO BLACK.": "切到黑场。",
    "SMASH CUT TO:": "急切至：",
    "MATCH CUT TO:": "匹配切至：",
    "DISSOLVE TO:": "溶解至：",
    "BACK TO SCENE.": "回到本场景。",
    "END.": "完。",
    "THE END.": "全剧终。",
}


# 英文人名 → 中文常见姓氏映射
SURNAME_MAP = {
    # 高频姓氏（DramaBench 短剧常见）
    "SONG": "宋", "LIU": "刘", "WANG": "王", "LI": "李", "ZHANG": "张",
    "CHEN": "陈", "YANG": "杨", "ZHAO": "赵", "WU": "吴", "ZHOU": "周",
    "XU": "徐", "SUN": "孙", "MA": "马", "ZHU": "朱", "HU": "胡",
    "GUO": "郭", "HE": "何", "GAO": "高", "LIN": "林", "LUO": "罗",
    "ZHENG": "郑", "LIANG": "梁", "XIE": "谢", "SHEN": "沈", "HAN": "韩",
    "TANG": "唐", "FENG": "冯", "CAO": "曹", "PENG": "彭", "ZENG": "曾",
    "XIAO": "肖", "TIAN": "田", "DONG": "董", "DENG": "邓", "PAN": "潘",
    "YUAN": "袁", "JIANG": "蒋", "CAI": "蔡", "YU": "余", "FAN": "范",
    "FANG": "方", "SHI": "石", "YAO": "姚", "TAN": "谭", "LU": "陆",
    "GU": "顾", "FU": "傅", "QIN": "秦", "DU": "杜", "MENG": "孟",
    "BAI": "白", "CHENG": "程", "QIAN": "钱", "JIA": "贾", "WEI": "魏",
    "XIA": "夏", "QIU": "邱", "XIONG": "熊", "WEN": "温", "PEI": "裴",
    "REN": "任", "JIAO": "焦", "LING": "凌", "MENG": "蒙", "QI": "齐",
    "MU": "穆", "BAO": "鲍", "NIE": "聂", "GE": "葛", "OUYANG": "欧阳",
    "SIMA": "司马",
    # 头衔
    "MR.": "先生", "MRS.": "夫人", "MS.": "女士", "DR.": "博士",
    "MR": "先生", "MRS": "夫人", "MS": "女士", "DR": "博士",
}

# 人名常用单字（中文短剧角色）
GIVEN_NAME_MAP = {
    "YUAN": "媛", "XIYUE": "夕悦", "QING": "清", "JING": "静", "YING": "颖",
    "YUE": "玥", "MEI": "美", "LING": "凌", "LAN": "兰", "JUAN": "娟",
    "HUA": "华", "FANG": "芳", "MIN": "敏", "WEI": "薇", "MENG": "梦",
    "XIN": "馨", "RUO": "若", "NUO": "诺", "QIN": "琴", "YAN": "妍",
    "RUI": "瑞", "WEN": "雯", "ZHEN": "珍", "BAO": "宝", "FU": "福",
    "PING": "萍", "XIA": "霞", "HONG": "红", "BING": "冰", "XUAN": "萱",
    "TING": "婷", "TIAN": "甜", "QIAO": "巧", "LI": "丽", "LIN": "琳",
    "ANG": "昂", "AO": "傲", "BIN": "斌", "BO": "博", "CHAO": "超",
    "CHENG": "成", "DA": "达", "FAN": "凡", "FEI": "飞", "GANG": "刚",
    "HAO": "浩", "HUI": "辉", "JIE": "杰", "JIANG": "江", "JUN": "俊",
    "KAI": "凯", "KE": "可", "LEI": "磊", "LIANG": "亮", "LONG": "龙",
    "MING": "明", "NING": "宁", "PENG": "鹏", "PING": "平", "QIANG": "强",
    "RUI": "睿", "SHENG": "盛", "TAO": "涛", "WEI": "伟", "XIANG": "翔",
    "XIN": "鑫", "YANG": "阳", "YI": "毅", "YONG": "勇", "ZE": "泽",
    "ZHAN": "展", "ZHE": "哲", "ZHEN": "震", "ZHI": "志", "ZHOU": "舟",
}

CHARACTER_NAME_CACHE: dict = {}


def translate_character_name(name: str) -> str:
    """把 ALL CAPS 角色名翻译成中文（基于姓+名字典）"""
    name_clean = name.strip()
    if name_clean in CHARACTER_NAME_CACHE:
        return CHARACTER_NAME_CACHE[name_clean]
    parts = name_clean.split()
    if not parts:
        return name_clean
    # 头衔（MR. / MRS.）
    titles = ["MR.", "MRS.", "MS.", "DR.", "MR", "MRS", "MS", "DR"]
    title = ""
    if parts[0].upper() in titles:
        title = SURNAME_MAP.get(parts[0].upper(), parts[0])
        parts = parts[1:]
    if not parts:
        return title or name_clean
    surname = SURNAME_MAP.get(parts[0].upper(), parts[0].capitalize())
    given = ""
    for p in parts[1:]:
        given += GIVEN_NAME_MAP.get(p.upper(), p.capitalize())
    if title:
        # MR. SONG → 宋先生 (调换)
        if title in ["先生", "夫人", "女士", "博士"]:
            result = f"{surname}{title}"
        else:
            result = f"{title}{surname}{given}"
    else:
        result = f"{surname}{given}"
    CHARACTER_NAME_CACHE[name_clean] = result
    return result


# -------- 行分类 --------

SCENE_HEAD_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|I/E\.|INT\.\\EXT\.)\s*(.+?)\s*-\s*(.+?)\s*$", re.IGNORECASE)
SCENE_HEAD_LOOSE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|I/E\.)\s*(.+)$", re.IGNORECASE)
ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9 \-\.\'#]+$")
PAREN_RE = re.compile(r"^\((.+)\)$")
TRANSITION_RE = re.compile(r"^\s*([A-Z][A-Z\.\: ]+)\s*$")


def classify_line(line: str) -> str:
    s = line.rstrip()
    if not s.strip():
        return "blank"
    stripped = s.strip()
    # 跳过元数据行（jsonl context 字段开头会重复一次）
    if stripped.startswith("Title:") or stripped.startswith("Description:"):
        return "meta"
    if stripped in TRANSITION_MAP:
        return "transition"
    if SCENE_HEAD_RE.match(s) or SCENE_HEAD_LOOSE_RE.match(s):
        return "scene"
    if PAREN_RE.match(stripped):
        return "paren"
    # 全大写短行 → 角色名（允许含点：MR. SONG, MRS. WANG）
    if ALL_CAPS_RE.match(stripped) and len(stripped) < 50 and not any(p in stripped for p in ("?", "!", ",")):
        # 排除场景标记
        if stripped not in TRANSITION_MAP:
            # 排除 "FADE IN:" 等
            return "character"
    return "text"


def parse_scene_parts(line: str) -> Tuple[str, str, str]:
    """解析场景标题，返回 (prefix_zh, location_en, time_zh_or_en)"""
    line = line.strip()
    m = SCENE_HEAD_RE.match(line)
    if m:
        prefix, loc, time = m.groups()
        prefix_zh = INT_EXT_MAP.get(prefix.upper(), prefix)
        time_zh = TIME_MAP.get(time.strip().upper(), time.strip())
        return prefix_zh, loc.strip(), time_zh
    m = SCENE_HEAD_LOOSE_RE.match(line)
    if m:
        prefix, rest = m.groups()
        prefix_zh = INT_EXT_MAP.get(prefix.upper(), prefix)
        return prefix_zh, rest.strip(), ""
    return "", line, ""


# 常见场景位置翻译（避免 MT 调用）
LOCATION_MAP = {
    "BEDROOM": "卧室", "LIVING ROOM": "客厅", "KITCHEN": "厨房",
    "BATHROOM": "浴室", "OFFICE": "办公室", "STUDY": "书房",
    "DINING ROOM": "餐厅", "HALLWAY": "走廊", "CORRIDOR": "走廊",
    "STAIRS": "楼梯", "BALCONY": "阳台", "GARAGE": "车库",
    "HOUSE": "房屋", "MANSION": "豪宅", "APARTMENT": "公寓",
    "HOTEL": "酒店", "HOTEL ROOM": "酒店客房",
    "HOTEL LOBBY": "酒店大堂", "RESTAURANT": "餐厅", "CAFE": "咖啡馆",
    "BAR": "酒吧", "CLUB": "俱乐部", "NIGHTCLUB": "夜总会",
    "SCHOOL": "学校", "CLASSROOM": "教室", "UNIVERSITY": "大学",
    "HOSPITAL": "医院", "HOSPITAL ROOM": "病房", "WARD": "病房",
    "ICU": "重症监护室", "EMERGENCY ROOM": "急诊室",
    "PRISON": "监狱", "PRISON CELL": "牢房", "JAIL": "监狱",
    "POLICE STATION": "警察局", "COURTROOM": "法庭", "COURT": "法庭",
    "STREET": "街道", "ALLEY": "小巷", "PARK": "公园",
    "GARDEN": "花园", "BEACH": "海滩", "FOREST": "森林",
    "CAR": "车内", "CAR INTERIOR": "车内", "VEHICLE": "车内",
    "BUS": "公交车", "TRAIN": "火车", "TAXI": "出租车",
    "AIRPORT": "机场", "TRAIN STATION": "火车站", "BUS STOP": "公交站",
    "WEDDING HALL": "婚礼现场", "CHURCH": "教堂", "TEMPLE": "寺庙",
    "CONFERENCE ROOM": "会议室", "BOARDROOM": "董事会议室",
    "MEETING ROOM": "会议室", "LOBBY": "大堂", "ELEVATOR": "电梯",
    "CEO OFFICE": "CEO 办公室", "COMPANY": "公司",
    "WAREHOUSE": "仓库", "FACTORY": "工厂",
    "MALL": "商场", "SHOP": "商店", "STORE": "商店",
    "GROCERY STORE": "超市", "SUPERMARKET": "超市",
    "POLICE CAR": "警车", "AMBULANCE": "救护车",
    "ROOF": "屋顶", "ROOFTOP": "屋顶",
    "BACKSEAT": "后座", "BACK SEAT": "后座",
    "FRONT SEAT": "前座",
    "BEDROOM - YUAN'S": "媛的卧室",
    "LIVING ROOM - SONG MANSION": "宋家客厅",
    "SONG FAMILY MANSION": "宋家大宅",
    "OFFICE - DAY": "办公室 - 日",
    "OFFICE BUILDING": "办公楼",
    "STREET - DAY": "街道 - 日",
    "CAR WASH": "洗车场",
    "BATHROOM STALL": "卫生间隔间",
    "GU FAMILY HOME": "顾家",
    "WANG MANSION": "王家大宅",
    "ZHANG MANSION": "张家大宅",
    "LI MANSION": "李家大宅",
    "CHEN MANSION": "陈家大宅",
    "LIU MANSION": "刘家大宅",
}


def translate_location_rule(loc: str) -> Tuple[str, bool]:
    """规则尝试翻译位置；返回 (zh, success)"""
    loc_up = loc.upper().strip()
    if loc_up in LOCATION_MAP:
        return LOCATION_MAP[loc_up], True
    # 尝试拆分： "BEDROOM - YUAN'S" → "BEDROOM" + "YUAN'S"
    if " - " in loc_up:
        parts = [p.strip() for p in loc_up.split(" - ")]
        translated = []
        all_ok = True
        for p in parts:
            if p in LOCATION_MAP:
                translated.append(LOCATION_MAP[p])
            elif p in TIME_MAP:
                translated.append(TIME_MAP[p])
            else:
                translated.append(p)
                all_ok = False
        return " - ".join(translated), all_ok
    return loc, False


def translate_paren_known(line: str) -> Tuple[str, bool]:
    """如果所有部分都在规则映射里，返回 (中文, True)；否则 (原文, False)"""
    stripped = line.strip()
    m = PAREN_RE.match(stripped)
    if not m:
        return line, True
    inside = m.group(1).strip()
    parts = re.split(r"[,/、，]", inside)
    translated = []
    all_mapped = True
    for p in parts:
        p = p.strip()
        up = p.upper()
        if up in PAREN_MAP:
            translated.append(PAREN_MAP[up])
        else:
            all_mapped = False
            break
    if all_mapped:
        return "（" + "、".join(translated) + "）", True
    return inside, False


def translate_transition(line: str) -> str:
    s = line.strip()
    return TRANSITION_MAP.get(s, s)


# -------- 翻译模型 --------

_MODEL = None
_TOK = None


def get_model():
    global _MODEL, _TOK
    if _MODEL is None:
        from transformers import MarianMTModel, MarianTokenizer
        name = "Helsinki-NLP/opus-mt-en-zh"
        _TOK = MarianTokenizer.from_pretrained(name)
        _MODEL = MarianMTModel.from_pretrained(name)
    return _MODEL, _TOK


def batch_translate(texts: List[str], batch_size: int = 16) -> List[str]:
    if not texts:
        return []
    model, tok = get_model()
    results = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        inputs = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=384)
        out = model.generate(
            **inputs, max_length=384, num_beams=2,
            no_repeat_ngram_size=3, repetition_penalty=1.3,
        )
        results.extend(tok.batch_decode(out, skip_special_tokens=True))
    return results


# -------- 角色名缓存（来自整本剧本） --------

def collect_characters(text: str) -> List[str]:
    """从剧本中收集所有 ALL_CAPS 角色名"""
    chars = set()
    for line in text.split("\n"):
        kind = classify_line(line)
        if kind == "character":
            # 去掉 (CONT'D) 这种
            base = re.sub(r"\s*\(.+?\)\s*$", "", line.strip())
            chars.add(base)
    return sorted(chars)


# -------- 主翻译流程 --------

def translate_script(title: str, description: str, script_text: str) -> str:
    """翻译一整个 Fountain 剧本（context + continuation 合并后的文本）
    返回中文 Markdown 格式剧本
    """
    lines = script_text.split("\n")
    classified = [(line, classify_line(line)) for line in lines]
    
    # 收集所有角色，建立标准译名映射
    all_chars = collect_characters(script_text)
    char_map = {c: translate_character_name(c) for c in all_chars}
    
    # 占位符方案：每个角色名分配一个 ZnameNZz 占位符
    # MT 会完美保留这种占位符，翻译后替换回标准中文译名
    placeholder_map = {}  # 英文全名 → "Zname{N}Zz"
    reverse_map = {}      # "Zname{N}Zz" → 中文标准译名
    # 按长度降序排，先匹配更长的（如 "SONG YUAN" 优先于 "SONG"）
    sorted_chars = sorted(all_chars, key=lambda x: -len(x))
    for n, en in enumerate(sorted_chars):
        ph = f"Zname{n+1}Zz"
        placeholder_map[en] = ph
        reverse_map[ph] = char_map[en]
    
    def apply_placeholders(text: str) -> str:
        for en, ph in placeholder_map.items():
            pat = re.compile(r"\b" + re.escape(en) + r"\b")
            text = pat.sub(ph, text)
        return text
    
    def restore_placeholders(text: str) -> str:
        for ph, zh in reverse_map.items():
            text = text.replace(ph, zh)
        return text
    
    # ====== Pass 1: 收集所有需要 MT 翻译的行 ======
    to_translate_idx = []
    to_translate_txt = []
    paren_need_mt = []  # (idx, paren_text)
    scene_loc_need_mt = []  # (idx, loc_text)
    for i, (line, kind) in enumerate(classified):
        stripped = line.strip()
        if kind == "text" and stripped:
            to_translate_idx.append(i)
            # 用占位符替换人名后再丢给 MT
            to_translate_txt.append(apply_placeholders(stripped))
        elif kind == "paren" and stripped:
            zh, mapped = translate_paren_known(stripped)
            if not mapped:
                paren_need_mt.append((i, apply_placeholders(zh)))
        elif kind == "scene":
            _, loc, _ = parse_scene_parts(stripped)
            loc_zh, ok = translate_location_rule(loc)
            if not ok:
                scene_loc_need_mt.append((i, apply_placeholders(loc)))
    
    paren_idx = [p[0] for p in paren_need_mt]
    paren_txt = [p[1] for p in paren_need_mt]
    scene_idx = [p[0] for p in scene_loc_need_mt]
    scene_txt = [p[1] for p in scene_loc_need_mt]
    
    all_idx = to_translate_idx + paren_idx + scene_idx
    all_txt = to_translate_txt + paren_txt + scene_txt
    translations = batch_translate(all_txt, batch_size=16)
    # 翻译后还原占位符
    translations = [restore_placeholders(t) for t in translations]
    trans_map = dict(zip(all_idx, translations))
    paren_idx_set = set(paren_idx)
    scene_idx_set = set(scene_idx)
    scene_loc_trans = dict(zip(scene_idx, translations[len(to_translate_idx) + len(paren_idx):]))
    
    # ====== Pass 2: 后处理人名修正 ======
    # 简单做法：把模型音译的姓+名替换回标准译名
    # 对每个角色，列出可能的变体（姓 + 各种音译）
    # 例: SONG YUAN 标准译"宋媛"，可能变体"宋勇/宋元/宋远/宋圆"等
    # 简单方法：基于姓氏匹配，把"宋X"统一成标准译名
    
    # 构建：标准姓 → 同姓所有角色的标准译名（按出现频率/长度排序）
    by_surname_zh = {}  # "宋" → [(英文全名, 中文标准译名), ...]
    for en, zh in char_map.items():
        if len(zh) >= 1:
            surname_zh = zh[0]
            by_surname_zh.setdefault(surname_zh, []).append((en, zh))
    
    # 对每个姓，如果只有一个角色，可以激进替换；多个角色不替换（容易错）
    name_replacements = {}  # 模型音译形式 → 标准译名
    for en, zh in char_map.items():
        # 把 EN 的首字（拼音音译可能） 替换成标准译名
        # 比较保守：直接保留 MT 输出
        pass
    
    # 简单后处理：扫描句首/句末单独的"X夫人/X先生"，统一为标准译名
    # 这步可以省略，让 MT 输出保持原样
    
    # ====== Pass 3: 组装结果 ======
    out_lines = []
    out_lines.append(f"# 《{title}》")
    out_lines.append("")
    
    if description:
        desc_zh = restore_placeholders(batch_translate([apply_placeholders(description)])[0])
        out_lines.append(f"> **剧情简介**: {desc_zh}")
        out_lines.append("")
    
    if char_map:
        out_lines.append("## 角色表")
        out_lines.append("")
        for en in sorted(char_map):
            out_lines.append(f"- **{char_map[en]}**（{en}）")
        out_lines.append("")
    
    out_lines.append("---")
    out_lines.append("")
    
    last_kind = None
    for i, (line, kind) in enumerate(classified):
        if kind == "blank":
            if last_kind not in ("blank", None):
                out_lines.append("")
            last_kind = "blank"
            continue
        if kind == "meta":
            # 跳过元数据（已在 markdown header 里展示）
            continue
        if kind == "scene":
            prefix_zh, loc_en, time_zh = parse_scene_parts(line)
            # location 翻译：先规则，规则不行用 MT
            loc_zh, ok = translate_location_rule(loc_en)
            if not ok and i in scene_loc_trans:
                loc_zh = scene_loc_trans[i]
            scene_text = f"{prefix_zh}．{loc_zh}"
            if time_zh:
                scene_text += f" - {time_zh}"
            out_lines.append("")
            out_lines.append(f"### 🎬 {scene_text}")
            out_lines.append("")
        elif kind == "transition":
            out_lines.append(f"_{translate_transition(line)}_")
            out_lines.append("")
        elif kind == "character":
            base = re.sub(r"(\s*)\((.+?)\)(\s*)$", "", line.strip())
            paren = re.search(r"\((.+?)\)\s*$", line.strip())
            zh_name = char_map.get(base, translate_character_name(base))
            if paren:
                paren_in = paren.group(1).strip()
                paren_zh = PAREN_MAP.get(paren_in.upper(), paren_in)
                out_lines.append(f"**{zh_name}** （{paren_zh}）")
            else:
                out_lines.append(f"**{zh_name}**")
        elif kind == "paren":
            if i in paren_idx_set:
                tr = trans_map.get(i, line.strip())
                out_lines.append(f"_（{tr}）_")
            else:
                zh, _ = translate_paren_known(line.strip())
                out_lines.append(f"_{zh}_")
        elif kind == "text":
            tr = trans_map.get(i, line.strip())
            out_lines.append(tr)
        last_kind = kind
    
    return "\n".join(out_lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="素材/范文库/短剧资源/DramaBench真实剧本_英文/dramabench_continuation_500.jsonl")
    parser.add_argument("--out-dir", default="素材/范文库/短剧资源/DramaBench中文剧本")
    parser.add_argument("--limit", type=int, default=None, help="只翻译前 N 个（测试用）")
    parser.add_argument("--start", type=int, default=0, help="从第几个开始")
    args = parser.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    with open(inp, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            records.append(json.loads(line))
    print(f"📚 加载 {len(records)} 个剧本")

    end = min(len(records), args.start + args.limit) if args.limit else len(records)
    todo = records[args.start:end]

    # 预热模型
    print("加载翻译模型...")
    t0 = time.time()
    get_model()
    print(f"加载耗时: {time.time()-t0:.1f}s")

    success = 0
    fail = 0
    total = len(todo)
    t_start = time.time()
    for i, rec in enumerate(todo):
        rid = rec["id"]
        title = rec.get("title", rid)
        desc = rec.get("description", "")
        ctx = rec.get("context", "")
        cont = rec.get("continuation", "")
        # 合并 context + continuation
        full_text = ctx
        if cont:
            full_text += "\n\n" + cont
        
        out_file = out_dir / f"{rid}_{title.replace('/', '_').replace(' ', '_')[:80]}.md"
        if out_file.exists():
            success += 1
            continue
        try:
            t0 = time.time()
            zh = translate_script(title, desc, full_text)
            out_file.write_text(zh, encoding="utf-8")
            elapsed = time.time() - t0
            elapsed_total = time.time() - t_start
            eta = (elapsed_total / (i + 1)) * (total - i - 1)
            success += 1
            print(f"  [{i+1:3d}/{total}] {rid} 《{title[:40]}》 {elapsed:.1f}s (ETA {eta/60:.1f}min)")
        except Exception as e:
            fail += 1
            print(f"  [{i+1:3d}/{total}] {rid} ❌ {e}")
    
    print(f"\n✅ 完成 {success}/{total} (失败 {fail})")
    print(f"总耗时: {(time.time()-t_start)/60:.1f} 分钟")


if __name__ == "__main__":
    main()
