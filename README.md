# 🎬 FANZA Discord Bot

FANZAのセール情報から高評価作品を自動取得して表示するDiscord BOTです。

## ✨ 機能

- 🎯 **スラッシュコマンド対応** - モダンなDiscordコマンド体験
- 🔍 **動的スクレイピング** - Playwrightによる最新情報取得
- ⭐ **高評価フィルタ** - 評価4.0以上の作品のみを厳選
- 📊 **評価順表示** - 上位5作品を評価順で表示
- 🎨 **美しいEmbed** - Discord Embedによる見やすい表示
- ⚡ **キャッシュシステム** - 1時間のキャッシュでAPI負荷軽減
- 🔒 **NSFW制限** - NSFWチャンネルでのみ動作
- ⏱️ **レート制限** - 5分に1回の適切な制限

## 🚀 クイックスタート

### 1. Botを招待
以下のリンクからBotをサーバーに招待：
```
https://discord.com/api/oauth2/authorize?client_id=1378875279556214804&permissions=2147483648&scope=bot%20applications.commands
```

### 2. NSFWチャンネルで使用
チャンネル設定でNSFWを有効化してから以下のコマンドを使用：
- `/fanza_sale` - セール中の高評価作品を表示
- `/help` - ヘルプを表示

## 🛠️ セルフホスト手順

自分でBotを動かしたい場合の手順：

### 前提条件
- **Python 3.9以上**
- **Git**
- **Discord Bot アカウント**

### 1. プロジェクトのクローン
```bash
git clone https://github.com/lalalasyun/fanza-discord-bot.git
cd fanza-discord-bot
```

### 2. 仮想環境のセットアップ
```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
playwright install chromium
```

### 3. Ubuntu/Debian系の場合の追加設定
```bash
# Playwrightの依存関係をインストール
sudo apt update
sudo apt install -y libnss3 libnspr4 libasound2t64
```

### 4. Discord Bot設定

#### 4.1 Discord Developer Portalでの設定
1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」でアプリケーションを作成
3. 「Bot」タブで「MESSAGE CONTENT INTENT」を有効化
4. Botトークンをコピー

#### 4.2 環境変数の設定
`.env.example`を`.env`にコピーしてトークンを設定：
```bash
cp .env.example .env
# .envファイルを編集
DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
```

### 5. Botの起動
```bash
# 仮想環境が有効化されていることを確認
source venv/bin/activate

# Botを起動
python bot.py
```

### 6. サーバーへの招待
以下のリンクでBotをサーバーに招待（CLIENT_IDを自分のものに変更）：
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147483648&scope=bot%20applications.commands
```

## 📋 使用方法

### スラッシュコマンド（推奨）
- `/fanza_sale` - セール中の高評価作品を表示
- `/help` - ヘルプを表示（プライベート応答）

### プレフィックスコマンド（レガシー対応）
- `!fanza_sale` - セール中の高評価作品を表示
- `!help_fanza` - ヘルプを表示
- `!sync` - スラッシュコマンドを手動同期（オーナー専用）

## ⚠️ 制限事項

- **NSFWチャンネル必須** - 年齢制限コンテンツのため
- **レート制限** - 同一ユーザーは5分に1回まで
- **キャッシュ** - 1時間のキャッシュで負荷軽減
- **年齢制限** - 18歳未満の使用は禁止

## 🔧 設定のカスタマイズ

`config.py`で以下の設定を変更可能：

```python
MIN_RATING = 4.0          # 表示する最低評価
MAX_ITEMS = 5             # 表示する最大件数
CACHE_DURATION = 3600     # キャッシュ保持時間（秒）
RATE_LIMIT_DURATION = 300 # レート制限時間（秒）
```

## 🐛 トラブルシューティング

### Botが起動しない場合
1. **Pythonバージョン確認**: `python --version`（3.9以上必要）
2. **仮想環境確認**: `source venv/bin/activate`が実行されているか
3. **トークン確認**: `.env`ファイルにトークンが正しく設定されているか
4. **依存関係確認**: `pip install -r requirements.txt`が完了しているか

### スラッシュコマンドが表示されない場合
1. **権限確認**: 正しい招待リンクを使用しているか
2. **同期確認**: `!sync`コマンドで手動同期を試す
3. **Discord再起動**: Discordアプリを再起動
4. **時間待機**: 最大1時間程度で反映される場合がある

### Playwright関連エラー
```bash
# 依存関係の再インストール
playwright install chromium
sudo apt install -y libnss3 libnspr4 libasound2t64
```

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します！

## ⚡ クイック起動コマンド

```bash
# プロジェクトディレクトリに移動
cd fanza-discord-bot

# 仮想環境を有効化してBot起動
source venv/bin/activate && python bot.py
```