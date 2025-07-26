import os
from dotenv import load_dotenv

load_dotenv()

# Discord設定
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"

# FANZAスクレイピング設定
FANZA_BASE_URL = "https://video.dmm.co.jp/av/list/"
FANZA_SORT = "review_rank"

# ソート設定
SORT_OPTIONS = {
    "suggest": {
        "name": "🔍 おすすめ順",
        "value": "suggest",
        "description": "FANZAのおすすめ順で表示"
    },
    "ranking": {
        "name": "📈 人気順", 
        "value": "ranking",
        "description": "人気順で表示"
    },
    "saleranking_asc": {
        "name": "💰 売上本数順",
        "value": "saleranking_asc", 
        "description": "売上本数順で表示"
    },
    "date": {
        "name": "🆕 新着順",
        "value": "date",
        "description": "新着順で表示"
    },
    "review_rank": {
        "name": "⭐ 評価の高い順",
        "value": "review_rank",
        "description": "評価の高い順で表示（デフォルト）"
    },
    "bookmark_desc": {
        "name": "❤️ お気に入り数順", 
        "value": "bookmark_desc",
        "description": "お気に入り数順で表示"
    }
}

# リリース設定
RELEASE_OPTIONS = {
    "all": {
        "name": "📅 全期間",
        "value": None,
        "description": "全期間の作品を表示"
    },
    "latest": {
        "name": "🆕 最新作",
        "value": "latest",
        "description": "最新作のみ表示"
    },
    "recent": {
        "name": "📺 準新作",
        "value": "recent", 
        "description": "準新作のみ表示"
    }
}

# セールタイプの定義
SALE_TYPES = {
    "none": {
        "name": "🔍 セールフィルターなし",
        "keys": []
    },
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

def get_sale_url(sale_type: str = "none", media_type: str = None, sort_type: str = "review_rank", keyword: str = None, release_filter: str = None) -> str:
    """セールタイプ、メディアタイプ、ソート、キーワード、リリースフィルターに応じたURLを生成"""
    if sale_type not in SALE_TYPES:
        sale_type = "none"
    
    keys = SALE_TYPES[sale_type]["keys"]
    
    # キーワードまたはセールキーが存在する場合のみkeyパラメータを追加
    key_parts = []
    if keyword and keyword.strip():
        key_parts.append(keyword.strip())
    if keys:
        key_parts.append('|'.join(keys))
    
    # ソートタイプの確認
    sort_value = SORT_OPTIONS.get(sort_type, {}).get("value", FANZA_SORT)
    
    # ベースURL構築
    url = f"{FANZA_BASE_URL}?sort={sort_value}"
    
    # keyパラメータがある場合のみ追加
    if key_parts:
        key_param = '+'.join(key_parts)
        url += f"&key={key_param}"
    
    # media_typeパラメータを追加
    if media_type == "2d":
        url += "&media_type=2d"
    elif media_type == "vr":
        url += "&media_type=vr"
    
    # リリースフィルターパラメータを追加
    if release_filter and release_filter != "all":
        release_value = RELEASE_OPTIONS.get(release_filter, {}).get("value")
        if release_value:
            url += f"&release={release_value}"
    
    return url
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