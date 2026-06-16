#!/usr/bin/env python3
"""
对已生成的剧本补充：
1. 每个场景抽 1 张关键帧（保存到 _frames/ 子目录）
2. cnocr 识别画面烧屏字幕（与 Whisper 对照、提取动作描述）
3. 升级版剧本：场景标题 + 关键帧链接 + 烧屏文字 + Whisper 台词

使用：
    python3 add_visual.py --drama-dir 素材/范文库/河马剧本提取实验/末世骗签
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


_OCR = None


def get_ocr():
    global _OCR
    if _OCR is None:
        from cnocr import CnOcr
        _OCR = CnOcr()
    return _OCR


# 烧屏垃圾词过滤
_TRASH_PATTERNS = [
    "画面为AI制作", "AI制作", "请勿带入模仿", "请勿模仿",
    "AI", "VIP", "剧情", "完整版", "下集", "下一集",
    "kuaikaw", "扫码", "下载", "微信",
]


def is_trash(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 2:
        return True
    if any(p in t for p in _TRASH_PATTERNS):
        return True
    # 全英文/数字
    if not any("\u4e00" <= c <= "\u9fff" for c in t):
        return True
    return False


def extract_keyframe(mp4: Path, timestamp: float, out: Path) -> Optional[Path]:
    """抽指定时间的关键帧"""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-ss", f"{timestamp:.2f}", "-i", str(mp4),
        "-vframes", "1", "-q:v", "3", str(out),
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return out if out.exists() else None
    except subprocess.CalledProcessError:
        return None


def ocr_frame(img: Path) -> List[str]:
    ocr = get_ocr()
    try:
        result = ocr.ocr(str(img))
    except Exception:
        return []
    return [r["text"].strip() for r in result if not is_trash(r["text"])]


def parse_script(md_path: Path) -> dict:
    """解析已生成的剧本 md，提取场景边界 + 各段时间"""
    txt = md_path.read_text(encoding="utf-8")
    # 抓 `### 场景 N` 和后面第一个时间戳
    scenes = []
    cur_scene = None
    for line in txt.split("\n"):
        m_scene = re.match(r"^### 场景 (\d+)", line)
        m_time = re.match(r"^`(\d+\.\d+)`", line)
        if m_scene:
            cur_scene = {"no": int(m_scene.group(1)), "start_time": None, "first_text": ""}
            scenes.append(cur_scene)
        elif m_time and cur_scene and cur_scene["start_time"] is None:
            cur_scene["start_time"] = float(m_time.group(1))
            # 截一段文字
            rest = line[m_time.end():].strip()
            cur_scene["first_text"] = rest[:60]
    return {"scenes": scenes, "raw": txt}


def enhance_episode(
    md_path: Path,
    mp4_path: Path,
    frames_dir: Path,
    ep_no: int,
) -> str:
    """对一集剧本，抽关键帧 + OCR，输出增强版"""
    parsed = parse_script(md_path)
    scenes = parsed["scenes"]
    raw = parsed["raw"]
    if not scenes:
        return raw

    # 每个场景抽帧 + OCR
    annotations = {}  # scene_no → (frame_rel_path, ocr_texts)
    for sc in scenes:
        t = sc["start_time"] or 0.0
        # 抽场景开始后 1.5 秒处（避开切换瞬间的模糊帧）
        ts = max(0.5, t + 1.5)
        img_name = f"ep{ep_no:02d}_场景{sc['no']:02d}.jpg"
        img_path = frames_dir / img_name
        ok = extract_keyframe(mp4_path, ts, img_path)
        if not ok:
            continue
        ocr_texts = ocr_frame(img_path)
        # 去重并保留长度合理的
        ocr_texts = list(dict.fromkeys(t for t in ocr_texts if 2 <= len(t) <= 30))
        annotations[sc["no"]] = (f"_frames/{img_name}", ocr_texts)

    # 在剧本里每个场景标题后插入"画面 + OCR 字幕"块
    out_lines = []
    for line in raw.split("\n"):
        out_lines.append(line)
        m = re.match(r"^### 场景 (\d+)", line)
        if m:
            sc_no = int(m.group(1))
            if sc_no in annotations:
                frame_rel, ocr_texts = annotations[sc_no]
                out_lines.append("")
                out_lines.append(f"![场景{sc_no}画面]({frame_rel})")
                if ocr_texts:
                    out_lines.append("")
                    out_lines.append("> **烧屏字幕**: " + " ／ ".join(ocr_texts))

    return "\n".join(out_lines)


def enhance_drama(drama_dir: Path, video_dir: Path) -> None:
    drama_name = drama_dir.name
    frames_dir = drama_dir / "_frames"
    frames_dir.mkdir(exist_ok=True)

    print(f"\n=== 增强 《{drama_name}》 ===")
    eps = sorted(drama_dir.glob("第??集.md"))
    for ep_md in eps:
        m = re.match(r"第(\d+)集\.md", ep_md.name)
        if not m:
            continue
        ep_no = int(m.group(1))
        mp4 = video_dir / f"{drama_name}_ep{ep_no:02d}.mp4"
        if not mp4.exists():
            print(f"  [集{ep_no:02d}] ❌ 缺视频: {mp4}")
            continue
        print(f"  [集{ep_no:02d}] 增强中...", end=" ", flush=True)
        enhanced = enhance_episode(ep_md, mp4, frames_dir, ep_no)
        ep_md.write_text(enhanced, encoding="utf-8")
        # 统计该集 frames
        ep_frames = list(frames_dir.glob(f"ep{ep_no:02d}_*.jpg"))
        print(f"{len(ep_frames)} 帧 OCR完成")

    # 重新合并全集剧本
    full = []
    full.append(f"# 《{drama_name}》剧本（增强版：含画面+烧屏字幕）")
    full.append("")
    for ep_md in eps:
        full.append(ep_md.read_text(encoding="utf-8"))
        full.append("\n---\n")
    full_path = drama_dir / f"《{drama_name}》完整剧本.md"
    full_path.write_text("\n".join(full), encoding="utf-8")
    print(f"  ✅ 完整剧本已更新: {full_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drama-dir", required=True)
    parser.add_argument("--video-dir", default="/tmp/drama_videos")
    args = parser.parse_args()
    enhance_drama(Path(args.drama_dir), Path(args.video_dir))


if __name__ == "__main__":
    main()
