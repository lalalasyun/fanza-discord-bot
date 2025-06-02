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
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} slash commands')
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
@bot.tree.command(name="fanza_sale", description="セール中の高評価AV作品を表示します")
async def slash_fanza_sale(interaction: discord.Interaction):
    """スラッシュコマンド版: FANZAのセール中高評価作品を表示"""
    
    # NSFWチェック
    if not await check_nsfw_interaction(interaction):
        return
    
    # レート制限チェック
    if not await check_rate_limit_interaction(interaction):
        return
    
    try:
        # 処理中メッセージ
        await interaction.response.send_message("セール情報を取得中... 🔍")
        
        # 商品情報を取得
        products = await scraper.get_high_rated_products()
        
        if not products:
            await interaction.edit_original_response(content="高評価の商品が見つかりませんでした。")
            return
        
        # ヘッダーメッセージ
        header_embed = discord.Embed(
            title="🎬 FANZAセール 高評価作品TOP5",
            description="現在セール中の評価4.0以上の作品です",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        await interaction.edit_original_response(content=None, embed=header_embed)
        
        # 各商品を表示
        for i, product in enumerate(products, 1):
            embed = FanzaEmbed(product)
            embed.title = f"{i}. {embed.title}"
            await interaction.followup.send(embed=embed)
            await asyncio.sleep(0.5)
        
        # フッターメッセージ
        footer_embed = discord.Embed(
            description="※価格は変動する可能性があります",
            color=discord.Color.greyple()
        )
        footer_embed.set_footer(text=f"取得時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await interaction.followup.send(embed=footer_embed)
        
    except Exception as e:
        logger.error(f"Error in slash fanza_sale command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)
        else:
            await interaction.followup.send("エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)


@bot.tree.command(name="help", description="FANZA Botの使用方法を表示します")
async def slash_help(interaction: discord.Interaction):
    """スラッシュコマンド版: ヘルプ"""
    embed = discord.Embed(
        title="FANZA Bot ヘルプ",
        description="FANZAのセール情報を取得するBotです",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="`/fanza_sale`",
        value="セール中の高評価作品（評価4.0以上）を最大5件表示します",
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