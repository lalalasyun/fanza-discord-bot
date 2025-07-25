# 🎬 FANZA Discord Bot

FANZAのセール情報から高評価作品を自動取得し、MissAVで動画検索もできる多機能Discord BOTです。

**🆕 新機能**: 
- **メディアタイプ別検索** - 2D動画とVR作品を個別に検索可能！
- MissAV検索機能を追加！タイトルや女優名で直接動画を検索できます
- FANZAセール情報にMissAV動画URLを自動追加！各作品の視聴リンクが表示されます

## ✨ 機能

### 🎬 FANZA機能
- 🎯 **スラッシュコマンド対応** - モダンなDiscordコマンド体験
- 🎥 **メディアタイプ別検索** - 2D動画とVR作品を個別に検索可能
- 🔍 **動的スクレイピング** - Playwrightによる最新情報取得
- ⭐ **高評価フィルタ** - 評価4.0以上の作品のみを厳選
- 📊 **評価順表示** - 上位5作品を評価順で表示
- 🎨 **美しいEmbed** - Discord Embedによる見やすい表示
- ⚡ **キャッシュシステム** - 1時間のキャッシュでAPI負荷軽減
- 🔗 **MissAV自動連携** - 各作品のMissAV視聴URLを自動検索・表示

### 🔍 MissAV検索機能 **NEW!**
- 🎯 **タイトル検索** - 日本語タイトルで動画を直接検索
- 📺 **動画情報取得** - タイトル、視聴URL、サムネイル、再生時間
- 🔗 **直接視聴** - 検索結果から直接動画ページにアクセス
- 🎪 **関連性スコア** - 検索クエリとの一致度を数値化
- ⚡ **高速キャッシュ** - 30分間のインテリジェントキャッシュ

### 🔒 共通セキュリティ機能
- 🔒 **NSFW制限** - NSFWチャンネルでのみ動作
- ⏱️ **レート制限** - 5分に1回の適切な制限
- 🛡️ **18歳未満利用禁止** - 年齢制限の厳格な適用

## 🚀 クイックスタート

### 1. Botを招待
以下のリンクからBotをサーバーに招待：
```
https://discord.com/api/oauth2/authorize?client_id=1378875279556214804&permissions=2147483648&scope=bot%20applications.commands
```

### 2. NSFWチャンネルで使用
チャンネル設定でNSFWを有効化してから以下のコマンドを使用：
- `/fanza_sale` - セール中の高評価作品を表示（2D+VR両方対応）
- `/fanza_sale_2d` - **NEW!** セール中の高評価2D動画のみを表示
- `/fanza_sale_vr` - **NEW!** セール中の高評価VR作品のみを表示
- `/missav_search [タイトル]` - MissAVで動画を検索
- `/help` - ヘルプを表示

#### 🔍 MissAV検索例
```
/missav_search 乃々瀬あい
/missav_search SSIS-960
/missav_search 嫁の連れ子をイラマチオ！ゴミ部屋に引きこもる反抗期の義娘を失禁するまで喉奥ピストン 乃々瀬あい
```

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

# 開発環境設定（オプション）
DISABLE_RATE_LIMIT=true  # 開発時のレート制限を無効化
```

**開発環境での設定:**
- `DISABLE_RATE_LIMIT=true` - レート制限を無効化（開発・テスト用）
- `DISABLE_RATE_LIMIT=false` または未設定 - レート制限を有効化（本番用）

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

#### 🎬 FANZA関連
- `/fanza_sale` - セール中の高評価作品を表示（2D+VR両方対応）
- `/fanza_sale_2d` - **NEW!** セール中の高評価2D動画のみを表示
- `/fanza_sale_vr` - **NEW!** セール中の高評価VR作品のみを表示

**共通オプション**:
- `mode` オプション:
  - 🏆 評価順（デフォルト） - 評価の高い順に表示
  - 🎲 ランダム - ランダムな順序で表示
  - 📋 リスト形式 - ページネーション付きコンパクト表示（5件/ページ、最大50件）
- `sale_type` オプション:
  - 🎯 全てのセール（デフォルト）
  - ⏰ 期間限定セール
  - 💸 割引セール (20-70% OFF)
  - 📅 日替わりセール
  - 💴 激安セール (10円/100円)
- **MissAV連携**: 各作品のMissAV視聴URLを自動で検索・表示

**使用例**:
```
/fanza_sale mode:評価順 sale_type:全てのセール
/fanza_sale_2d mode:ランダム sale_type:割引セール
/fanza_sale_vr mode:リスト形式 sale_type:期間限定セール
```

#### 🔍 MissAV検索 **NEW!**
- `/missav_search [タイトル]` - MissAVで動画を検索
  - **対応タイトル形式**:
    - 女優名: `乃々瀬あい`、`椎名ゆな`
    - 品番: `SSIS-960`、`CAWD-845`
    - 完全タイトル: `「私のオッパイの方が気持ちいいよ」彼女ができた僕に嫉妬した女友達が...`
    - 部分キーワード: `イラマチオ`、`義娘`
  - **取得情報**: タイトル、視聴URL、サムネイル、再生時間
  - **検索結果**: 最大5件、関連性順で表示

#### 💡 ヘルプ・情報
- `/help` - ヘルプを表示（プライベート応答）
- `/bot_info` - BOTの詳細情報とステータスを表示

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

### FANZA関連設定
```python
MIN_RATING = 4.0          # 表示する最低評価
MAX_ITEMS = 5             # 表示する最大件数
CACHE_DURATION = 3600     # キャッシュ保持時間（秒）
RATE_LIMIT_DURATION = 300 # レート制限時間（秒）
```

### MissAV関連設定
```python
# missav_scraper.pyで変更可能
CACHE_DURATION = 1800     # MissAVキャッシュ保持時間（30分）
MISSAV_BASE_URL = "https://missav123.com"  # ベースURL
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

### MissAV検索で結果が出ない場合
1. **タイトル確認**: 正確なタイトルまたはキーワードを使用
2. **ネットワーク確認**: MissAVサイトへのアクセスが可能か確認
3. **キャッシュリセット**: 30分待ってから再度検索
4. **キーワード変更**: 女優名や品番などシンプルなキーワードで検索

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します！

### 🧪 PRのテスト方法（WSL環境）

WSL環境では、PRブランチから直接Botをテストできます：

```bash
# PR番号を指定してテスト
./update_bot_pr.sh 123

# ブランチ名を指定してテスト
./update_bot_pr.sh feature/new-feature
```

テスト後、mainブランチに戻るには：
```bash
./update_bot.sh
```

詳細は[WSL運用ガイド](README_WSL.md)を参照してください。

## ⚡ クイック起動コマンド

```bash
# プロジェクトディレクトリに移動
cd fanza-discord-bot

# 仮想環境を有効化してBot起動
source venv/bin/activate && python bot.py
```