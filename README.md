![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)
# TerMa (TerminalMangaViewer)

> **Ter**minal **Ma**nga Viewer — *"タマ"*

> TerMa は **Kitty** / **WezTerm** / **Sixel対応ターミナル** などに対応したターミナル漫画ビューアです。Kitty Graphics Protocol、WezTerm imgcat、または Sixel グラフィックスを使って表紙と見開きを表示し、キーボード操作を中心にマウス操作もサポートします。Python と curses を使って、ターミナル上で完結し、片手で全ての操作を行えることを目標としています。

## 日本語版

Kitty、WezTerm、Sixel対応ターミナル向けの漫画ビューアです。
表紙は中央に表示され、2枚目以降は右綴じの見開き表示を行います。

### 特徴

- 1枚目は表紙として中央表示し、2枚目以降は右綴じの見開き表示を行います
- Kitty、WezTerm、Sixel対応ターミナルを自動検出して、対応する画像プロトコルを切り替えます
- キーボード主体の操作に加え、マウスクリックにも対応します
- 兄弟ディレクトリを自然順で辿って、次の巻へ移動できます
- 通常フォルダとアーカイブの前回表示位置を自動で保存・復元します
- Pillow を入れると、画像の縦横比を正確に判定して表示を安定させます
- `TERMA_DEBUG=1` でデバッグログを有効化できます

### サンプル画像

![表紙表示](assets/sample-cover.jpg)
*表紙ページは中央に表示されます*

![見開き表示](assets/sample-spread.jpg)
*2枚目以降は見開き（右綴じ）で表示されます*

### 必要要件

| 項目 | 内容 |
|------|------|
| Python | 3.8 以上 |
| ターミナル | Kitty / WezTerm / Sixel対応ターミナル |
| Pillow | **強く推奨・標準インストール**。画像のアスペクト比を正確に判定します |

### インストール

#### ゼロからのインストール手順

```bash
# 1. Python 3.8 以上をインストール
# 2. git をインストール
# 3. make をインストール（base-devel / build-essential）
#    Arch Linux:  sudo pacman -S base-devel
#    Ubuntu:      sudo apt install build-essential
#    macOS:       xcode-select --install

# 4. リポジトリを取得
git clone https://github.com/radiconkid/TerminalMangaViewer.git
cd TerminalMangaViewer

# 5. インストール（uv・venv・Pythonパッケージ・chafa確認を自動実行）
make install
```

`make install` は以下の処理を自動で行います：

- uv が未インストールなら自動インストール
- 仮想環境 (venv) の作成
- Pillow を含む Python パッケージのインストール
- chafa（画像変換ツール）の有無を確認し、なければインストール方法を表示

#### 手動インストール

```bash
python3 -m pip install Pillow
python3 -m pip install .
```

#### ビルド済み実行ファイル（GitHub Releases）

各OS向けのスタンドアロン実行ファイルを [Releases](https://github.com/radiconkid/TerminalMangaViewer/releases) で配布しています。
Python 環境がなくてもダウンロードしてそのまま実行できます。

```bash
# Linux / macOS
./terma-linux-x86_64 /path/to/manga

# Windows
terma-windows-x86_64.exe C:\path\to\manga
```

> **注意**: chafa は別途インストールが必要です。
> 実行ファイルに含まれていないため、お使いのOSのパッケージマネージャでインストールしてください。

### 使い方

```bash
./terma.py /path/to/manga/volume01
```

`volume01` と同階層にある兄弟ディレクトリが、自動的に次の巻として認識されます。

```text
manga/
├── volume01/   ← ここを指定すると…
├── volume02/   ← 次の巻として自動認識
└── volume03/
```

前回表示していた巻とページは自動的に保存され、同じフォルダまたはアーカイブを開くと続きから再開します。
レジューム情報は `~/.terma_resume.json` に保存されます。

### キーバインド

| キー | 動作 |
|------|------|
| `j` / `←` / `Enter` | 次のページへ |
| `k` / `l` / `→` | 前のページへ |
| `0` | 最初のページ（表紙）へ |
| `J` / `Shift` + `←` | 10ページ進む（ターボ） |
| `K` / `Shift` + `→` | 10ページ戻る（ターボ） |
| `1`〜`9` | 全体の 10%〜90% の位置へ移動 |
| `c` | カバーモードの切り替え（表紙表示あり/なし） |
| `r` | 読書方向の切り替え（右綴じ/左綴じ） |
| `,` | 次の巻へ |
| `.` | 前の巻へ |
| `q` / `Q` / `h` | 終了 |

### マウス操作

| 操作 | 動作 |
|------|------|
| 左クリック | 次のページへ |
| 右クリック | 前のページへ |
| 中クリック | 終了 |

### ターミナル対応

**動作確認済み**

| ターミナル | プロトコル | 検出方法 |
|------------|-----------|---------|
| Kitty | Kitty Graphics Protocol（icat） | `KITTY_WINDOW_ID` 環境変数 |
| WezTerm | Sixel（chafa） | `WEZTERM_PANE` / `WEZTERM_UNIX_SOCKET` 環境変数 |
| foot | Sixel（chafa） | `TERM=foot*` |
| Windows Terminal | Sixel（chafa） | `WT_SESSION` 環境変数 |

**その他対応（理論上動作）**

| ターミナル | プロトコル | 検出方法 |
|------------|-----------|---------|
| XTerm互換端末 | Sixel（chafa） | `TERM` に `xterm` を含み `COLORTERM=truecolor` |
| mintty (Cygwin/MSYS2) | Sixel（chafa） | `TERM_PROGRAM=mintty` |
| mlterm / Contour | Sixel（chafa） | `TERM` の値で判定 |

tmux 経由でも環境変数による判定が有効です。

### デバッグ

```bash
TERMA_DEBUG=1 ./terma.py /path/to/manga/volume01
```

ログは `~/terma-debug.log` に出力されます。

### プロジェクト構成

```text
TerminalMangaViewer/
├── terma.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### コントリビューション

Issue・PR ともに歓迎します。

- バグ報告の際は OS・ターミナル名・バージョン・デバッグログを添えてください
- 機能追加の提案は Issue で先に議論していただけると助かります

### ライセンス

[MIT](LICENSE)

---

## English

TerMa is a terminal manga viewer for **Kitty**, **WezTerm**, and Sixel-compatible terminals.
It shows the cover page in the center and, from the second page onward, displays spreads in right-to-left reading order.

### Features

- The first page is shown as a centered cover page.
- From the second page onward, the viewer displays spreads using a right-bound layout.
- Kitty, WezTerm, and Sixel-compatible terminals are detected automatically, and the corresponding image protocol is selected.
- The application is keyboard-first and also supports mouse clicks.
- Sibling directories are traversed in natural sort order so the next volume is discovered automatically.
- The last viewed position is saved and restored automatically for normal folders and archives.
- Installing Pillow improves aspect-ratio detection and makes layout behavior more reliable.
- `TERMA_DEBUG=1` enables debug logging.

### Sample Images

![Cover display](assets/sample-cover.jpg)
*The cover page is shown in the center.*

![Spread display](assets/sample-spread.jpg)
*From the second page onward, the viewer shows spreads in right-to-left order.*

### Requirements

| Item | Details |
|------|---------|
| Python | 3.8 or newer |
| Terminal | Kitty, WezTerm, or Sixel-compatible terminals |
| Pillow | **Strongly recommended and installed by default** for accurate aspect-ratio detection |

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/radiconkid/TerminalMangaViewer.git
cd TerminalMangaViewer
```

#### 2. Use the standard install

```bash
python3 -m pip install Pillow
python3 -m pip install .
```

`pip install .` installs Pillow by default, so this is usually sufficient.
If you use `pipx install .`, Pillow is included as part of the standard install.

#### 3. Run directly

```bash
python3 terma.py /path/to/manga/volume01
```

#### 4. Install with pipx

```bash
pipx install .
```

#### 5. Upgrade or reinstall with pipx

```bash
pipx upgrade terma
pipx reinstall terma
pipx install . --force
```

### Usage

```bash
./terma.py /path/to/manga/volume01
```

Sibling directories next to `volume01` are automatically detected as the next volume.

```text
manga/
├── volume01/   ← start here
├── volume02/   ← automatically recognized as the next volume
└── volume03/
```

The last viewed volume and page are saved automatically, so opening the same folder or archive resumes from that position.
Resume data is stored in `~/.terma_resume.json`.

### Key Bindings

| Key | Action |
|------|--------|
| `j` / `←` / `Enter` | Move to the next page |
| `k` / `l` / `→` | Move to the previous page |
| `0` | Jump to the first page (cover) |
| `J` / `Shift` + `←` | Move forward 10 pages (Turbo) |
| `K` / `Shift` + `→` | Move backward 10 pages (Turbo) |
| `1`〜`9` | Jump to 10% through 90% progress |
| `c` | Toggle cover mode (cover page on/off) |
| `r` | Toggle reading direction (right-to-left / left-to-right) |
| `,` | Move to the next volume |
| `.` | Move to the previous volume |
| `q` / `Q` / `h` | Quit |

### Mouse Controls

| Action | Behavior |
|--------|----------|
| Left click | Move to the next page |
| Right click | Move to the previous page |
| Middle click | Quit |

### Terminal Support

| Terminal | Protocol | Detection |
|----------|----------|-----------|
| Kitty | Kitty Graphics Protocol (`icat`) | `KITTY_WINDOW_ID` environment variable |
| WezTerm | imgcat | `WEZTERM_PANE` / `WEZTERM_UNIX_SOCKET` environment variables |
| Windows Terminal | Sixel (chafa) | `WT_SESSION` environment variable |
| foot | Sixel (chafa) | `TERM=foot*` |
| XTerm-compatible | Sixel (chafa) | `TERM` contains `xterm` and `COLORTERM=truecolor` |
| mintty (Cygwin/MSYS2) | Sixel (chafa) | `TERM_PROGRAM=mintty` |
| mlterm / Contour | Sixel (chafa) | `TERM` value |

Environment variable detection also works when launched from tmux.
If no Sixel support is detected, WezTerm's imgcat is used as a fallback.

### Debug

```bash
TERMA_DEBUG=1 ./terma.py /path/to/manga/volume01
```

Logs are written to `~/terma-debug.log`.

### Project Structure

```text
TerminalMangaViewer/
├── terma.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### Contributing

Issues and pull requests are welcome.

- Include your OS, terminal name, version, and debug log when reporting a bug.
- Feature ideas are best discussed in an issue before implementation.

### License

[MIT](LICENSE)
