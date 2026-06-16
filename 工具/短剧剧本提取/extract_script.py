#!/usr/bin/env python3
"""
短剧视频 → 剧本提取流水线

输入：河马短剧（已知 bookId）
输出：剧本格式文本（Fountain 风格）：场景标记 + 旁白 + 对白 + 动作提示

步骤：
1. 拉河马详情 API 获取每集 mp4 URL
2. 下载 mp4
3. ffmpeg 抽音频 + 场景切换检测
4. faster-whisper 转录（中文）
5. 合并：scene cuts + subtitle segments → 剧本

依赖：requests, faster-whisper, ffmpeg
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import requests


HEMA_HEADERS = {
    "accept": "*/*",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/143.0.0.0",
    "referer": "https://www.kuaikaw.cn",
    "origin": "https://www.kuaikaw.cn",
    "content-type": "application/json",
    "pname": "www.kuaikaw.cn",
}


# -------- 河马 API --------

def fetch_drama_detail(book_id: str) -> dict:
    url = f"https://www.kuaikaw.cn/_next/data/hmjc_20251016/drama/{book_id}.json"
    r = requests.get(url, params={"bookId": book_id}, headers=HEMA_HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def list_playable_episodes(detail: dict) -> List[Tuple[int, str, dict]]:
    """返回 (ep_no, mp4_url, raw_chapter)"""
    chapters = detail["pageProps"].get("chapterList", []) or []
    out: List[Tuple[int, str, dict]] = []
    for i, ch in enumerate(chapters):
        cvv = ch.get("chapterVideoVo") or {}
        url = cvv.get("mp4720p") or cvv.get("mp4") or cvv.get("vodMp4Url")
        if url:
            ep_no = int(ch.get("chapterIndex") or (i + 1))
            out.append((ep_no, url, ch))
    return out


# -------- 下载 + 媒体处理 --------

def download(url: str, out: Path) -> Path:
    if out.exists() and out.stat().st_size > 1024:
        return out
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/143.0.0.0",
        "referer": "https://www.kuaikaw.cn",
    }
    with requests.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    return out


def download_with_refresh(url: str, out: Path, book_id: str, ep_no: int) -> Path:
    """下载失败时（如 URL 过期 403），重新拉 detail 拿最新 URL 重试"""
    try:
        return download(url, out)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (403, 410):
            print(f"      ⟲ URL 过期，重新拉详情...", end=" ", flush=True)
            detail = fetch_drama_detail(book_id)
            fresh = list_playable_episodes(detail)
            new_url = next((u for n, u, _ in fresh if n == ep_no), None)
            if new_url and new_url != url:
                return download(new_url, out)
        raise


def extract_audio(mp4: Path, wav: Path) -> Path:
    if wav.exists() and wav.stat().st_size > 1024:
        return wav
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp4), "-vn", "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", str(wav)],
        capture_output=True, check=True,
    )
    return wav


def detect_scene_cuts(mp4: Path, threshold: float = 0.3) -> List[float]:
    cmd = ["ffmpeg", "-i", str(mp4), "-vf",
           f"select=gt(scene\\,{threshold}),showinfo", "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    cuts: List[float] = []
    for line in res.stderr.split("\n"):
        if "pts_time:" in line and "showinfo" in line:
            m = re.search(r"pts_time:([\d.]+)", line)
            if m:
                cuts.append(float(m.group(1)))
    return cuts


def get_duration(mp4: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(mp4)],
        capture_output=True, text=True,
    )
    return float(json.loads(res.stdout)["format"]["duration"])


# -------- Whisper 转写 --------

_WHISPER_MODEL = None


def get_whisper(model_size: str = "small"):
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def transcribe(wav: Path, model_size: str = "small",
               min_segments: int = 5) -> List[Dict]:
    """先用 VAD 转一次；若段数过少（BGM 过响场景），关掉 VAD 再试一次。"""
    model = get_whisper(model_size)
    segments, _ = model.transcribe(
        str(wav), language="zh", beam_size=5, vad_filter=True,
        initial_prompt="这是一部中文短剧的台词。",
    )
    result = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    if len(result) < min_segments:
        # 退化：关掉 VAD，更鲁棒
        segments, _ = model.transcribe(
            str(wav), language="zh", beam_size=5, vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt="这是一部中文短剧的台词。",
        )
        result_no_vad = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
        if len(result_no_vad) > len(result):
            return result_no_vad
    return result


# -------- 剧本组装 --------

_QUOTE_CHARS = "！？!?"
_PRONOUN_HEAD = re.compile(r"^[我他她我们他们]")
_ADDRESS_WORDS = ["阿", "宝贝", "爸", "妈", "哎", "喂", "嗯", "好的", "对不起", "求求"]


def classify_line(text: str) -> str:
    """启发式区分旁白/对白
    短剧大部分都是第一人称旁白驱动，对白只在关键节点冒头。
    返回："旁白" / "对白"
    """
    if not text:
        return "对白"
    t = text.strip()
    # 强对白：直接称呼别人 + 感叹/疑问
    if any(a in t for a in _ADDRESS_WORDS) and any(p in t for p in _QUOTE_CHARS):
        return "对白"
    # 标点结尾带"！？!?"且没有"我"开头 → 对白
    if _PRONOUN_HEAD.match(t):
        return "旁白"
    if any(p in t for p in _QUOTE_CHARS):
        return "对白"
    # 短句（≤10字）且没有"我/他/她"开头，可能是对白
    if len(t) <= 10 and not _PRONOUN_HEAD.match(t):
        return "对白"
    return "旁白"


def merge_narration(segments: List[Dict], gap_threshold: float = 1.5) -> List[Dict]:
    """合并连续旁白：相邻间隔小于阈值 + 同类型，合成一段"""
    if not segments:
        return []
    merged: List[Dict] = []
    for seg in segments:
        seg = dict(seg)
        seg["kind"] = classify_line(seg["text"])
        if not merged:
            merged.append(seg)
            continue
        prev = merged[-1]
        gap = seg["start"] - prev["end"]
        if (
            prev["kind"] == seg["kind"] == "旁白"
            and gap <= gap_threshold
            and len(prev["text"]) + len(seg["text"]) < 80
        ):
            prev["text"] = prev["text"].rstrip("，。 ") + "，" + seg["text"]
            prev["end"] = seg["end"]
        else:
            merged.append(seg)
    return merged


def build_script(
    ep_no: int,
    ep_title: str,
    duration: float,
    scene_cuts: List[float],
    segments: List[Dict],
) -> str:
    """组合成剧本"""
    lines = []
    lines.append(f"# 第{ep_no:02d}集 · {ep_title}")
    lines.append("")
    lines.append(
        f"> 时长 {duration:.1f}s · 镜头切换 {len(scene_cuts)} 处 · 台词 {len(segments)} 段"
    )
    lines.append("")

    merged = merge_narration(segments)

    last_cut_time = -10.0
    scene_no = 1
    lines.append(f"### 场景 {scene_no}")
    lines.append("")

    for seg in merged:
        s = seg["start"]
        # 跨过场景切换点
        crossed = [c for c in scene_cuts if last_cut_time < c <= s]
        if crossed:
            # 只在距上次场景标记 ≥ 4 秒时算"大场景跳跃"
            if crossed[-1] - last_cut_time >= 4.0 and crossed[-1] > 5.0:
                scene_no += 1
                lines.append("")
                lines.append(f"### 场景 {scene_no}")
                lines.append("")
            last_cut_time = crossed[-1]

        kind = seg["kind"]
        ts = f"`{seg['start']:05.1f}`"
        text = seg["text"].strip()
        if kind == "对白":
            lines.append(f"{ts} **「{text}」**")
        else:
            lines.append(f"{ts} {text}")
        lines.append("")

    return "\n".join(lines) + "\n"


# -------- 主流程 --------

def extract_drama_to_script(
    book_id: str,
    book_name: str,
    out_dir: Path,
    introduction: str = "",
    actor: str = "",
    actress: str = "",
    max_episodes: Optional[int] = None,
    model_size: str = "small",
    video_dir: Optional[Path] = None,
) -> Path:
    """主入口：把一部剧的可下载集全提取成剧本"""
    out_dir.mkdir(parents=True, exist_ok=True)
    video_dir = video_dir or (out_dir / "_videos")
    video_dir.mkdir(parents=True, exist_ok=True)

    detail = fetch_drama_detail(book_id)
    playable = list_playable_episodes(detail)
    if max_episodes:
        playable = playable[:max_episodes]
    if not playable:
        raise RuntimeError("没有可下载的集")

    print(f"\n=== 《{book_name}》 ===")
    print(f"  可下载: {len(playable)} 集")

    # 主剧本文件（汇总）
    full_lines = []
    full_lines.append(f"# 《{book_name}》剧本")
    full_lines.append("")
    full_lines.append(f"> **来源**: 河马短剧 (kuaikaw.cn, bookId={book_id})")
    full_lines.append(f"> **演员**: {actor or '?'} / {actress or '?'}")
    full_lines.append(f"> **本剧本基于 Whisper small 模型自动转录 + ffmpeg 镜头切换检测**")
    full_lines.append(f"> ⚠️ 仅含免费放出集数（一般 5 集）")
    full_lines.append("")

    if introduction:
        full_lines.append(f"## 剧情简介")
        full_lines.append("")
        full_lines.append(f"> {introduction}")
        full_lines.append("")

    full_lines.append("---")
    full_lines.append("")

    for ep_no, url, ch in playable:
        ep_title = ch.get("chapterName") or f"第{ep_no}集"
        print(f"\n  [集{ep_no:02d}] {ep_title}")

        mp4 = video_dir / f"{book_name}_ep{ep_no:02d}.mp4"
        wav = video_dir / f"{book_name}_ep{ep_no:02d}.wav"

        # 1. 下载
        print(f"    📥 下载...", end=" ", flush=True)
        t0 = time.time()
        try:
            download_with_refresh(url, mp4, book_id, ep_no)
            print(f"{mp4.stat().st_size // 1024} KB ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"❌ {e}")
            continue

        # 2. 抽音频
        print(f"    🎵 抽音频...", end=" ", flush=True)
        t0 = time.time()
        try:
            extract_audio(mp4, wav)
            print(f"OK ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"❌ {e}")
            continue

        # 3. 场景切换
        print(f"    🎬 镜头切换检测...", end=" ", flush=True)
        t0 = time.time()
        scene_cuts = detect_scene_cuts(mp4)
        dur = get_duration(mp4)
        print(f"{len(scene_cuts)} 处 ({time.time()-t0:.1f}s)")

        # 4. 转写
        print(f"    📝 Whisper 转写...", end=" ", flush=True)
        t0 = time.time()
        segs = transcribe(wav, model_size=model_size)
        print(f"{len(segs)} 段 ({time.time()-t0:.1f}s)")

        # 5. 组装
        script = build_script(ep_no, ep_title, dur, scene_cuts, segs)

        # 单集保存
        ep_path = out_dir / f"第{ep_no:02d}集.md"
        ep_path.write_text(script, encoding="utf-8")

        full_lines.append(script)
        full_lines.append("")
        full_lines.append("---")
        full_lines.append("")

    # 主剧本保存
    full_path = out_dir / f"《{book_name}》完整剧本.md"
    full_path.write_text("\n".join(full_lines), encoding="utf-8")
    print(f"\n✅ 完整剧本: {full_path}")
    return full_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--book-name", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--introduction", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--actress", default="")
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--model-size", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--video-dir", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    video_dir = Path(args.video_dir) if args.video_dir else None
    extract_drama_to_script(
        book_id=args.book_id,
        book_name=args.book_name,
        out_dir=out_dir,
        introduction=args.introduction,
        actor=args.actor,
        actress=args.actress,
        max_episodes=args.max_episodes,
        model_size=args.model_size,
        video_dir=video_dir,
    )


if __name__ == "__main__":
    main()
