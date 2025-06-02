import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict
from playwright_scraper import FanzaScraper  # Playwright版を使用
from config import (
    DISCORD_TOKEN, COMMAND_PREFIX, RATE_LIMIT_DURATION,
    LOG_LEVEL, LOG_FORMAT
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
user_last_command: Dict[int, datetime] = {}


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
        
        if product['url']:
            self.add_field(name="詳細", value=f"[商品ページを見る]({product['url']})", inline=False)
        
        self.set_footer(text="FANZA セール情報")


@bot.event
async def on_ready():
    """Bot起動時の処理"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    
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
    user_id = interaction.user.id
    now = datetime.now()
    
    if user_id in user_last_command:
        time_since_last = now - user_last_command[user_id]
        if time_since_last < timedelta(seconds=RATE_LIMIT_DURATION):
            remaining = RATE_LIMIT_DURATION - time_since_last.total_seconds()
            await interaction.response.send_message(
                f"レート制限中です。あと{remaining:.0f}秒お待ちください。", 
                ephemeral=True
            )
            return False
    
    user_last_command[user_id] = now
    return True


@bot.command(name='fanza_sale')
@check_nsfw_channel()
@check_rate_limit()
async def fanza_sale(ctx):
    """FANZAのセール中高評価作品を表示"""
    try:
        # 処理中メッセージ
        processing_msg = await ctx.send("セール情報を取得中... 🔍")
        
        # 商品情報を取得
        products = await scraper.get_high_rated_products()
        
        if not products:
            await processing_msg.edit(content="高評価の商品が見つかりませんでした。")
            return
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # ヘッダーメッセージ
        header_embed = discord.Embed(
            title="🎬 FANZAセール 高評価作品TOP5",
            description="現在セール中の評価4.0以上の作品です",
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
        logger.error(f"Error in fanza_sale command: {e}")
        await ctx.send("エラーが発生しました。管理者にお問い合わせください。")


# スラッシュコマンド定義
@bot.tree.command(name="fanza_sale", description="🎬 セール中の高評価AV作品(評価4.0以上)を表示")
@app_commands.describe()
async def slash_fanza_sale(interaction: discord.Interaction):
    """スラッシュコマンド版: FANZAのセール中高評価作品を表示"""
    
    # NSFWチェック
    if not await check_nsfw_interaction(interaction):
        return
    
    # レート制限チェック
    if not await check_rate_limit_interaction(interaction):
        return
    
    try:
        # 処理中メッセージ（defer で3秒の猶予を確保）
        await interaction.response.defer()
        
        # 商品情報を取得
        products = await scraper.get_high_rated_products()
        
        if not products:
            await interaction.followup.send("❌ 現在、評価4.0以上の商品が見つかりませんでした。", ephemeral=True)
            return
        
        # ヘッダーメッセージ
        header_embed = discord.Embed(
            title="🎬 FANZAセール 高評価作品TOP5",
            description=f"現在セール中の評価4.0以上の作品です ({len(products)}件)",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        header_embed.set_thumbnail(url="https://i.imgur.com/fanza_logo.png")
        await interaction.followup.send(embed=header_embed)
        
        # 各商品を表示
        for i, product in enumerate(products, 1):
            embed = FanzaEmbed(product)
            embed.title = f"{i}. {embed.title}"
            await interaction.followup.send(embed=embed)
            await asyncio.sleep(0.5)
        
        # フッターメッセージ
        footer_embed = discord.Embed(
            description="💡 スラッシュコマンド `/help` でヘルプを表示\n⚠️ 価格は変動する可能性があります",
            color=discord.Color.greyple()
        )
        footer_embed.set_footer(text=f"取得時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await interaction.followup.send(embed=footer_embed)
        
    except Exception as e:
        logger.error(f"Error in slash fanza_sale command: {e}")
        try:
            await interaction.followup.send("❌ エラーが発生しました。しばらく時間をおいてから再試行してください。", ephemeral=True)
        except:
            pass


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
        name="🎯 `/fanza_sale`",
        value="セール中の高評価作品（評価4.0以上）を最大5件表示\n**推奨コマンド**",
        inline=True
    )
    embed.add_field(
        name="💡 `/help`",
        value="このヘルプメッセージを表示\n（あなただけに見えます）",
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


def main():
    """メイン実行関数"""
    if not DISCORD_TOKEN:
        logger.error("Discord token not found! Please set DISCORD_TOKEN in .env file")
        return
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")


if __name__ == "__main__":
    main()