@echo off
setlocal

:: ── Sequential Image Viewer ─────────────────────────────────────
::  このバッチファイルをダブルクリックするだけで起動します
:: ────────────────────────────────────────────────────────────────

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv"
set "REQS_FILE=%APP_DIR%requirements.txt"

echo ============================================
echo   SEQ VIEWER  -  Sequential Image Viewer
echo ============================================

:: Python確認
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。
    echo         https://www.python.org からインストールしてください。
    pause
    exit /b 1
)

:: 仮想環境がなければ作成
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [SETUP] 仮想環境を作成中...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 仮想環境の作成に失敗しました。
        pause
        exit /b 1
    )
)

:: 仮想環境有効化
call "%VENV_DIR%\Scripts\activate.bat"

:: 依存関係インストール確認（flask がなければインストール）
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] ライブラリをインストール中...
    pip install -r "%REQS_FILE%" --quiet
    if errorlevel 1 (
        echo [ERROR] インストールに失敗しました。
        pause
        exit /b 1
    )
    echo [SETUP] インストール完了
) else (
    echo [OK] ライブラリ確認済み
)

:: ffmpeg 確認（任意）
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [INFO] ffmpeg が見つかりません。動画変換には ffmpeg が必要です。
) else (
    echo [OK] ffmpeg 検出済み
)

echo.
echo  ブラウザで開く:  http://localhost:5000
echo  終了: Ctrl+C
echo.

:: アプリ起動
python "%APP_DIR%app.py" >nul 2>&1

pause
