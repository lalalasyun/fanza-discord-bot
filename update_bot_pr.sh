#!/bin/bash

# FANZA Discord Bot PRテスト用アップデートスクリプト
# GitHub PRから最新の変更を取得してWSL環境に適用

BOT_DIR="/home/syun/fanza-discord-bot"
BACKUP_DIR="/home/syun/fanza-bot-backup-$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$BOT_DIR/update.log"

# PR番号またはブランチ名を引数から取得
PR_OR_BRANCH="${1}"

if [ -z "$PR_OR_BRANCH" ]; then
    echo "❌ エラー: PR番号またはブランチ名を指定してください"
    echo ""
    echo "使用方法:"
    echo "  PR番号を指定:      ./update_bot_pr.sh 123"
    echo "  ブランチ名を指定:  ./update_bot_pr.sh feature/new-feature"
    echo ""
    echo "例:"
    echo "  ./update_bot_pr.sh 7"
    echo "  ./update_bot_pr.sh test/bot-pr-testing"
    exit 1
fi

echo "🔄 FANZA Discord Bot PRテスト用アップデートスクリプト"
echo "📁 プロジェクトディレクトリ: $BOT_DIR"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# プロジェクトディレクトリに移動
cd "$BOT_DIR" || {
    echo "❌ エラー: プロジェクトディレクトリが見つかりません"
    exit 1
}

log "🚀 PRアップデート開始"

# 数字のみの場合はPR番号として扱う
if [[ "$PR_OR_BRANCH" =~ ^[0-9]+$ ]]; then
    PR_NUMBER="$PR_OR_BRANCH"
    echo "📌 PR #$PR_NUMBER から取得します"
    
    # ghコマンドが利用可能か確認
    if ! command -v gh &> /dev/null; then
        echo "❌ GitHub CLIがインストールされていません"
        echo "💡 以下のコマンドでインストールしてください:"
        echo "   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
        echo "   echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null"
        echo "   sudo apt update && sudo apt install gh"
        exit 1
    fi
    
    # PRの情報を取得
    echo "📡 PR情報を取得中..."
    PR_INFO=$(gh pr view $PR_NUMBER --json headRefName,state 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo "❌ PR #$PR_NUMBER の情報を取得できませんでした"
        exit 1
    fi
    
    BRANCH=$(echo "$PR_INFO" | jq -r '.headRefName')
    PR_STATE=$(echo "$PR_INFO" | jq -r '.state')
    
    echo "🌿 PRブランチ: $BRANCH"
    echo "📊 PR状態: $PR_STATE"
    
    if [ "$PR_STATE" = "CLOSED" ] || [ "$PR_STATE" = "MERGED" ]; then
        echo "⚠️  警告: このPRは既にクローズ/マージされています"
        read -p "続行しますか? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            exit 0
        fi
    fi
else
    # ブランチ名として扱う
    BRANCH="$PR_OR_BRANCH"
    echo "🌿 ブランチ: $BRANCH"
fi

# 現在のBot状態を確認
echo "📊 現在のBot状態を確認中..."
BOT_RUNNING=false
BOT_PROCESSES=$(pgrep -f "python.*bot.py")
USERNAME=$(whoami)
SERVICE_ACTIVE=$(systemctl is-active fanza-bot@$USERNAME.service 2>/dev/null || echo "inactive")
SCREEN_SESSIONS=$(screen -list 2>/dev/null | grep fanza-bot || echo "")

if [ -n "$BOT_PROCESSES" ] || [ "$SERVICE_ACTIVE" = "active" ] || [ -n "$SCREEN_SESSIONS" ]; then
    BOT_RUNNING=true
    echo "🟡 Bot実行中を検出"
    
    read -p "🛑 アップデート前にBotを停止しますか? (推奨) (y/n): " stop_bot
    if [ "$stop_bot" = "y" ]; then
        echo "🛑 Bot停止中..."
        if systemctl is-active --quiet fanza-bot@$USERNAME.service 2>/dev/null; then
            sudo systemctl stop fanza-bot@$USERNAME.service
            echo "✅ systemdサービスを停止しました"
        else
            pkill -TERM -f "python.*bot.py"
            echo "✅ Botプロセスを停止しました"
        fi
        sleep 2
    fi
fi

# 現在の状態をバックアップ
echo "💾 現在の状態をバックアップ中..."
cp -r "$BOT_DIR" "$BACKUP_DIR"
log "📁 バックアップ作成: $BACKUP_DIR"

# Git状態確認
echo "📋 Git状態確認中..."
git status --porcelain

# ローカル変更があるかチェック
TRACKED_CHANGES=$(git status --porcelain | grep -v -E "^\?\? (fanza-bot\.service|start_bot\.sh|stop_bot\.sh|update_bot\.sh|update_bot_pr\.sh|test_wsl\.py|README_WSL\.md|.*\.log)$")

if [ -n "$TRACKED_CHANGES" ]; then
    echo "⚠️  ローカルに未コミットの変更があります"
    echo "🗑️  PRテストのため、ローカル変更を破棄します"
    git reset --hard HEAD
    git clean -fd -e "fanza-bot.service" -e "start_bot.sh" -e "stop_bot.sh" -e "update_bot.sh" -e "update_bot_pr.sh" -e "test_wsl.py" -e "README_WSL.md" -e "*.log"
    log "🗑️  ローカル変更を破棄（WSLファイルは保持）"
fi

# リモートから最新情報を取得
echo "📡 リモートから最新情報を取得中..."
git fetch origin "$BRANCH" || {
    echo "❌ ブランチ '$BRANCH' の取得に失敗しました"
    echo "💡 ブランチ名が正しいか確認してください"
    log "❌ git fetch失敗: $BRANCH"
    exit 1
}

# 現在のブランチを確認
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 現在のブランチ: $CURRENT_BRANCH"

# ブランチをチェックアウト
echo "🔄 ブランチ '$BRANCH' に切り替え中..."
git checkout -B "$BRANCH" "origin/$BRANCH" || {
    echo "❌ ブランチの切り替えに失敗しました"
    log "❌ git checkout失敗: $BRANCH"
    
    # バックアップから復旧
    echo "🔄 バックアップから復旧中..."
    rm -rf "$BOT_DIR"
    cp -r "$BACKUP_DIR" "$BOT_DIR"
    cd "$BOT_DIR"
    git checkout "$CURRENT_BRANCH"
    echo "✅ バックアップから復旧完了"
    exit 1
}

log "✅ ブランチ切り替え完了: $CURRENT_BRANCH -> $BRANCH"

# 依存関係の更新チェック
echo "📦 依存関係の更新チェック中..."
if [ -f "requirements.txt" ]; then
    echo "📦 Pythonパッケージを更新中..."
    source venv/bin/activate
    pip install -r requirements.txt --upgrade || {
        echo "⚠️  パッケージの更新に失敗しました"
        log "⚠️  pip install失敗"
    }
    
    # Playwrightブラウザの更新
    playwright install chromium || {
        echo "⚠️  Playwrightブラウザの更新に失敗しました"
        log "⚠️  playwright install失敗"
    }
    
    log "📦 依存関係更新完了"
fi

# 設定ファイルの確認
echo "⚙️  設定ファイル確認中..."
if [ ! -f ".env" ]; then
    echo "⚠️  .envファイルが見つかりません"
    if [ -f ".env.example" ]; then
        echo "💡 .env.exampleから.envを作成してください"
    fi
fi

# 更新完了
echo ""
echo "🎉 PRテスト用アップデート完了!"
log "🎉 PRアップデート成功: $BRANCH"

# 現在の状態を表示
echo ""
echo "📋 現在の状態:"
echo "  ブランチ: $BRANCH"
echo "  コミット: $(git rev-parse --short HEAD)"
echo "  バックアップ: $BACKUP_DIR"

# Bot再起動の提案
if [ "$BOT_RUNNING" = true ]; then
    echo ""
    read -p "🚀 Botを再起動しますか? (推奨) (y/n): " restart_bot
    if [ "$restart_bot" = "y" ]; then
        echo "🚀 Bot再起動中..."
        ./start_bot.sh
        log "🚀 Bot再起動完了"
    fi
else
    echo ""
    echo "💡 Botを起動するには: ./start_bot.sh"
fi

# mainブランチに戻る提案
echo ""
echo "💡 テスト完了後、mainブランチに戻るには:"
echo "   ./update_bot.sh"
echo ""
echo "✨ PRテスト環境の準備完了!"
log "✨ PRテスト処理完了"