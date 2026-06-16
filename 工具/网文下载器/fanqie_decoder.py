#!/usr/bin/env python3
"""
番茄小说字体解密器 v1
=====================

破解番茄小说 PUA 字体加密的完整方案。

原理：
- 番茄用自定义 woff2 字体把常用汉字映射到 PUA 私有区（U+E000-U+F8FF）
- 字体里有 362 个 glyph，每次更新字体 glyph ID 会变
- 老映射表会失效，所以需要每次自动重建映射

方案：
1. 从页面提取字体 URL
2. 下载 woff2 字体
3. 把每个 glyph 渲染成图片
4. 用 ddddocr 自动识别
5. 生成 PUA → 真实汉字 的映射表（缓存到本地）
6. 用映射表替换正文里的 PUA 字符

依赖：
    pip install requests fonttools brotli Pillow ddddocr beautifulsoup4 lxml

使用：
    from fanqie_decoder import FanqieDecoder
    decoder = FanqieDecoder()
    
    # 解密一段抓取来的乱码文本
    decoded = decoder.decode_text(raw_text, font_url)
    
    # 或下载一本书
    decoder.download_book(book_url, output_dir='./output')
"""

import os
import re
import io
import json
import time
import random
import hashlib
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple, List

try:
    import requests
    from bs4 import BeautifulSoup
    from fontTools.ttLib import TTFont
    from PIL import Image, ImageDraw, ImageFont
    import ddddocr
except ImportError as e:
    print(f"❌ 缺少依赖: {e.name}")
    print("\n请运行: pip install requests fonttools brotli Pillow ddddocr beautifulsoup4 lxml\n")
    raise


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://fanqienovel.com/",
}

# 字体文件 URL 缓存路径
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "fanqie_decoder"
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class FanqieDecoder:
    """番茄小说字体解密器"""
    
    def __init__(self, cache_dir: Optional[Path] = None, verbose: bool = True):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self._ocr = None  # 懒加载
        self._mapping_cache: Dict[str, Dict[str, str]] = {}  # font_hash → mapping
    
    def log(self, msg):
        if self.verbose:
            print(msg)
    
    @property
    def ocr(self):
        """懒加载 OCR（首次使用时初始化）"""
        if self._ocr is None:
            self.log("⏳ 初始化 OCR ...")
            self._ocr = ddddocr.DdddOcr(beta=True, show_ad=False)
            self.log("✅ OCR 就绪")
        return self._ocr
    
    def fetch(self, url: str, binary: bool = False, retries: int = 3) -> Optional[bytes | str]:
        """安全抓取页面"""
        for attempt in range(retries):
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
                r.raise_for_status()
                if binary:
                    return r.content
                r.encoding = r.apparent_encoding or 'utf-8'
                return r.text
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt + random.uniform(0, 1))
                else:
                    self.log(f"❌ 抓取失败 {url}: {e}")
        return None
    
    def extract_font_url(self, html: str) -> Optional[str]:
        """从页面 HTML 提取番茄字体 URL"""
        # 番茄字体 URL 模式: lf*-awef.bytetos.com/obj/awesome-font/c/*.woff2
        matches = re.findall(
            r'(https?://[^/\s"\']+\.bytetos\.com/obj/awesome-font/[^/]+/[a-z0-9]+\.woff2)',
            html
        )
        if matches:
            return matches[0]
        return None
    
    def font_url_to_cache_key(self, font_url: str) -> str:
        """字体 URL → 缓存 key（hash 提取）"""
        # URL 里的字体 hash 通常类似 dc027189e0ba4cd.woff2
        match = re.search(r'/([a-z0-9]+)\.woff2?$', font_url)
        if match:
            return match.group(1)
        # 兜底：URL md5
        return hashlib.md5(font_url.encode()).hexdigest()[:16]
    
    def get_font_mapping(self, font_url: str) -> Dict[str, str]:
        """获取字体的 PUA → 真实字符 映射表（带缓存）"""
        cache_key = self.font_url_to_cache_key(font_url)
        
        # 内存缓存
        if cache_key in self._mapping_cache:
            return self._mapping_cache[cache_key]
        
        # 磁盘缓存
        cache_file = self.cache_dir / f"mapping_{cache_key}.json"
        if cache_file.exists():
            self.log(f"📦 从缓存加载映射: {cache_file.name}")
            with open(cache_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            self._mapping_cache[cache_key] = mapping
            return mapping
        
        # 现场生成
        self.log(f"🔧 生成新映射 ({cache_key}) ...")
        mapping = self._build_mapping(font_url, cache_key)
        
        # 缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        self.log(f"💾 缓存到: {cache_file}")
        
        self._mapping_cache[cache_key] = mapping
        return mapping
    
    def _build_mapping(self, font_url: str, cache_key: str) -> Dict[str, str]:
        """下载字体 + OCR 识别 → 构建 PUA → 字符 映射"""
        # 下载字体
        woff_path = self.cache_dir / f"font_{cache_key}.woff2"
        ttf_path = self.cache_dir / f"font_{cache_key}.ttf"
        
        if not woff_path.exists():
            self.log(f"⬇️  下载字体: {font_url}")
            data = self.fetch(font_url, binary=True)
            if not data:
                raise RuntimeError(f"无法下载字体: {font_url}")
            with open(woff_path, 'wb') as f:
                f.write(data)
        
        # 解析字体
        font = TTFont(str(woff_path))
        
        # 转 TTF 给 Pillow 用
        if not ttf_path.exists():
            font.flavor = None
            font.save(str(ttf_path))
        
        # 提取 PUA 字符
        cmap = font.getBestCmap()
        pua_chars = [(code, name) for code, name in cmap.items() 
                     if 0xE000 <= code <= 0xF8FF]
        self.log(f"  发现 {len(pua_chars)} 个 PUA 字符待识别")
        
        # OCR 识别每个字
        img_font = ImageFont.truetype(str(ttf_path), 80)
        mapping = {}
        
        for i, (code, glyph_name) in enumerate(pua_chars):
            char = chr(code)
            # 渲染成图片
            img = Image.new('RGB', (120, 120), color='white')
            draw = ImageDraw.Draw(img)
            try:
                bbox = draw.textbbox((0, 0), char, font=img_font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                draw.text((60-w//2-bbox[0], 60-h//2-bbox[1]), char, fill='black', font=img_font)
            except:
                continue
            
            # OCR
            img_buf = io.BytesIO()
            img.save(img_buf, format='PNG')
            img_buf.seek(0)
            try:
                result = self.ocr.classification(img_buf.read())
                recognized = result.strip()[:1] if result and result.strip() else None
                if recognized:
                    mapping[char] = recognized
            except Exception:
                pass
            
            if (i + 1) % 100 == 0:
                self.log(f"  ...{i+1}/{len(pua_chars)}")
        
        self.log(f"✅ 映射构建完成: {len(mapping)} 个有效字符")
        return mapping
    
    def decode_text(self, text: str, font_url: str) -> str:
        """用字体映射解密一段文本"""
        if not text or not font_url:
            return text
        
        mapping = self.get_font_mapping(font_url)
        return ''.join(mapping.get(c, c) for c in text)
    
    def parse_book_page(self, book_url: str) -> Optional[Dict]:
        """解析番茄书籍详情页，返回书名+章节列表"""
        html = self.fetch(book_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 标题
        title_el = soup.select_one('.info-name, h1.book-name')
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            # 从 <title> 备选
            title_meta = soup.find('title')
            if title_meta:
                title = re.sub(r'(完整版.*$|_番茄.*$)', '', title_meta.get_text(strip=True)).strip()
        
        # 作者
        author = "unknown"
        for el in soup.select('.author-name, .info-author'):
            text = el.get_text(strip=True)
            if text:
                author = text
                break
        
        # 章节列表
        chapters = []
        seen = set()
        for a in soup.find_all('a', href=re.compile(r'/reader/\d+')):
            href = a.get('href', '')
            ch_title = a.get_text(strip=True)
            full_url = urllib.parse.urljoin(book_url, href)
            if full_url not in seen and ch_title and not ch_title.startswith('最'):
                # 去掉"最近更新"那种
                chapters.append({'title': ch_title, 'url': full_url})
                seen.add(full_url)
        
        return {
            'title': title or 'unknown',
            'author': author,
            'chapters': chapters,
            'url': book_url,
        }
    
    def parse_chapter(self, chapter_url: str) -> Optional[Dict]:
        """解析单章正文（带解密）"""
        html = self.fetch(chapter_url)
        if not html:
            return None
        
        # 提取字体 URL
        font_url = self.extract_font_url(html)
        if not font_url:
            self.log(f"⚠️  未找到字体 URL: {chapter_url}")
        
        # 提取正文
        soup = BeautifulSoup(html, 'lxml')
        
        # 标题
        title_el = soup.select_one('.muye-reader-title, h1')
        title = title_el.get_text(strip=True) if title_el else ''
        
        # 正文容器
        content = ''
        for sel in ['.muye-reader-content', '.muye-reader', '[class*="reader-content"]']:
            el = soup.select_one(sel)
            if el:
                # 优先按段落抓取（保留排版）
                paragraphs = el.find_all('p')
                if paragraphs:
                    raw = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                else:
                    raw = el.get_text('\n', strip=True)
                
                if raw and font_url:
                    content = self.decode_text(raw, font_url)
                else:
                    content = raw
                break
        
        # 检查是否需付费
        if not content or '本章节已下架' in content or '请购买' in content:
            return None
        
        return {
            'title': title,
            'content': content,
            'url': chapter_url,
        }
    
    def download_book(self, book_url: str, output_dir: Path, delay: float = 1.0,
                       max_chapters: Optional[int] = None) -> Optional[Path]:
        """下载完整一本书（解密版）"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 抓书籍信息
        self.log(f"\n📖 抓取书籍: {book_url}")
        book = self.parse_book_page(book_url)
        if not book or not book['chapters']:
            self.log("❌ 未找到章节列表")
            return None
        
        title = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', book['title'])[:60]
        self.log(f"📚 《{title}》共 {len(book['chapters'])} 章")
        
        if max_chapters:
            book['chapters'] = book['chapters'][:max_chapters]
            self.log(f"   限制下载前 {max_chapters} 章")
        
        # 2. 输出文件
        out_file = output_dir / f"{title}.txt"
        success = 0
        skipped = 0
        
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"《{book['title']}》\n")
            f.write(f"作者: {book['author']}\n")
            f.write(f"来源: {book_url}\n")
            f.write(f"共 {len(book['chapters'])} 章\n")
            f.write("=" * 50 + "\n\n")
            
            for i, ch in enumerate(book['chapters'], 1):
                self.log(f"  [{i}/{len(book['chapters'])}] {ch['title'][:40]}", )
                
                chapter = self.parse_chapter(ch['url'])
                if not chapter:
                    self.log(f"     ⚠️ 跳过（可能付费/失败）")
                    skipped += 1
                    continue
                
                f.write(f"\n\n第 {i} 章 {chapter['title']}\n\n")
                f.write(chapter['content'])
                f.flush()
                success += 1
                
                time.sleep(delay + random.uniform(0, 0.5))
        
        # 3. 统计
        with open(out_file, 'r', encoding='utf-8') as f:
            full_text = f.read()
        chinese_count = sum(1 for c in full_text if '\u4e00' <= c <= '\u9fff')
        
        self.log(f"\n✅ 完成: {out_file}")
        self.log(f"   成功 {success} 章 / 跳过 {skipped} 章 / 总字数 {chinese_count}")
        
        return out_file


def main():
    import argparse
    parser = argparse.ArgumentParser(description='番茄小说下载器（带字体解密）')
    parser.add_argument('url', help='番茄小说 URL（书籍页或章节页）')
    parser.add_argument('-o', '--out', default='./output', help='输出目录')
    parser.add_argument('-d', '--delay', type=float, default=1.0, help='章节间延迟（秒）')
    parser.add_argument('-n', '--max', type=int, help='最多下载章节数')
    
    args = parser.parse_args()
    
    decoder = FanqieDecoder()
    
    # 自动识别 URL 类型
    if '/page/' in args.url:
        decoder.download_book(args.url, args.out, args.delay, args.max)
    elif '/reader/' in args.url:
        chapter = decoder.parse_chapter(args.url)
        if chapter:
            out_dir = Path(args.out)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{chapter['title'][:60]}.txt"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chapter['title']}\n\n")
                f.write(f"来源: {chapter['url']}\n\n")
                f.write(chapter['content'])
            print(f"✅ {out_file}")
    else:
        print("❌ 无法识别 URL 类型，应该包含 /page/ 或 /reader/")


if __name__ == '__main__':
    main()
