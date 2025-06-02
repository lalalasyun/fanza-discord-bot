import os
from dotenv import load_dotenv

load_dotenv()

# Discord設定
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"

# FANZAスクレイピング設定
FANZA_SALE_URL = "https://video.dmm.co.jp/av/list/?key=%E6%9C%9F%E9%96%93%E9%99%90%E5%AE%9A%E3%82%BB%E3%83%BC%E3%83%AB|20%EF%BC%85OFF|30%EF%BC%85OFF|50%EF%BC%85OFF|70%EF%BC%85OFF|%E6%97%A5%E6%9B%BF%E3%82%8F%E3%82%8A%E3%82%BB%E3%83%BC%E3%83%AB|10%E5%86%86%E3%82%BB%E3%83%BC%E3%83%AB|100%E5%86%86%E3%82%BB%E3%83%BC%E3%83%AB&sort=review_rank"
MIN_RATING = 4.0
MAX_ITEMS = 50  # キャッシュする最大商品数（10ページ × 5件）
# 表示設定
ITEMS_PER_PAGE = 5  # リスト形式での1ページあたりの表示件数
MAX_DISPLAY_PAGES = 10  # リスト形式での最大ページ数

# キャッシュ設定
CACHE_DURATION = 3600  # 1時間（秒）

# レート制限設定
RATE_LIMIT_DURATION = 300  # 5分（秒）

# ユーザーエージェント
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"