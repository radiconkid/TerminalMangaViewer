# Changelog / 変更履歴

All notable changes to this project will be documented in this file. / 本プロジェクトの重要な変更はこのファイルに記録します。

## [0.2.3] - 2026-05-25

### Changed / 変更
- Added landscape-page detection so wide pages are shown as single-page displays instead of spreads / 横長ページを検出し、見開きではなく単ページ表示になるように変更
- Unified navigation step size so page movement matches the current display mode / 表示モードに合わせてページ移動のステップ幅を統一
- Updated display status text to reflect single-page rendering / 単ページ表示に合わせて表示ステータステキストを更新

### Fixed / 修正
- Inconsistent spread/single behavior when the current or next page was landscape-oriented / 現在ページまたは次ページが横長の場合に、見開き表示と単ページ表示の挙動が不一致になる問題を修正
- Pipx-installed execution now matches local `python3 terma.py` behavior when Pillow is available / Pillow が利用可能な場合、pipx 経由の実行がローカルの `python3 terma.py` と同じ挙動になるように修正

## [0.2.2] - 2026-04-20

### Changed / 変更
- Updated version to 0.2.2 in `pyproject.toml` and `terma.py` / `pyproject.toml` と `terma.py` のバージョンを 0.2.2 に更新
- Use absolute paths for image files in Kitty and WezTerm renderers / Kitty と WezTerm のレンダラーで画像ファイルの絶対パスを使用するように変更
- Improved directory navigation with better path resolution / パス解決を改善してディレクトリ移動を安定化

### Fixed / 修正
- Path resolution issues in Kitty and WezTerm image rendering / Kitty と WezTerm の画像描画におけるパス解決の問題を修正
- Windows/ANSI terminal display escape code issues / Windows と ANSI ターミナルでのエスケープコード表示の問題を修正
- Directory index lookup for initial directory selection / 初期ディレクトリ選択時のディレクトリインデックス参照を修正

## [0.2.1] - 2026-04-20

### Added / 追加
- Windows compatibility using `msvcrt` for terminal operations / ターミナル操作に `msvcrt` を使った Windows 対応を追加
- Debug output for WezTerm/Kitty commands (enabled with `TERMA_DEBUG=1`) / WezTerm/Kitty コマンドのデバッグ出力を追加（`TERMA_DEBUG=1` で有効）
- Sample images in `README.md` / `README.md` にサンプル画像を追加
- Version constant in `terma.py` / `terma.py` にバージョン定数を追加
- `CHANGELOG.md` file / `CHANGELOG.md` を追加

### Changed / 変更
- Updated version to 0.2.1 in `pyproject.toml` and `terma.py` / `pyproject.toml` と `terma.py` のバージョンを 0.2.1 に更新
- Refactored terminal handling to support both curses (Unix) and `msvcrt` (Windows) / Unix 用の curses と Windows 用の `msvcrt` の両方に対応するように端末処理を整理
- Improved error handling and terminal detection / エラー処理とターミナル検出を改善
- Added debug statements throughout the codebase / コードベース全体にデバッグ用のログ出力を追加

### Fixed / 修正
- Windows terminal compatibility issues / Windows ターミナル互換性の問題を修正
- Missing debug output for command execution / コマンド実行時のデバッグ出力不足を修正
- Terminal size detection on Windows / Windows でのターミナルサイズ検出を修正

## [0.2.0] - 2026-04-20

### Added / 追加
- Initial Windows support / 初期の Windows 対応を追加
- Basic debug functionality / 基本的なデバッグ機能を追加

## [0.1.2] - 2026-04-10

### Added / 追加
- Package installation support with `pyproject.toml` / `pyproject.toml` を使ったパッケージインストール対応を追加
- Argument handling improvements / 引数処理を改善
- `--help` option / `--help` オプションを追加

### Changed / 変更
- Enhanced argument parsing / 引数解析を強化
- Improved error messages / エラーメッセージを改善

## [0.1.1] - 2026-04-09

### Added / 追加
- Package installation support / パッケージインストール対応を追加
- `pyproject.toml` configuration / `pyproject.toml` の設定を追加

## [0.1.0] - 2026-04-08

### Added / 追加
- Initial implementation of TerMa v0.1.0 / TerMa v0.1.0 の初期実装を追加
- Kitty and WezTerm renderer support / Kitty と WezTerm のレンダラー対応を追加
- Basic manga viewing functionality / 基本的な漫画表示機能を追加
- Cover and spread page display / 表紙と見開き表示を追加
- Keyboard navigation (`j`/`k`/left/right) / キーボードナビゲーション（`j`/`k`/左右キー）を追加
- Mouse support / マウス操作を追加
