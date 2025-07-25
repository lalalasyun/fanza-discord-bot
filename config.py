import os
from dotenv import load_dotenv

load_dotenv()

# Discord設定
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"

# FANZAスクレイピング設定
FANZA_BASE_URL = "https://video.dmm.co.jp/av/list/"
FANZA_SORT = "review_rank"

# セールタイプの定義
SALE_TYPES = {
    "all": {
        "name": "🎯 全てのセール",
        "keys": ["期間限定セール", "20％OFF", "30％OFF", "50％OFF", "70％OFF", "日替わりセール", "10円セール", "100円セール"]
    },
    "limited": {
        "name": "⏰ 期間限定セール",
        "keys": ["期間限定セール"]
    },
    "percent": {
        "name": "💸 割引セール (20-70% OFF)",
        "keys": ["20％OFF", "30％OFF", "50％OFF", "70％OFF"]
    },
    "daily": {
        "name": "📅 日替わりセール",
        "keys": ["日替わりセール"]
    },
    "cheap": {
        "name": "💴 激安セール (10円/100円)",
        "keys": ["10円セール", "100円セール"]
    }
}

# デフォルトのセールURL（全てのセール）
FANZA_SALE_URL = f"{FANZA_BASE_URL}?key={'|'.join(SALE_TYPES['all']['keys'])}&sort={FANZA_SORT}"

def get_sale_url(sale_type: str = "all") -> str:
    """セールタイプに応じたURLを生成"""
    if sale_type not in SALE_TYPES:
        sale_type = "all"
    
    keys = SALE_TYPES[sale_type]["keys"]
    return f"{FANZA_BASE_URL}?key={'|'.join(keys)}&sort={FANZA_SORT}"
MIN_RATING = 4.0
MAX_ITEMS = 50  # キャッシュする最大商品数（10ページ × 5件）
# 表示設定
ITEMS_PER_PAGE = 5  # リスト形式での1ページあたりの表示件数
MAX_DISPLAY_PAGES = 10  # リスト形式での最大ページ数

# キャッシュ設定
CACHE_DURATION = 3600  # 1時間（秒）

# レート制限設定
RATE_LIMIT_DURATION = 30  # 30秒
DISABLE_RATE_LIMIT = os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true"  # 開発環境でのレート制限無効化

# ユーザーエージェント
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Bot バージョン
BOT_VERSION = "2.2.0"