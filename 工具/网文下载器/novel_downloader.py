#!/usr/bin/env python3
"""
爆文批量下载工具 v1
=================

适用站点：
- 笔趣阁系列（biquge / bqg / xbiquge 等）—— 全本小说
- 微信公众号文章（mp.weixin.qq.com）—— 单篇爽文
- 知乎专栏文章（zhuanlan.zhihu.com）—— 单篇
- 通用网页（兜底）

使用前安装依赖：
    pip install requests beautifulsoup4 lxml html2text tqdm

使用示例：

    # 下载单本笔趣阁小说（输入小说目录页 URL）
    python novel_downloader.py --url "https://www.xbiquge.so/book/12345/"
    
    # 下载单篇公众号文章
    python novel_downloader.py --url "https://mp.weixin.qq.com/s/xxxx"
    
    # 批量下载（urls.txt 一行一个 URL，# 开头是注释）
    python novel_downloader.py --batch urls.txt
    
    # 批量下载并按字数筛选（只保留 8000-12000 字的短篇）
    python novel_downloader.py --batch urls.txt --min 8000 --max 12000
    
    # 指定输出目录
    python novel_downloader.py --batch urls.txt --out 我的范文库

⚠️ 仅供个人学习研究使用，不要二次传播、不要商用、不要批量抓取大站VIP内容。
"""

import argparse
import os
import re
import sys
import time
import random
from pathlib import Path
from urllib.parse import urlparse, urljoin
from typing import Optional, List, Dict, Tuple

# ----------------------------------------------------------------
# 依赖检查
# ----------------------------------------------------------------
try:
    import requests
    from bs4 import BeautifulSoup
    import html2text
    from tqdm import tqdm
except ImportError as e:
    print(f"❌ 缺少依赖：{e.name}")
    print("\n请先运行以下命令安装：\n")
    print("    pip install requests beautifulsoup4 lxml html2text tqdm\n")
    sys.exit(1)


# ----------------------------------------------------------------
# 全局配置
# ----------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

DELAY_RANGE = (1.0, 2.5)  # 章节间随机延迟（秒），降低被封风险

DEFAULT_OUTPUT_DIR = Path("素材/范文库")


# ----------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------
def get_headers() -> Dict:
    """返回随机 User-Agent 的请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def random_delay():
    """章节间随机延迟"""
    time.sleep(random.uniform(*DELAY_RANGE))


def safe_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    name = re.sub(r'[<>:"/\\|?*\n\r\t\0]', '_', name)
    name = name.strip()[:80]
    return name or "untitled"


def count_chinese_chars(text: str) -> int:
    """统计中文字数"""
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def fetch_url(url: str, timeout: int = 30, retries: int = 3) -> Optional[str]:
    """安全抓取页面，自动重试 + 编码检测"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=get_headers(), timeout=timeout)
            response.raise_for_status()
            # 优先使用 response 推断的编码，对老站友好
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except requests.RequestException as e:
            if attempt < retries - 1:
                wait = 2 ** attempt + random.uniform(0, 1)
                print(f"  ⚠️ 第 {attempt+1} 次失败，{wait:.1f}s 后重试: {e}")
                time.sleep(wait)
            else:
                print(f"  ❌ 抓取失败 {url}: {e}")
    return None


# ============================================================
# 解析器 1：笔趣阁系列（通用，覆盖多数同类站点）
# ============================================================
class BiqugeParser:
    """笔趣阁/笔趣阁clone的通用解析器"""

    # 章节列表的常见 selector（按命中率排）
    CHAPTER_LIST_SELECTORS = [
        '#list dl dd a',
        '.listmain dl dd a',
        '#chapterlist a',
        '.list-chapter a',
        '.zjlist dd a',
        '.book-list a',
        '.chapter-list a',
        'div.box_con div#list a',
    ]

    # 章节正文的常见 selector
    CONTENT_SELECTORS = [
        '#content',
        '#chaptercontent',
        '.content',
        '#booktext',
        '.read-content',
        '.bookcontent',
        '.txt',
    ]

    def __init__(self, base_url: str):
        parsed = urlparse(base_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

    def parse_book_info(self, html: str) -> Dict:
        """解析书籍标题、作者"""
        soup = BeautifulSoup(html, 'lxml')

        # 标题
        title = None
        for sel in ['meta[property="og:novel:book_name"]', 'meta[property="og:title"]',
                    '#info h1', '.info h1', '#bookinfo h1', 'h1']:
            el = soup.select_one(sel)
            if el:
                title = el.get('content') if el.name == 'meta' else el.get_text(strip=True)
                if title:
                    break

        # 作者
        author = None
        for sel in ['meta[property="og:novel:author"]', '#info p:first-of-type', '.author']:
            el = soup.select_one(sel)
            if el:
                author = el.get('content') if el.name == 'meta' else el.get_text(strip=True)
                if author:
                    author = re.sub(r'^(作\s*者[:：\s]*)', '', author).strip()
                    break

        return {
            'title': title or 'unknown',
            'author': author or 'unknown',
        }

    def parse_chapter_list(self, html: str, base_url: str) -> List[Tuple[str, str]]:
        """解析章节列表，返回 [(标题, URL), ...]"""
        soup = BeautifulSoup(html, 'lxml')

        for selector in self.CHAPTER_LIST_SELECTORS:
            elements = soup.select(selector)
            # 过滤掉"最新章节"那种重复 block（通常出现在前几个）
            valid = [el for el in elements if el.get('href') and el.get_text(strip=True)]
            if len(valid) > 5:  # 至少有几章才算找到了
                chapters = []
                seen = set()
                for el in valid:
                    href = urljoin(base_url, el['href'])
                    title = el.get_text(strip=True)
                    if href not in seen:
                        chapters.append((title, href))
                        seen.add(href)
                return chapters

        return []

    def parse_chapter_content(self, html: str) -> Tuple[str, str]:
        """解析单章内容"""
        soup = BeautifulSoup(html, 'lxml')

        # 标题
        title = ''
        for sel in ['.bookname h1', 'h1', '.title']:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break

        # 正文
        content = ''
        for sel in self.CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                # 移除噪音
                for noise in el.select('script, style, .adsbygoogle, .ad, ins'):
                    noise.decompose()
                content = el.get_text('\n', strip=True)
                if len(content) > 100:  # 至少 100 字才算真正抓到了
                    break

        # 清理常见广告/导航文字
        if content:
            cleanup_patterns = [
                r'请记住本站[^\n]*',
                r'本章未完[^\n]*',
                r'<<\s*上一[页章][^\n]*',
                r'下一[页章]\s*>>[^\n]*',
                r'添加书签[^\n]*',
                r'加入书架[^\n]*',
                r'最快更新[^\n]*',
                r'手机阅读[^\n]*',
                r'笔趣阁[^\n]*',
                r'www\.[a-z0-9]+\.[a-z]+[^\n]*',
            ]
            for pattern in cleanup_patterns:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            content = re.sub(r'\n{3,}', '\n\n', content).strip()

        return title, content

    def download_book(self, book_url: str, output_dir: Path) -> Optional[Path]:
        """下载完整一本书"""
        print(f"\n📖 抓取目录页: {book_url}")
        toc_html = fetch_url(book_url)
        if not toc_html:
            return None

        book_info = self.parse_book_info(toc_html)
        chapters = self.parse_chapter_list(toc_html, book_url)

        if not chapters:
            print("  ❌ 未找到章节列表（可能站点结构特殊）")
            return None

        title = safe_filename(book_info['title'])
        author = book_info['author']
        print(f"  📚 《{title}》作者: {author}，共 {len(chapters)} 章")

        # 输出文件
        out_file = output_dir / f"{title}.txt"

        # 逐章下载
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"《{book_info['title']}》\n")
            f.write(f"作者: {author}\n")
            f.write(f"来源: {book_url}\n")
            f.write(f"章节数: {len(chapters)}\n")
            f.write("=" * 50 + "\n\n")

            success_count = 0
            with tqdm(chapters, desc=f"  下载《{title}》", unit="章") as pbar:
                for idx, (ch_title, ch_url) in enumerate(pbar, 1):
                    ch_html = fetch_url(ch_url)
                    if not ch_html:
                        continue

                    parsed_title, content = self.parse_chapter_content(ch_html)
                    if not content:
                        continue

                    final_title = parsed_title or ch_title
                    f.write(f"\n\n第 {idx} 章 {final_title}\n\n")
                    f.write(content)
                    f.flush()
                    success_count += 1

                    random_delay()

        # 统计
        with open(out_file, 'r', encoding='utf-8') as f:
            total_text = f.read()
        word_count = count_chinese_chars(total_text)
        print(f"  ✅ 完成：{out_file.name}（成功 {success_count}/{len(chapters)} 章，共 {word_count} 字）")

        return out_file


# ============================================================
# 解析器 2：微信公众号文章
# ============================================================
class WechatParser:
    """微信公众号文章解析器"""

    def parse(self, url: str) -> Optional[Dict]:
        html = fetch_url(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # 标题
        title = 'unknown'
        title_el = soup.select_one('#activity-name') or soup.select_one('h1')
        if title_el:
            title = title_el.get_text(strip=True)

        # 作者
        author = 'unknown'
        author_el = soup.select_one('#js_name')
        if author_el:
            author = author_el.get_text(strip=True)

        # 正文
        content_el = soup.select_one('#js_content') or soup.select_one('.rich_media_content')
        if not content_el:
            print("  ❌ 未找到正文（可能链接已失效或被屏蔽）")
            return None

        # 转 Markdown
        h = html2text.HTML2Text()
        h.ignore_images = True
        h.ignore_links = True
        h.body_width = 0
        h.unicode_snob = True
        content = h.handle(str(content_el))

        # 清理多余空行
        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        return {
            'title': title,
            'author': author,
            'content': content,
            'url': url,
        }

    def download(self, url: str, output_dir: Path) -> Optional[Path]:
        article = self.parse(url)
        if not article:
            return None

        title = safe_filename(article['title'])
        word_count = count_chinese_chars(article['content'])

        out_file = output_dir / f"{title}.md"
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"# {article['title']}\n\n")
            f.write(f"> **作者**: {article['author']}\n")
            f.write(f"> **字数**: {word_count}\n")
            f.write(f"> **来源**: {article['url']}\n\n")
            f.write("---\n\n")
            f.write(article['content'])

        print(f"  ✅ 公众号文章: {out_file.name}（{word_count} 字）")
        return out_file


# ============================================================
# 解析器 3：通用网页（兜底）
# ============================================================
class GenericParser:
    """通用网页正文提取（用于知乎专栏 / 自定义博客等）"""

    NOISE_SELECTORS = [
        'script', 'style', 'nav', 'header', 'footer', 'aside',
        '.ad', '.advertisement', '.ads', '#header', '#footer',
        '.comment', '.comments', '.related', '.sidebar',
    ]

    CONTENT_SELECTORS = [
        'article',
        '.article-content',
        '.RichText',  # 知乎
        '.content-inner',
        '#content',
        '.post-content',
        '.entry-content',
        'main',
    ]

    def parse(self, url: str) -> Optional[Dict]:
        html = fetch_url(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # 移除噪音
        for sel in self.NOISE_SELECTORS:
            for el in soup.select(sel):
                el.decompose()

        # 标题
        title = 'unknown'
        for sel in ['h1.Post-Title', '.Post-Title', 'h1', 'title']:  # 知乎专栏标题在第一个
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                if title and title != 'unknown':
                    break

        # 正文
        content = ''
        for sel in self.CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                content = el.get_text('\n', strip=True)
                if len(content) > 200:
                    break

        # 兜底：拼接所有较长 p 标签
        if not content or len(content) < 200:
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')
                          if len(p.get_text(strip=True)) > 30]
            content = '\n\n'.join(paragraphs)

        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if not content:
            print("  ❌ 未提取到正文")
            return None

        return {
            'title': title,
            'content': content,
            'url': url,
        }

    def download(self, url: str, output_dir: Path) -> Optional[Path]:
        article = self.parse(url)
        if not article:
            return None

        title = safe_filename(article['title'])
        word_count = count_chinese_chars(article['content'])

        out_file = output_dir / f"{title}.txt"
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(f"《{article['title']}》\n")
            f.write(f"来源: {article['url']}\n")
            f.write(f"字数: {word_count}\n")
            f.write("=" * 50 + "\n\n")
            f.write(article['content'])

        print(f"  ✅ 通用网页: {out_file.name}（{word_count} 字）")
        return out_file


# ============================================================
# 主控制器
# ============================================================
def detect_site_type(url: str) -> str:
    """根据 URL 自动检测站点类型"""
    domain = urlparse(url).netloc.lower()

    if 'mp.weixin.qq.com' in domain:
        return 'wechat'
    if any(kw in domain for kw in ['biquge', 'bqg', 'xbiquge', 'biqu', '23us',
                                    'xs8', '52ks', 'biqumi', '0kshu']):
        return 'biquge'
    # 其他统一归为通用
    return 'generic'


def download_one(url: str, site_type: Optional[str], output_dir: Path) -> Optional[Path]:
    """下载单个 URL"""
    if not site_type:
        site_type = detect_site_type(url)

    print(f"\n🔍 [{site_type}] {url}")

    try:
        if site_type == 'wechat':
            return WechatParser().download(url, output_dir)
        elif site_type == 'biquge':
            return BiqugeParser(url).download_book(url, output_dir)
        else:
            return GenericParser().download(url, output_dir)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def filter_by_length(file_path: Path, min_chars: int, max_chars: int,
                     reject_dir: Path) -> bool:
    """按字数筛选，不在范围的移到 _筛除/"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            wc = count_chinese_chars(f.read())
    except Exception:
        return False

    if min_chars <= wc <= max_chars:
        return True

    reject_dir.mkdir(exist_ok=True)
    new_path = reject_dir / file_path.name
    file_path.rename(new_path)
    print(f"  ⚠️ 字数 {wc} 不在 [{min_chars}, {max_chars}]，移到 _筛除/")
    return False


def batch_download(urls_file: Path, min_chars: int, max_chars: int,
                   output_dir: Path, site_type: Optional[str] = None):
    """批量下载"""
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)

    if not urls:
        print("❌ urls 文件里没有有效 URL")
        return

    print(f"\n📋 共 {len(urls)} 个 URL，开始批量下载")
    print(f"📂 输出目录: {output_dir.absolute()}")
    if min_chars > 0 or max_chars < int(1e9):
        print(f"📏 字数筛选: [{min_chars}, {max_chars}]")
    print()

    results = []
    rejected = []

    for i, url in enumerate(urls, 1):
        print(f"\n────── [{i}/{len(urls)}] ──────")
        out_file = download_one(url, site_type, output_dir)

        if out_file and out_file.exists():
            if filter_by_length(out_file, min_chars, max_chars,
                                output_dir / "_筛除"):
                results.append(out_file)
            else:
                rejected.append(out_file)

        # URL 间额外延迟
        if i < len(urls):
            time.sleep(random.uniform(2, 5))

    # 总结
    print(f"\n{'='*50}")
    print(f"📊 下载完成：")
    print(f"  ✅ 通过筛选: {len(results)} 篇")
    print(f"  ⚠️ 被筛除: {len(rejected)} 篇")
    print(f"  ❌ 失败: {len(urls) - len(results) - len(rejected)} 篇")
    print(f"  📂 保存在: {output_dir.absolute()}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(
        description='爆文批量下载工具（笔趣阁/公众号/通用网页）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  下载单本笔趣阁小说：
    %(prog)s --url "https://www.xbiquge.so/book/12345/"
  
  下载单篇公众号文章：
    %(prog)s --url "https://mp.weixin.qq.com/s/xxxx"
  
  批量下载（urls.txt 一行一个）：
    %(prog)s --batch urls.txt
  
  批量下载并按字数筛选（8000-12000 字）：
    %(prog)s --batch urls.txt --min 8000 --max 12000

⚠️ 仅供个人学习用途，请遵守目标站点的使用条款。
        """
    )

    parser.add_argument('--url', help='单个 URL')
    parser.add_argument('--batch', help='批量 URL 列表文件（一行一个 URL）')
    parser.add_argument('--type', choices=['biquge', 'wechat', 'generic'],
                        help='强制指定站点类型（不指定则自动检测）')
    parser.add_argument('--min', type=int, default=0,
                        dest='min_chars', help='最小中文字数（默认 0）')
    parser.add_argument('--max', type=int, default=int(1e9),
                        dest='max_chars', help='最大中文字数（默认无限）')
    parser.add_argument('--out', default=str(DEFAULT_OUTPUT_DIR),
                        help=f'输出目录（默认: {DEFAULT_OUTPUT_DIR}）')

    args = parser.parse_args()

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.url:
        result = download_one(args.url, args.type, output_dir)
        if result and (args.min_chars > 0 or args.max_chars < int(1e9)):
            filter_by_length(result, args.min_chars, args.max_chars,
                             output_dir / "_筛除")
    elif args.batch:
        urls_file = Path(args.batch)
        if not urls_file.exists():
            print(f"❌ URL 列表文件不存在: {urls_file}")
            sys.exit(1)
        batch_download(urls_file, args.min_chars, args.max_chars, output_dir, args.type)
    else:
        parser.print_help()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
