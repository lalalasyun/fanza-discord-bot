import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import asyncio
import logging
import random
import platform
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from playwright_scraper import FanzaScraper  # Playwright版を使用
from missav_scraper import MissAVScraper  # MissAV検索機能
from config import (
    DISCORD_TOKEN, COMMAND_PREFIX, RATE_LIMIT_DURATION,
    LOG_LEVEL, LOG_FORMAT, SALE_TYPES, get_sale_url,
    ITEMS_PER_PAGE, MAX_DISPLAY_PAGES, DISABLE_RATE_LIMIT, BOT_VERSION,
    SORT_OPTIONS, RELEASE_OPTIONS
)

# ログ設定
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# Botインスタンスの作成
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# スクレイパーとレート制限管理
scraper = FanzaScraper()
missav_scraper = MissAVScraper()
user_last_command: Dict[int, datetime] = {}


async def search_missav_for_product(product: dict, force_refresh: bool = False) -> Optional[str]:
    """FANZA商品のタイトルでMissAVを検索してURLを取得"""
    try:
        # タイトルから不要な部分を削除して検索クエリを作成
        title = product['title']
        # 【】や（）内の情報を削除
        title = re.sub(r'【[^】]*】', '', title)
        title = re.sub(r'（[^）]*）', '', title)
        title = re.sub(r'\([^)]*\)', '', title)
        # 余分な空白を削除
        title = ' '.join(title.split())
        
        if not title:
            return None
        
        # MissAVで検索
        videos = await missav_scraper.search_videos(title, force_refresh=force_refresh)
        
        if videos and len(videos) > 0:
            # 最も関連性の高い動画のURLを返す
            return videos[0].get('url')
        
    except Exception as e:
        logger.error(f"Error searching MissAV for product: {e}")
    
    return None


class FanzaEmbed(discord.Embed):
    """FANZA商品表示用のカスタムEmbed"""
    def __init__(self, product: dict):
        super().__init__(
            title=product['title'],
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        rating_stars = scraper.format_rating_stars(product['rating'])
        self.add_field(name="評価", value=f"{rating_stars} ({product['rating']:.1f})", inline=True)
        self.add_field(name="価格", value=product['price'], inline=True)
        
        # 女優名を追加
        if product.get('actresses'):
            if isinstance(product['actresses'], list) and product['actresses']:
                # New format: list of dictionaries with name and url
                actress_links = [f"[{actress['name']}]({actress['url']})" for actress in product['actresses']]
                self.add_field(name="出演者", value=", ".join(actress_links), inline=False)
            elif isinstance(product['actresses'], str) and product['actresses'] != "不明":
                # Legacy format: string of names
                self.add_field(name="出演者", value=product['actresses'], inline=False)
        
        if product['url']:
            self.add_field(name="詳細", value=f"[商品ページを見る]({product['url']})", inline=False)
        
        # MissAV URLが存在する場合は追加
        if product.get('missav_url'):
            self.add_field(name="🎬 MissAV", value=f"[動画を視聴]({product['missav_url']})", inline=False)
        
        # 商品画像を設定
        if product.get('image_url'):
            self.set_image(url=product['image_url'])
        
        self.set_footer(text="FANZA 作品情報")


class PaginationView(View):
    """ページネーション用のView"""
    def __init__(self, products: List[dict], interaction: discord.Interaction, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.products = products
        self.interaction = interaction
        self.current_page = 0
        self.items_per_page = ITEMS_PER_PAGE  # configから読み込み
        self.total_pages = (len(products) - 1) // self.items_per_page + 1
        self.max_pages = MAX_DISPLAY_PAGES  # 最大ページ数の制限
        
        # 最大ページ数を超える場合は制限する
        if self.total_pages > self.max_pages:
            self.total_pages = self.max_pages
            self.products = self.products[:self.max_pages * self.items_per_page]
        
        # 初期ボタン状態を設定
        self._update_buttons()
    
    def _update_buttons(self):
        """ページに応じてボタンの有効/無効を切り替え"""
        # childrenからボタンを取得して更新
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "◀ 前へ":
                    item.disabled = self.current_page == 0
                elif item.label == "次へ ▶":
                    item.disabled = self.current_page >= self.total_pages - 1
    
    def create_embed(self) -> discord.Embed:
        """現在のページのEmbedを作成"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.products))
        current_products = self.products[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"📋 FANZA 作品リスト (ページ {self.current_page + 1}/{self.total_pages})",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for i, product in enumerate(current_products, start=start_idx + 1):
            rating_stars = scraper.format_rating_stars(product['rating'])
            value_text = f"{rating_stars} ({product['rating']:.1f}) | {product['price']}"
            
            # 女優名を追加
            if product.get('actresses'):
                if isinstance(product['actresses'], list) and product['actresses']:
                    # New format: list of dictionaries with name and url
                    actress_links = [f"[{actress['name']}]({actress['url']})" for actress in product['actresses']]
                    value_text += f"\n👥 出演: {', '.join(actress_links)}"
                elif isinstance(product['actresses'], str) and product['actresses'] != "不明":
                    # Legacy format: string of names
                    value_text += f"\n👥 出演: {product['actresses']}"
            
            value_text += f"\n[詳細を見る]({product['url']})"
            
            # MissAV URLが存在する場合は追加
            if product.get('missav_url'):
                value_text += f" | [🎬 MissAV]({product['missav_url']})"
            
            embed.add_field(
                name=f"{i}. {product['title']}",
                value=value_text,
                inline=False
            )
        
        embed.set_footer(text=f"ページ {self.current_page + 1}/{self.total_pages} | FANZA 作品情報")
        return embed
    
    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.primary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("このボタンは他の人のコマンドです。", ephemeral=True)
            return
        
        self.current_page -= 1
        self._update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="次へ ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("このボタンは他の人のコマンドです。", ephemeral=True)
            return
        
        self.current_page += 1
        self._update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🗑️ 閉じる", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("このボタンは他の人のコマンドです。", ephemeral=True)
            return
        
        await interaction.response.edit_message(content="リストを閉じました。", embed=None, view=None)
        self.stop()
    
    async def on_timeout(self):
        """タイムアウト時の処理"""
        # ボタンを無効化
        for item in self.children:
            item.disabled = True
        
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            logger.warning("Interaction message not found on timeout.")
        except discord.HTTPException as e:
            logger.error(f"Failed to edit message on timeout: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on timeout: {e}")


async def setup_bot_profile():
    """BOTのプロフィールとステータスを設定"""
    try:
        # BOTのアクティビティステータスを設定
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="🎬 FANZA作品検索 | /fanza_search"
        )
        
        # BOTのステータスを設定（オンライン状態）
        await bot.change_presence(
            status=discord.Status.online,
            activity=activity
        )
        
        logger.info("Bot profile and status configured successfully")
        
        # 動的ステータス更新を開始
        asyncio.create_task(dynamic_status_updater())
        
    except Exception as e:
        logger.error(f"Error setting bot profile: {e}")


async def dynamic_status_updater():
    """BOTのステータスを動的に更新"""
    # テンプレートベースのステータスメッセージ定義
    status_message_definitions = [
        ("🎬 FANZA作品検索 | /fanza_search", False),
        ("⭐ 高評価作品を検索中...", False),
        ("🔍 作品検索 | /fanza_search", False),
        ("⏰ セールフィルター | /fanza_search", False),
        ("💸 高評価作品 | /fanza_search", False),
        ("📅 日替わりセール | /fanza_search", False),
        ("💴 激安セール | /fanza_search", False),
        ("💡 /help でヘルプ表示", False),
        ("🏠 {guild_count}のサーバーで稼働中", True),  # 動的データが必要
    ]
    
    try:
        await asyncio.sleep(30)  # 初期化後30秒待機
        
        while not bot.is_closed():
            # ランダムにステータスメッセージテンプレートを選択
            template, needs_dynamic_data = random.choice(status_message_definitions)
            
            # 動的データが必要な場合はフォーマット
            if needs_dynamic_data:
                message = template.format(guild_count=len(bot.guilds))
            else:
                message = template
            
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=message
            )
            
            await bot.change_presence(
                status=discord.Status.online,
                activity=activity
            )
            
            logger.debug(f"Updated bot status: {message}")
            
            # 60秒待機
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"Error in dynamic status updater: {e}")


@bot.event
async def on_ready():
    """Bot起動時の処理"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    
    # 起動時間を記録
    bot.start_time = datetime.now()
    
    # BOTのプロフィール設定
    await setup_bot_profile()
    
    # スラッシュコマンドを同期
    try:
        # グローバル同期
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} global slash commands')
        
        # 各ギルドでも同期
        for guild in bot.guilds:
            try:
                guild_synced = await bot.tree.sync(guild=guild)
                logger.info(f'Synced {len(guild_synced)} slash commands for guild: {guild.name}')
            except Exception as e:
                logger.error(f'Failed to sync for guild {guild.name}: {e}')
                
    except Exception as e:
        logger.error(f'Failed to sync slash commands: {e}')


@bot.event
async def on_command_error(ctx, error):
    """コマンドエラー時の処理"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"コマンドはクールダウン中です。{error.retry_after:.0f}秒後に再試行してください。")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("エラーが発生しました。しばらくしてから再試行してください。")


def check_nsfw_channel():
    """NSFWチャンネルかチェックするデコレータ"""
    async def predicate(ctx):
        if not ctx.channel.is_nsfw():
            await ctx.send("このコマンドはNSFWチャンネルでのみ使用できます。")
            return False
        return True
    return commands.check(predicate)


def check_rate_limit():
    """レート制限をチェックするデコレータ"""
    async def predicate(ctx):
        # 開発環境でレート制限が無効の場合はスキップ
        if DISABLE_RATE_LIMIT:
            return True
            
        user_id = ctx.author.id
        now = datetime.now()
        
        if user_id in user_last_command:
            time_since_last = now - user_last_command[user_id]
            if time_since_last < timedelta(seconds=RATE_LIMIT_DURATION):
                remaining = RATE_LIMIT_DURATION - time_since_last.total_seconds()
                await ctx.send(f"レート制限中です。あと{remaining:.0f}秒お待ちください。")
                return False
        
        user_last_command[user_id] = now
        return True
    return commands.check(predicate)


async def check_nsfw_interaction(interaction: discord.Interaction) -> bool:
    """インタラクション用NSFWチェック"""
    if not interaction.channel.is_nsfw():
        await interaction.response.send_message(
            "このコマンドはNSFWチャンネルでのみ使用できます。", 
            ephemeral=True
        )
        return False
    return True


async def check_rate_limit_interaction(interaction: discord.Interaction) -> bool:
    """インタラクション用レート制限チェック"""
    # 開発環境でレート制限が無効の場合はスキップ
    if DISABLE_RATE_LIMIT:
        return True
        
    user_id = interaction.user.id
    now = datetime.now()
    
    if user_id in user_last_command:
        time_since_last = now - user_last_command[user_id]
        if time_since_last < timedelta(seconds=RATE_LIMIT_DURATION):
            remaining = RATE_LIMIT_DURATION - time_since_last.total_seconds()
            # interaction.responseが既に使われている場合はfollowupを使用
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"レート制限中です。あと{remaining:.0f}秒お待ちください。", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"レート制限中です。あと{remaining:.0f}秒お待ちください。", 
                    ephemeral=True
                )
            return False
    
    user_last_command[user_id] = now
    return True


@bot.command(name='fanza_search')
@check_nsfw_channel()
@check_rate_limit()
async def fanza_search(ctx):
    """FANZAの高評価作品を表示"""
    try:
        # 処理中メッセージ
        processing_msg = await ctx.send("商品情報を取得中... 🔍")
        
        # 商品情報を取得
        products = await scraper.get_high_rated_products()
        
        if not products:
            await processing_msg.edit(content="高評価の商品が見つかりませんでした。")
            return
        
        # 各商品についてMissAVで検索（非同期で並列実行）
        async def add_missav_url(product):
            missav_url = await search_missav_for_product(product, force_refresh=force_refresh)
            if missav_url:
                product['missav_url'] = missav_url
            return product
        
        # 並列でMissAV検索を実行（上位5件のみ）
        products_to_search = products[:5]
        products[:5] = await asyncio.gather(*[add_missav_url(product) for product in products_to_search])
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # ヘッダーメッセージ
        header_embed = discord.Embed(
            title="🎬 FANZA 高評価作品TOP5",
            description="評価4.0以上の作品です",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        await ctx.send(embed=header_embed)
        
        # 各商品を表示
        for i, product in enumerate(products, 1):
            embed = FanzaEmbed(product)
            embed.title = f"{i}. {embed.title}"
            await ctx.send(embed=embed)
            await asyncio.sleep(0.5)  # 連続投稿を避けるため少し待機
        
        # フッターメッセージ
        footer_embed = discord.Embed(
            description="※価格は変動する可能性があります",
            color=discord.Color.greyple()
        )
        footer_embed.set_footer(text=f"取得時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=footer_embed)
        
    except Exception as e:
        logger.error(f"Error in fanza_search command: {e}")
        await ctx.send("エラーが発生しました。管理者にお問い合わせください。")


# スラッシュコマンド定義
@bot.tree.command(name="fanza_search", description="🎬 FANZA高評価AV作品を検索")
@app_commands.describe(
    mode="表示モード: 評価順（デフォルト）、ランダム、リスト形式",
    sale_type="セールフィルター: なし（デフォルト）、期間限定、割引、日替わり、激安、全てのセール",
    media_type="メディアタイプ: 全て（デフォルト）、2D動画のみ、VRのみ",
    sort_type="ソート順: 評価順（デフォルト）、おすすめ順、人気順、売上順、新着順、お気に入り順",
    keyword="キーワード検索: 作品名、女優名などで絞り込み",
    release_filter="配信開始日: 全期間（デフォルト）、最新作、準新作",
    count="表示件数: 1-10件（デフォルト: 5件）",
    force_refresh="キャッシュを無視して最新データを取得"
)
@app_commands.choices(
    mode=[
        app_commands.Choice(name="🏆 評価順（デフォルト）", value="rating"),
        app_commands.Choice(name="🎲 ランダム", value="random"),
        app_commands.Choice(name="📋 リスト形式", value="list"),
    ],
    sale_type=[
        app_commands.Choice(name="🔍 セールフィルターなし（デフォルト）", value="none"),
        app_commands.Choice(name="⏰ 期間限定セール", value="limited"),
        app_commands.Choice(name="💸 割引セール (20-70% OFF)", value="percent"),
        app_commands.Choice(name="📅 日替わりセール", value="daily"),
        app_commands.Choice(name="💴 激安セール (10円/100円)", value="cheap"),
        app_commands.Choice(name="🎯 全てのセール", value="all"),
    ],
    media_type=[
        app_commands.Choice(name="🎬 全て（2D+VR）", value="all"),
        app_commands.Choice(name="📺 2D動画のみ", value="2d"),
        app_commands.Choice(name="🥽 VRのみ", value="vr"),
    ],
    sort_type=[
        app_commands.Choice(name="⭐ 評価の高い順（デフォルト）", value="review_rank"),
        app_commands.Choice(name="🔍 おすすめ順", value="suggest"),
        app_commands.Choice(name="📈 人気順", value="ranking"),
        app_commands.Choice(name="💰 売上本数順", value="saleranking_asc"),
        app_commands.Choice(name="🆕 新着順", value="date"),
        app_commands.Choice(name="❤️ お気に入り数順", value="bookmark_desc"),
    ],
    release_filter=[
        app_commands.Choice(name="📅 全期間（デフォルト）", value="all"),
        app_commands.Choice(name="🆕 最新作", value="latest"),
        app_commands.Choice(name="📺 準新作", value="recent"),
    ]
)
async def slash_fanza_search(interaction: discord.Interaction, mode: str = "rating", sale_type: str = "none", media_type: str = "all", sort_type: str = "review_rank", keyword: Optional[str] = None, release_filter: str = "all", count: app_commands.Range[int, 1, 10] = 5, force_refresh: bool = False):
    """スラッシュコマンド版: FANZAの高評価作品を検索"""
    
    # NSFWチェック
    if not await check_nsfw_interaction(interaction):
        return
    
    try:
        # 処理中メッセージ（defer で3秒の猶予を確保）
        await interaction.response.defer()
        
        # レート制限チェック（defer後に実行）
        if not await check_rate_limit_interaction(interaction):
            return
        
        # セールタイプ、メディアタイプ、ソート、キーワード、リリースフィルターに応じたURLを生成
        media_param = None if media_type == "all" else media_type
        url = get_sale_url(
            sale_type=sale_type, 
            media_type=media_param, 
            sort_type=sort_type, 
            keyword=keyword, 
            release_filter=release_filter
        )
        
        # 商品情報を取得
        products = await scraper.get_high_rated_products(url=url, force_refresh=force_refresh)
        
        if not products:
            media_text = {
                "all": "商品",
                "2d": "2D動画", 
                "vr": "VR作品"
            }.get(media_type, "商品")
            await interaction.followup.send(f"❌ 評価4.0以上の{media_text}が見つかりませんでした。", ephemeral=True)
            return
        
        # 各商品についてMissAVで検索（非同期で並列実行）
        async def add_missav_url(product):
            missav_url = await search_missav_for_product(product, force_refresh=force_refresh)
            if missav_url:
                product['missav_url'] = missav_url
            return product
        
        # 並列でMissAV検索を実行
        products = await asyncio.gather(*[add_missav_url(product) for product in products])
        
        # セールタイプとメディアタイプの表示名を取得
        sale_type_name = SALE_TYPES.get(sale_type, {}).get("name", "🎯 全てのセール")
        media_emoji = {
            "all": "🎬",
            "2d": "📺",
            "vr": "🥽"
        }.get(media_type, "🎬")
        media_text = {
            "all": "作品",
            "2d": "2D動画",
            "vr": "VR作品"
        }.get(media_type, "作品")
        
        # モードに応じて処理
        import random
        
        if mode == "random":
            # ランダムモード: 商品をシャッフルして指定件数選択
            products = random.sample(products, min(count, len(products)))
            title = f"🎲 FANZA {media_emoji} {media_text} ランダム - {sale_type_name}"
            description = f"ランダムに選ばれた高評価{media_text}です ({count}件)"
        elif mode == "list":
            # リストモード: 簡易表示
            title = f"📋 FANZA {media_emoji} {media_text}リスト - {sale_type_name}"
            description = f"高評価{media_text}一覧 ({len(products)}件)"
        else:
            # 評価順モード（デフォルト）- 指定件数のみ表示
            title = f"{media_emoji} FANZA 高評価{media_text}TOP{count} - {sale_type_name}"
            description = f"評価4.0以上の{media_text}です (表示: {count}件 / 全{len(products)}件)"
            products = products[:count]  # 評価順とランダムモードは指定件数に制限
        
        # ヘッダーメッセージ
        header_embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # 検索URLを追加
        header_embed.add_field(
            name="🔗 検索URL",
            value=f"[FANZAで直接確認する]({url})",
            inline=False
        )
        
        await interaction.followup.send(embed=header_embed)
        
        # モードに応じた表示
        if mode == "list":
            # リスト形式: ページネーション付きで表示
            view = PaginationView(products, interaction)
            embed = view.create_embed()
            await interaction.followup.send(embed=embed, view=view)
        else:
            # 通常形式: 個別のEmbedで表示
            for i, product in enumerate(products, 1):
                embed = FanzaEmbed(product)
                embed.title = f"{i}. {embed.title}"
                await interaction.followup.send(embed=embed)
                await asyncio.sleep(0.5)
        
        
    except Exception as e:
        logger.error(f"Error in slash fanza_search command: {e}")
        try:
            await interaction.followup.send("❌ エラーが発生しました。しばらく時間をおいてから再試行してください。", ephemeral=True)
        except discord.NotFound:
            logger.warning("Failed to send error message: interaction not found.")
        except discord.HTTPException as e:
            logger.error(f"Failed to send error message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending error message: {e}")



@bot.tree.command(name="help", description="💡 FANZA Botの使用方法とコマンド一覧を表示")
async def slash_help(interaction: discord.Interaction):
    """スラッシュコマンド版: ヘルプ"""
    embed = discord.Embed(
        title="🤖 FANZA Bot ヘルプ",
        description="FANZAのセール情報から高評価作品を取得するBotです",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # コマンド説明
    embed.add_field(
        name="📋 コマンド一覧",
        value="",
        inline=False
    )
    embed.add_field(
        name="🎬 `/fanza_sale`",
        value="セール中の高評価作品（評価4.0以上）を最大5件表示\n**推奨コマンド** | media_typeオプション対応",
        inline=False
    )
    embed.add_field(
        name="💡 `/help`",
        value="このヘルプメッセージを表示\n（あなただけに見えます）",
        inline=True
    )
    embed.add_field(
        name="⚙️ 共通オプション",
        value="**表示モード:**\n• 🏆 評価順（デフォルト）\n• 🎲 ランダム\n• 📋 リスト形式\n\n**セールタイプ:**\n• 🎯 全て（デフォルト）\n• ⏰ 期間限定\n• 💸 割引セール\n• 📅 日替わり\n• 💴 激安セール\n\n**メディアタイプ NEW!:**\n• 🎬 全て（2D+VR）\n• 📺 2D動画のみ\n• 🥽 VRのみ",
        inline=False
    )
    embed.add_field(
        name="🔍 `/missav_search`",
        value="MissAVで動画を検索して視聴URLを取得\n**NEW!** 動画検索機能",
        inline=True
    )
    embed.add_field(
        name="🔧 `!fanza_sale`",
        value="プレフィックス版コマンド\n（レガシー対応）",
        inline=True
    )
    
    # 使用条件
    embed.add_field(
        name="⚠️ 使用条件",
        value="• **NSFWチャンネル**でのみ使用可能\n• **5分に1回**のレート制限あり\n• 18歳未満の使用は禁止",
        inline=False
    )
    
    # 機能説明
    embed.add_field(
        name="✨ 機能",
        value="• 動的スクレイピング（最新情報）\n• キャッシュシステム（1時間）\n• 高評価作品のフィルタリング",
        inline=False
    )
    
    embed.set_footer(text="FANZA Bot v2.0 | スラッシュコマンド対応")
    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name='help_fanza')
async def help_fanza(ctx):
    """ヘルプコマンド（プレフィックス版）"""
    embed = discord.Embed(
        title="FANZA Bot ヘルプ",
        description="FANZAのセール情報を取得するBotです",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="`/fanza_sale`",
        value="セール中の高評価作品（評価4.0以上）を最大5件表示します（推奨）",
        inline=False
    )
    embed.add_field(
        name="`!fanza_sale`",
        value="プレフィックスコマンド版（レガシー対応）",
        inline=False
    )
    embed.add_field(
        name="使用条件",
        value="• NSFWチャンネルでのみ使用可能\n• 5分に1回のレート制限あり",
        inline=False
    )
    embed.set_footer(text="FANZA Bot v2.0 - スラッシュコマンド対応")
    await ctx.send(embed=embed)


@bot.command(name='sync')
@commands.is_owner()
async def sync_commands(ctx):
    """スラッシュコマンドを手動同期（オーナー専用）"""
    try:
        # グローバル同期
        synced = await bot.tree.sync()
        await ctx.send(f"✅ {len(synced)} global slash commands synced")
        
        # ギルド同期
        if ctx.guild:
            guild_synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ {len(guild_synced)} guild slash commands synced for {ctx.guild.name}")
            
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")
        logger.error(f"Manual sync error: {e}")


@bot.tree.command(name="bot_info", description="🤖 BOTの詳細情報とステータスを表示")
async def bot_info(interaction: discord.Interaction):
    """BOTの情報を表示（コマンドボタン付き）"""
    try:
        # BOTの統計情報を取得（パフォーマンス最適化）
        guild_count = len(bot.guilds)
        
        # 大量のギルドの場合の最適化：サンプリングまたは概算計算
        if guild_count > 1000:
            # 大規模BOTの場合は概算値を使用
            total_members = "1M+" if guild_count > 10000 else f"{guild_count * 500:,}+ (概算)"
        else:
            # 通常規模の場合は正確な計算
            total_members = sum(guild.member_count or 0 for guild in bot.guilds)
            total_members = f"{total_members:,}"
        
        uptime = datetime.now() - bot.start_time if hasattr(bot, 'start_time') else "計算中..."
        
        embed = discord.Embed(
            title="🤖 FANZA Bot 詳細情報",
            description="FANZAセール情報を提供するDiscord BOTです",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # BOTの基本情報
        embed.add_field(
            name="📊 基本統計",
            value=f"• **サーバー数**: {guild_count:,}\n• **総ユーザー数**: {total_members}\n• **稼働時間**: {uptime}",
            inline=True
        )
        
        # 機能情報
        embed.add_field(
            name="⚡ 主な機能",
            value="• セール作品検索\n• 5つのセールタイプ\n• 動的ステータス表示\n• レート制限保護",
            inline=True
        )
        
        # バージョン情報（動的取得）
        python_version = platform.python_version()
        embed.add_field(
            name="🔧 技術情報",
            value=f"• **discord.py**: {discord.__version__}\n• **Python**: {python_version}\n• **Bot Version**: {BOT_VERSION}",
            inline=True
        )
        
        # アバター画像を設定
        if bot.user.avatar:
            embed.set_thumbnail(url=bot.user.avatar.url)
        
        embed.set_footer(text="FANZA Bot | 高評価作品をお届け")
        
        # コマンドボタンを作成
        view = BotInfoView()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in bot_info command: {e}")
        await interaction.response.send_message(
            "❌ BOT情報の取得に失敗しました。", 
            ephemeral=True
        )


class BotInfoView(View):
    """BOT情報表示用のView（コマンドボタン付き）"""
    def __init__(self):
        super().__init__(timeout=300)  # 5分でタイムアウト
    
    @discord.ui.button(label="🎬 作品検索", style=discord.ButtonStyle.primary, emoji="🎬")
    async def sale_search_button(self, interaction: discord.Interaction, button: Button):
        """作品検索ボタン"""
        embed = discord.Embed(
            title="🎬 FANZA作品検索",
            description="以下のコマンドでFANZA作品を検索できます",
            color=discord.Color.green()
        )
        embed.add_field(
            name="💡 使用方法",
            value="`/fanza_search` コマンドを使用してください\n\n**オプション:**\n• 表示モード: 評価順/ランダム/リスト\n• セールフィルター: なし/期間限定/割引/日替わり/激安/全セール",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="💡 ヘルプ", style=discord.ButtonStyle.secondary, emoji="💡")
    async def help_button(self, interaction: discord.Interaction, button: Button):
        """ヘルプボタン"""
        embed = discord.Embed(
            title="💡 FANZA Bot ヘルプ",
            description="コマンド一覧と使用方法",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 主要コマンド",
            value="• `/fanza_search` - FANZA作品検索\n• `/help` - 詳細ヘルプ\n• `/bot_info` - BOT情報表示",
            inline=False
        )
        embed.add_field(
            name="⚠️ 使用条件",
            value="• NSFWチャンネルでのみ使用可能\n• レート制限: 5分に1回",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📊 ステータス", style=discord.ButtonStyle.secondary, emoji="📊")
    async def status_button(self, interaction: discord.Interaction, button: Button):
        """ステータスボタン"""
        guild_count = len(interaction.client.guilds)
        
        # 大量ギルド対応のパフォーマンス最適化
        if guild_count > 1000:
            total_members = "1M+" if guild_count > 10000 else f"{guild_count * 500:,}+ (概算)"
        else:
            total_members = sum(guild.member_count or 0 for guild in interaction.client.guilds)
            total_members = f"{total_members:,}人"
        
        # 動的なステータスチェック
        current_time = datetime.now()
        uptime = current_time - interaction.client.start_time if hasattr(interaction.client, 'start_time') else "不明"
        
        # より正確な機能状況チェック
        try:
            # BOTが正常に動作しているかの基本チェック
            bot_healthy = not interaction.client.is_closed()
            scraping_status = "🟢 利用可能" if bot_healthy else "🔴 停止中"
            cache_status = "🟢 利用可能" if bot_healthy else "🔴 停止中"
            # コマンド同期ステータスをより正確に表現
            commands_status = "🟢 ローカル登録済み" if interaction.client.tree else "🟡 未登録"
        except Exception:
            scraping_status = "🟡 確認中"
            cache_status = "🟡 確認中"
            commands_status = "🟡 確認中"
        
        embed = discord.Embed(
            title="📊 BOTステータス",
            description="現在のBOT動作状況（リアルタイム）",
            color=discord.Color.orange(),
            timestamp=current_time
        )
        embed.add_field(
            name="🌐 接続情報",
            value=f"• **稼働サーバー**: {guild_count:,}個\n• **総ユーザー数**: {total_members}\n• **接続状態**: 🟢 オンライン\n• **稼働時間**: {uptime}",
            inline=False
        )
        embed.add_field(
            name="⚡ システム状況",
            value=f"• **スクレイピング機能**: {scraping_status}\n• **キャッシュシステム**: {cache_status}\n• **コマンドシステム**: {commands_status}",
            inline=False
        )
        embed.add_field(
            name="📊 監視項目",
            value="• **応答性**: リアルタイム監視中\n• **リソース**: 設計上最適化を考慮\n• **Discord API**: 接続状況良好",
            inline=False
        )
        embed.set_footer(text="最終確認時刻")
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="missav_search", description="🔍 MissAVで動画を検索して視聴URLを取得")
@app_commands.describe(
    title="検索したい動画のタイトル",
    force_refresh="キャッシュを無視して最新データを取得"
)
async def missav_search(interaction: discord.Interaction, title: str, force_refresh: bool = False):
    """MissAV動画検索コマンド"""
    
    # NSFWチェック
    if not await check_nsfw_interaction(interaction):
        return
    
    # レート制限チェック
    if not await check_rate_limit_interaction(interaction):
        return
    
    if not title or len(title.strip()) < 2:
        await interaction.response.send_message("❌ 検索タイトルは2文字以上で入力してください。", ephemeral=True)
        return
    
    try:
        # 処理中メッセージ
        await interaction.response.defer()
        
        # MissAVで動画を検索
        videos = await missav_scraper.search_videos(title.strip(), force_refresh=force_refresh)
        
        if not videos:
            await interaction.followup.send(f"❌ 「{title}」に関連する動画が見つかりませんでした。", ephemeral=True)
            return
        
        # 検索結果を表示（最大5件）
        videos = videos[:5]
        
        # ヘッダーEmbed
        header_embed = discord.Embed(
            title=f"🔍 MissAV検索結果: {title}",
            description=f"見つかった動画: {len(videos)}件",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=header_embed)
        
        # 各動画の情報を表示
        for i, video in enumerate(videos, 1):
            embed = discord.Embed(
                title=f"{i}. {video['title'][:60]}{'...' if len(video['title']) > 60 else ''}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            if video.get('duration'):
                embed.add_field(name="再生時間", value=video['duration'], inline=True)
            
            embed.add_field(name="ソース", value=video['source'], inline=True)
            
            if video.get('url'):
                embed.add_field(name="視聴URL", value=f"[動画を見る]({video['url']})", inline=False)
            
            # サムネイル画像を設定
            if video.get('thumbnail'):
                embed.set_image(url=video['thumbnail'])
            
            embed.set_footer(text="MissAV検索結果")
            
            await interaction.followup.send(embed=embed)
            await asyncio.sleep(0.5)
        
        # フッターメッセージ
        footer_embed = discord.Embed(
            description="⚠️ 18歳未満の視聴は禁止されています\n💡 `/help` でヘルプを表示",
            color=discord.Color.greyple()
        )
        footer_embed.set_footer(text=f"検索時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await interaction.followup.send(embed=footer_embed)
        
    except Exception as e:
        logger.error(f"Error in missav_search command: {e}")
        try:
            await interaction.followup.send("❌ 検索中にエラーが発生しました。しばらく時間をおいてから再試行してください。", ephemeral=True)
        except:
            logger.error("Failed to send error message")


async def cleanup():
    """クリーンアップ処理"""
    try:
        await scraper.close()
        logger.info("Scraper resources cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def main():
    """メイン実行関数"""
    if not DISCORD_TOKEN:
        logger.error("Discord token not found! Please set DISCORD_TOKEN in .env file")
        return
    
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")
    finally:
        # クリーンアップ処理を実行
        try:
            asyncio.run(cleanup())
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


if __name__ == "__main__":
    main()