"""
Playwright版スクレイパー（Seleniumの代替案）
軽量で高速、Chrome/Chromiumのインストールが不要
高速化最適化済み
"""

import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext
from datetime import datetime, timedelta
import logging
import re
import hashlib
from typing import List, Dict, Optional
from config import USER_AGENT, FANZA_SALE_URL, MIN_RATING, MAX_ITEMS, CACHE_DURATION

logger = logging.getLogger(__name__)


class PlaywrightFanzaScraper:
    def __init__(self):
        self.cache = {}
        self.cache_timestamp = None
        self.cache_by_url = {}  # URL別の包括的キャッシュ
        self.cache_timestamp_by_url = {}  # URL別のタイムスタンプ
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None

    def parse_rating(self, rating_text: str) -> float:
        """評価テキストから数値を抽出"""
        try:
            match = re.search(r'[\d.]+', rating_text)
            if match:
                return float(match.group())
            return 0.0
        except:
            return 0.0

    def format_rating_stars(self, rating: float) -> str:
        """評価を星マークで表現"""
        full_stars = int(rating)
        half_star = 1 if rating - full_stars >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        
        return "★" * full_stars + "☆" * half_star + "☆" * empty_stars

    def _generate_cache_key(self, url: str) -> str:
        """URLベースの包括的なキャッシュキーを生成"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    async def _get_browser(self) -> Browser:
        """ブラウザインスタンスを取得（再利用）"""
        if self._browser is None or not self._browser.is_connected():
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--disable-images']
            )
        return self._browser
    
    async def _get_context(self) -> BrowserContext:
        """ブラウザコンテキストを取得（再利用）"""
        if self._context is None or self._context.browser != await self._get_browser():
            browser = await self._get_browser()
            self._context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
        return self._context
    
    async def close(self):
        """リソースをクリーンアップ"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def get_high_rated_products(self, url: str = None, max_items: Optional[int] = None, force_refresh: bool = False) -> List[Dict[str, any]]:
        """高評価商品を取得（キャッシュ機能付き）
        
        Args:
            url: スクレイピング対象のURL（省略時はデフォルトURL）
            max_items: 最大取得件数
            force_refresh: Trueの場合、キャッシュを無視して新規取得
        """
        # URLが指定されていない場合はデフォルトURL
        if not url:
            url = FANZA_SALE_URL
        
        # URLベースのキャッシュキーを生成
        cache_key = self._generate_cache_key(url)
        
        # force_refreshがFalseの場合のみキャッシュをチェック
        if not force_refresh:
            # キャッシュチェック
            if cache_key in self.cache_timestamp_by_url and cache_key in self.cache_by_url:
                if datetime.now() - self.cache_timestamp_by_url[cache_key] < timedelta(seconds=CACHE_DURATION):
                    logger.info(f"Returning cached data for URL: {url[:100]}...")
                    return self.cache_by_url[cache_key]
        else:
            logger.info(f"Force refresh enabled, bypassing cache for URL: {url[:100]}...")
        
        # 新規取得
        products = await self.scrape_products(url)
        if products:
            self.cache_by_url[cache_key] = products
            self.cache_timestamp_by_url[cache_key] = datetime.now()
            logger.info(f"Cached {len(products)} products for URL: {url[:100]}...")
        
        return products

    async def scrape_products(self, url: str) -> List[Dict[str, any]]:
        """実際のスクレイピング処理（高速化版）"""
        products = []
        
        try:
            # 再利用可能なブラウザコンテキストを取得
            context = await self._get_context()
            page = await context.new_page()
            
            try:
                # ページにアクセス
                logger.info(f"Accessing URL: {url}")
                await page.goto(url, wait_until='domcontentloaded')  # networkidleより高速
                
                # 年齢認証の処理
                try:
                    # 年齢認証ボタンを探す（タイムアウト短縮）
                    age_button = await page.query_selector("a:has-text('はい')")
                    if age_button:
                        await age_button.click()
                        logger.info("Age verification completed")
                        await page.wait_for_load_state('domcontentloaded')
                except:
                    pass
                
                # 商品リストの要素を直接待機（タイムアウト短縮）
                try:
                    await page.wait_for_selector("[data-e2eid='content-card']", timeout=10000)
                except:
                    logger.warning("Product selector not found within timeout")
                
                # 商品要素を探す（最初に見つかったセレクターを使用）
                product_selectors = [
                    "[data-e2eid='content-card']",
                    "div[data-e2eid='content-card']",
                    "article[data-e2eid='content-card']"
                ]
                
                product_elements = None
                for selector in product_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        product_elements = elements
                        logger.info(f"Found {len(elements)} products with selector: {selector}")
                        break
                
                if not product_elements:
                    logger.warning("No product elements found")
                    return products
                
                # 並列処理で商品情報を取得（最大100件まで確認）
                semaphore = asyncio.Semaphore(10)  # 同時処理数制限
                tasks = []
                
                async def process_element(element):
                    async with semaphore:
                        return await self._extract_product_info(element)
                
                # タスクを作成
                for element in product_elements[:100]:
                    tasks.append(process_element(element))
                
                # 並列実行
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 結果を処理
                for result in results:
                    if isinstance(result, dict) and result.get('title'):
                        product_rating = result.get('rating', 0)
                        logger.debug(f"Product: {result['title'][:30]}... Rating: {product_rating}")
                        
                        if product_rating >= MIN_RATING:
                            products.append(result)
                            logger.debug(f"Added product: {result['title'][:30]}... (Rating: {product_rating})")
                        elif product_rating > 0:
                            logger.debug(f"Product below threshold: {result['title'][:30]}... (Rating: {product_rating}, Min: {MIN_RATING})")
                        else:
                            logger.debug(f"Product with zero rating: {result['title'][:30]}...")
                
            finally:
                await page.close()
                
            # 評価順でソートして上位を返す
            products.sort(key=lambda x: x['rating'], reverse=True)
            products = products[:MAX_ITEMS]
            
            logger.info(f"Successfully scraped {len(products)} high-rated products")
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        return products
    
    async def _extract_product_info(self, element) -> Dict[str, any]:
        """商品要素から情報を抽出（並列処理用）"""
        try:
            # タイトル
            title = ""
            # まず画像のaltタグから取得を試みる
            title_img = await element.query_selector("a[href*='/detail/'] img")
            if title_img:
                title = await title_img.get_attribute('alt')
                if title:
                    title = title.strip()
            
            # altタグが空の場合は他のセレクターを試す
            if not title:
                title_selectors = [
                    "a[data-e2eid='title']",
                    "a[href*='/detail/']",
                    "span.hover\\:underline",
                    "a span.hover\\:underline"
                ]
                for selector in title_selectors:
                    title_elem = await element.query_selector(selector)
                    if title_elem:
                        title = await title_elem.text_content()
                        title = title.strip() if title else ""
                        if title:
                            break
            
            if not title:
                return {}
            
            # URL
            url = ""
            link_elem = await element.query_selector("a[data-e2eid='title']")
            if not link_elem:
                link_elem = await element.query_selector("a[href*='/detail/']")
            if link_elem:
                url = await link_elem.get_attribute('href')
                if url and not url.startswith('http'):
                    url = f"https://www.dmm.co.jp{url}"
            
            # 評価（星の画像の数をカウント - 複数のセレクターを試行）
            rating = 0.0
            star_selectors = [
                "img[src*='icon/star/yellow.svg']",  # 正確なセレクター
                "img[src*='star/yellow']",
                "img[src*='star'][alt='']",  # 空のaltタグの星画像
                "img[alt*='星']",
                "[class*='star']",
                "[data-rating]",
                ".star-rating img",
                "img[src*='rating']"
            ]
            
            for selector in star_selectors:
                star_images = await element.query_selector_all(selector)
                if star_images:
                    rating = len(star_images)
                    logger.debug(f"Found {rating} stars with selector: {selector}")
                    break
            
            # 代替手段：評価テキストから抽出
            if rating == 0.0:
                rating_selectors = [
                    "[class*='rating']",
                    "[class*='review']",
                    "span:has-text('★')",
                    "*:has-text('評価')"
                ]
                for selector in rating_selectors:
                    rating_elem = await element.query_selector(selector)
                    if rating_elem:
                        rating_text = await rating_elem.text_content()
                        if rating_text:
                            parsed_rating = self.parse_rating(rating_text)
                            if parsed_rating > 0:
                                rating = parsed_rating
                                logger.debug(f"Found rating {rating} from text: {rating_text}")
                                break
            
            # 評価が見つからない場合のデバッグ情報
            if rating == 0.0:
                logger.debug(f"No rating found for product: {title[:30]}...")
                # デバッグ用：要素の内部HTMLを出力
                try:
                    inner_html = await element.inner_html()
                    logger.debug(f"Element HTML preview: {inner_html[:500]}...")
                except:
                    pass
            
            # 価格
            price = "価格不明"
            price_elem = await element.query_selector("[data-e2eid='content-price']")
            if price_elem:
                price_text = await price_elem.text_content()
                if price_text and '円' in price_text:
                    price = price_text.strip()
            
            # 商品画像URL（最初の有効なものを使用）
            image_url = ""
            image_selectors = [
                "a[href*='/detail/'] img",  # 商品リンク内の画像
                "picture img",              # picture要素内の画像
                "img[loading='lazy']",      # 遅延読み込み画像
                "img[alt]"                  # altタグがある画像
            ]
            for selector in image_selectors:
                img_elem = await element.query_selector(selector)
                if img_elem:
                    image_url = await img_elem.get_attribute('src')
                    if image_url and ('awsimgsrc.dmm.co.jp' in image_url or 'pics.dmm.co.jp' in image_url):
                        # 高解像度版に変換
                        if 'ps.jpg' in image_url:
                            image_url = image_url.replace('ps.jpg', 'pl.jpg')
                        break
            
            # 女優名（優先順位付きセレクター）
            actresses = []
            actress_selectors = [
                "a[href*='?actress=']",
                "a.text-gray-500.hover\\:underline",
                "a[href*='/actress/']",
                "a[href*='actress_id=']"
            ]
            
            # 最初に見つかったセレクターのみ使用（パフォーマンス向上）
            for selector in actress_selectors:
                try:
                    actress_elems = await element.query_selector_all(selector)
                    if actress_elems:
                        for actress_elem in actress_elems[:3]:  # 最大3名まで
                            actress_name = await actress_elem.text_content()
                            actress_href = await actress_elem.get_attribute('href') or ""
                            if actress_name and actress_name.strip():
                                clean_name = actress_name.strip()
                                if (len(clean_name) > 1 and 
                                    clean_name not in ['詳細', '商品', '動画', 'サンプル', '画像', 'レビュー'] and
                                    not any(a['name'] == clean_name for a in actresses)):
                                    
                                    # Build full URL
                                    if actress_href.startswith('/'):
                                        actress_url = f"https://www.dmm.co.jp{actress_href}"
                                    else:
                                        actress_url = actress_href if actress_href.startswith('http') else f"https://www.dmm.co.jp/{actress_href}"
                                    
                                    actresses.append({
                                        'name': clean_name,
                                        'url': actress_url
                                    })
                        break  # 最初に成功したセレクターで完了
                except Exception:
                    continue
            
            return {
                'title': title[:50] + '...' if len(title) > 50 else title,
                'rating': rating,
                'price': price,
                'url': url,
                'image_url': image_url,
                'actresses': actresses
            }
            
        except Exception as e:
            logger.error(f"Error parsing product element: {e}")
            return {}


# 非同期対応のラッパー
class FanzaScraper:
    def __init__(self):
        self.playwright_scraper = PlaywrightFanzaScraper()
    
    async def get_high_rated_products(self, url: str = None, max_items: Optional[int] = None, force_refresh: bool = False) -> List[Dict[str, any]]:
        """高評価商品を取得"""
        return await self.playwright_scraper.get_high_rated_products(url=url, max_items=max_items, force_refresh=force_refresh)
    
    def format_rating_stars(self, rating: float) -> str:
        """評価を星マークで表現"""
        return self.playwright_scraper.format_rating_stars(rating)
    
    async def close(self):
        """リソースをクリーンアップ"""
        await self.playwright_scraper.close()