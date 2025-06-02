# FANZA Discord Bot

FANZAのセール情報から高評価作品を取得して表示するDiscord BOTです。

## 機能

- `!fanza_sale` コマンドでセール中の高評価AV作品を表示
- 評価4.0以上の作品のみを抽出
- 上位5作品を評価順で表示
- Discord Embedを使用した見やすい表示形式
- キャッシュ機能（1時間）でAPI負荷軽減
- NSFWチャンネルでのみ動作

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 環境変数の設定

`.env`ファイルを作成し、Discord Botトークンを設定：

```
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```

### 3. Discord設定

1. [Discord Developer Portal](https://discord.com/developers/applications)でMESSAGE CONTENT INTENTを有効化
2. 以下のリンクでBotをサーバーに招待：
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=3072&scope=bot
   ```

### 4. Botの起動

```bash
python bot.py
```

## 使用方法

NSFWチャンネルで以下のコマンドを使用：

- `!fanza_sale` - セール中の高評価作品を表示
- `!help_fanza` - ヘルプを表示

## 制限事項

- NSFWチャンネルでのみ使用可能
- 5分に1回のレート制限
- キャッシュは1時間保持

## 設定のカスタマイズ

`config.py`で設定を変更できます：

- `MIN_RATING`: 表示する最低評価（デフォルト: 4.0）
- `MAX_ITEMS`: 表示する最大件数（デフォルト: 5）
- `CACHE_DURATION`: キャッシュ保持時間（デフォルト: 3600秒）
- `RATE_LIMIT_DURATION`: レート制限時間（デフォルト: 300秒）