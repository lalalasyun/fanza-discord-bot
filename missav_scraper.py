"""
MissAV検索・スクレイピングモジュール
タイトル検索から動画URLを取得する機能を提供
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MISSAV_BASE_URL = "https://missav123.com"
CACHE_DURATION = 0  # キャッシュを無効化


class MissAVScraper:
    def __init__(self):
        self.cache = {}
        self.cache_timestamp = {}

    async def search_videos(self, title: str) -> List[Dict[str, any]]:
        """タイトルで動画を検索"""
        # キャッシュチェック
        cache_key = f"search_{title.lower()}"
        if cache_key in self.cache_timestamp:
            if datetime.now() - self.cache_timestamp[cache_key] < timedelta(seconds=CACHE_DURATION):
                logger.info(f"Returning cached search results for: {title}")
                return self.cache[cache_key]

        # 検索実行
        search_url = f"{MISSAV_BASE_URL}/ja/search/{quote(title)}"
        videos = await self.scrape_search_results(search_url, title)
        
        # キャッシュに保存
        if videos:
            self.cache[cache_key] = videos
            self.cache_timestamp[cache_key] = datetime.now()
        
        return videos

    async def scrape_search_results(self, search_url: str, title: str) -> List[Dict[str, any]]:
        """検索結果ページをスクレイピング"""
        videos = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = await browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                logger.info(f"Searching MissAV for: {title}")
                logger.info(f"Search URL: {search_url}")
                
                await page.goto(search_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                # 検索結果の動画要素を取得（MissAVの実際の構造に基づく）
                video_elements = await page.query_selector_all("div.grid.grid-cols-2 > div")
                
                if not video_elements:
                    # フォールバック用の他のセレクタ
                    fallback_selectors = [
                        "div[class*='grid'] > div",
                        ".thumbnail.group",
                        "div.thumbnail"
                    ]
                    
                    for selector in fallback_selectors:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            video_elements = elements
                            logger.info(f"Found {len(elements)} elements with fallback selector: {selector}")
                            break
                else:
                    logger.info(f"Found {len(video_elements)} videos with main selector")
                
                if not video_elements:
                    logger.warning("No video elements found")
                    await browser.close()
                    return videos
                
                # 各動画の情報を取得（最大20件）
                for element in video_elements[:20]:
                    try:
                        video_info = await self.extract_video_info(element)
                        if video_info and self.is_relevant_video(video_info['title'], title):
                            videos.append(video_info)
                            logger.info(f"Added video: {video_info['title'][:50]}...")
                        
                    except Exception as e:
                        logger.error(f"Error extracting video info: {e}")
                        continue
                
                await browser.close()
                
                # 関連性でソート（タイトルの類似度）
                videos.sort(key=lambda x: self.calculate_relevance(x['title'], title), reverse=True)
                
                logger.info(f"Successfully found {len(videos)} relevant videos")
                
        except Exception as e:
            logger.error(f"MissAV scraping error: {e}")
        
        return videos

    async def extract_video_info(self, element) -> Optional[Dict[str, any]]:
        """動画要素から情報を抽出"""
        try:
            # タイトル（MissAVの実際の構造に基づく）
            title = ""
            
            # MissAVでは `.text-secondary` クラスのa要素にタイトルが含まれる
            title_elem = await element.query_selector("a.text-secondary")
            if title_elem:
                title = await title_elem.text_content()
            
            # フォールバック
            if not title:
                title_selectors = [
                    "a[alt]",
                    "img[alt]",
                    "a[title]",
                    "a"
                ]
                
                for selector in title_selectors:
                    elem = await element.query_selector(selector)
                    if elem:
                        title = await elem.get_attribute('alt')
                        if not title:
                            title = await elem.get_attribute('title')
                        if not title:
                            title = await elem.text_content()
                        
                        if title:
                            title = title.strip()
                            break
            
            if not title or title == "":
                logger.debug("No title found for element")
                return None
            
            # 動画URL
            video_url = ""
            link_elem = await element.query_selector("a[href*='/']")
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    if href.startswith('/'):
                        video_url = f"{MISSAV_BASE_URL}{href}"
                    elif not href.startswith('http'):
                        video_url = f"{MISSAV_BASE_URL}/{href}"
                    else:
                        video_url = href
            
            # サムネイル画像
            thumbnail_url = ""
            img_elem = await element.query_selector("img[src]")
            if img_elem:
                src = await img_elem.get_attribute('src')
                if src and ('jpg' in src or 'png' in src or 'webp' in src):
                    if src.startswith('//'):
                        thumbnail_url = f"https:{src}"
                    elif src.startswith('/'):
                        thumbnail_url = f"{MISSAV_BASE_URL}{src}"
                    elif src.startswith('http'):
                        thumbnail_url = src
            
            # data-src属性もチェック
            if not thumbnail_url:
                img_elem = await element.query_selector("img[data-src]")
                if img_elem:
                    src = await img_elem.get_attribute('data-src')
                    if src and ('jpg' in src or 'png' in src or 'webp' in src):
                        if src.startswith('//'):
                            thumbnail_url = f"https:{src}"
                        elif src.startswith('/'):
                            thumbnail_url = f"{MISSAV_BASE_URL}{src}"
                        elif src.startswith('http'):
                            thumbnail_url = src
            
            # 時間（右下のspan要素）
            duration = ""
            duration_elem = await element.query_selector("span.absolute.bottom-1.right-1")
            if duration_elem:
                duration_text = await duration_elem.text_content()
                if duration_text and ':' in duration_text:
                    duration = duration_text.strip()
            
            return {
                'title': title.strip(),
                'url': video_url,
                'thumbnail': thumbnail_url,
                'duration': duration,
                'source': 'MissAV'
            }
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None

    def is_relevant_video(self, video_title: str, search_title: str) -> bool:
        """動画が検索クエリと関連性があるかチェック"""
        if not video_title or not search_title:
            return False
        
        video_title_lower = video_title.lower()
        search_title_lower = search_title.lower()
        
        # 完全一致
        if search_title_lower in video_title_lower:
            return True
        
        # 単語レベルでの一致チェック
        search_words = re.findall(r'\w+', search_title_lower)
        video_words = re.findall(r'\w+', video_title_lower)
        
        if not search_words:
            return False
        
        # 検索語の50%以上が含まれているかチェック
        matches = sum(1 for word in search_words if word in video_words)
        relevance_score = matches / len(search_words)
        
        return relevance_score >= 0.5

    def calculate_relevance(self, video_title: str, search_title: str) -> float:
        """動画と検索クエリの関連性スコアを計算"""
        if not video_title or not search_title:
            return 0.0
        
        video_title_lower = video_title.lower()
        search_title_lower = search_title.lower()
        
        # 完全一致の場合は最高スコア
        if search_title_lower == video_title_lower:
            return 1.0
        
        # 部分一致の場合
        if search_title_lower in video_title_lower:
            return 0.8
        
        # 単語レベルでの類似度計算
        search_words = set(re.findall(r'\w+', search_title_lower))
        video_words = set(re.findall(r'\w+', video_title_lower))
        
        if not search_words:
            return 0.0
        
        intersection = search_words.intersection(video_words)
        union = search_words.union(video_words)
        
        # Jaccard係数
        jaccard = len(intersection) / len(union) if union else 0.0
        
        return jaccard

    async def get_video_direct_url(self, video_page_url: str) -> Optional[str]:
        """動画ページから直接再生URLを取得"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                context = await browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                logger.info(f"Getting direct URL from: {video_page_url}")
                
                await page.goto(video_page_url, wait_until='networkidle')
                await page.wait_for_timeout(5000)
                
                # 動画URLを探す
                video_selectors = [
                    "video source[src]",
                    "video[src]",
                    "source[src*='.mp4']",
                    "source[src*='.m3u8']"
                ]
                
                for selector in video_selectors:
                    video_elem = await page.query_selector(selector)
                    if video_elem:
                        src = await video_elem.get_attribute('src')
                        if src:
                            if src.startswith('//'):
                                return f"https:{src}"
                            elif src.startswith('/'):
                                return f"{MISSAV_BASE_URL}{src}"
                            elif src.startswith('http'):
                                return src
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Error getting direct video URL: {e}")
        
        return None