#!/bin/bash
# ── Sequential Image Viewer ──────────────────────────────────────
#  実行: bash start.sh  または  ./start.sh
# ────────────────────────────────────────────────────────────────

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"

echo "============================================"
echo "  SEQ VIEWER  -  Sequential Image Viewer"
echo "============================================"

# Python確認 (python3 or python)
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "[ERROR] Python が見つかりません。"
    echo "        https://www.python.org からインストールしてください。"
    exit 1
fi

echo "[OK] Python: $($PYTHON --version)"

# 仮想環境がなければ作成
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[SETUP] 仮想環境を作成中..."
    $PYTHON -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[ERROR] 仮想環境の作成に失敗しました。"
        exit 1
    fi
fi

# 仮想環境有効化
source "$VENV_DIR/bin/activate"

# flask インストール確認
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[SETUP] ライブラリをインストール中..."
    pip install -r "$APP_DIR/requirements.txt" -q
    if [ $? -ne 0 ]; then
        echo "[ERROR] インストールに失敗しました。"
        exit 1
    fi
    echo "[SETUP] インストール完了"
else
    echo "[OK] ライブラリ確認済み"
fi

# ffmpeg 確認（任意）
if command -v ffmpeg &>/dev/null; then
    echo "[OK] ffmpeg 検出済み"
else
    echo "[INFO] ffmpeg が見つかりません。動画変換には ffmpeg が必要です。"
fi

echo ""
echo "  ブラウザで開く:  http://localhost:5000"
echo "  終了: Ctrl+C"
echo ""

# ブラウザ自動起動（任意）
if command -v open &>/dev/null; then
    sleep 1.5 && open "http://localhost:5000" &
elif command -v xdg-open &>/dev/null; then
    sleep 1.5 && xdg-open "http://localhost:5000" &
fi

# アプリ起動
python "$APP_DIR/app.py" &>/dev/null
