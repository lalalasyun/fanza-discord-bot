"""
Playwright版スクレイパー（Seleniumの代替案）
軽量で高速、Chrome/Chromiumのインストールが不要
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict
from config import USER_AGENT, FANZA_SALE_URL, MIN_RATING, MAX_ITEMS, CACHE_DURATION

logger = logging.getLogger(__name__)


class PlaywrightFanzaScraper:
    def __init__(self):
        self.cache = {}
        self.cache_timestamp = None

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

    async def get_high_rated_products(self) -> List[Dict[str, any]]:
        """高評価商品を取得（キャッシュ機能付き）"""
        # キャッシュチェック
        if self.cache_timestamp and self.cache:
            if datetime.now() - self.cache_timestamp < timedelta(seconds=CACHE_DURATION):
                logger.info("Returning cached data")
                return self.cache
        
        # 新規取得
        products = await self.scrape_products()
        if products:
            self.cache = products
            self.cache_timestamp = datetime.now()
        
        return products

    async def scrape_products(self) -> List[Dict[str, any]]:
        """実際のスクレイピング処理"""
        products = []
        
        try:
            async with async_playwright() as p:
                # ブラウザを起動（自動的にChromiumをダウンロード）
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                # コンテキストとページを作成
                context = await browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                # ページにアクセス
                logger.info(f"Accessing URL: {FANZA_SALE_URL}")
                await page.goto(FANZA_SALE_URL, wait_until='networkidle')
                
                # 年齢認証の処理
                try:
                    # 年齢認証ボタンを探す
                    age_button = await page.query_selector("a:has-text('はい')")
                    if age_button:
                        await age_button.click()
                        logger.info("Age verification completed")
                        await page.wait_for_load_state('networkidle')
                except:
                    pass
                
                # 商品リストが読み込まれるまで待機
                await page.wait_for_timeout(3000)
                
                # 商品要素を探す
                product_selectors = [
                    "[data-e2eid='content-card']",
                    "li[class*='border border-gray-300']",
                    "div[data-e2eid='content-card']",
                    "li:has(div[data-e2eid='content-card'])",
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
                    await browser.close()
                    return products
                
                # 各商品の情報を取得（最大100件まで確認）
                for element in product_elements[:100]:
                    try:
                        # タイトル
                        title = ""
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
                            continue
                        
                        # URL
                        url = ""
                        link_elem = await element.query_selector("a[data-e2eid='title']")
                        if not link_elem:
                            link_elem = await element.query_selector("a[href*='/detail/']")
                        if link_elem:
                            url = await link_elem.get_attribute('href')
                            if url and not url.startswith('http'):
                                url = f"https://www.dmm.co.jp{url}"
                        
                        # 評価（星の画像の数をカウント）
                        rating = 0.0
                        star_images = await element.query_selector_all("img[src*='star/yellow']")
                        if star_images:
                            rating = len(star_images)
                        
                        # 価格
                        price = "価格不明"
                        price_elem = await element.query_selector("[data-e2eid='content-price']")
                        if price_elem:
                            price_text = await price_elem.text_content()
                            if price_text and '円' in price_text:
                                price = price_text.strip()
                        
                        # 割引情報
                        discount = ""
                        discount_elem = await element.query_selector("div:has-text('セール')")
                        if discount_elem:
                            discount_text = await discount_elem.text_content()
                            if 'セール' in discount_text:
                                discount = "セール中"
                        
                        # 商品画像URL
                        image_url = ""
                        image_selectors = [
                            "img[data-e2eid='content-image']",
                            "img[src*='pics.dmm.co.jp']",
                            "img[src*='dmm.com']",
                            "img[alt*='パッケージ']",
                            "div[data-e2eid='content-image'] img",
                            "picture img",
                            "img[loading='lazy']"
                        ]
                        for selector in image_selectors:
                            img_elem = await element.query_selector(selector)
                            if img_elem:
                                image_url = await img_elem.get_attribute('src')
                                if image_url and ('dmm' in image_url or 'pics' in image_url):
                                    # 高解像度版に変換
                                    if 'ps.jpg' in image_url:
                                        image_url = image_url.replace('ps.jpg', 'pl.jpg')
                                    break
                        
                        # 評価が基準以上の商品のみ追加
                        if rating >= MIN_RATING:
                            products.append({
                                'title': title[:50] + '...' if len(title) > 50 else title,
                                'rating': rating,
                                'price': price,
                                'url': url,
                                'image_url': image_url
                            })
                            logger.info(f"Added product: {title[:30]}... (Rating: {rating}, Image: {bool(image_url)})")
                        
                    except Exception as e:
                        logger.error(f"Error parsing product element: {e}")
                        continue
                
                await browser.close()
                
                # 評価順でソートして上位を返す
                products.sort(key=lambda x: x['rating'], reverse=True)
                products = products[:MAX_ITEMS]
                
                logger.info(f"Successfully scraped {len(products)} high-rated products")
                
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        return products


# 非同期対応のラッパー
class FanzaScraper:
    def __init__(self):
        self.playwright_scraper = PlaywrightFanzaScraper()
    
    async def get_high_rated_products(self) -> List[Dict[str, any]]:
        """高評価商品を取得"""
        return await self.playwright_scraper.get_high_rated_products()
    
    def format_rating_stars(self, rating: float) -> str:
        """評価を星マークで表現"""
        return self.playwright_scraper.format_rating_stars(rating)