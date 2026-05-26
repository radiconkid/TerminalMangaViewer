# TerMa (TerminalMangaViewer)

> **Ter**minal **Ma**nga Viewer — *"タマ"*

> TerMa は Kitty / WezTerm 向けのターミナル漫画ビューアです。Kitty Graphics Protocol または WezTerm imgcat を使って表紙と見開きを表示し、キーボード操作を中心にマウス操作もサポートします。Python と curses を使って、ターミナル上で完結し、片手で全ての操作を行えることを目標としています。

## 日本語版

Kitty と WezTerm 向けのターミナル漫画ビューアです。
表紙は中央に表示され、2枚目以降は右綴じの見開き表示を行います。

### 特徴

- 1枚目は表紙として中央表示し、2枚目以降は右綴じの見開き表示を行います
- Kitty か WezTerm を自動検出して、対応する画像プロトコルを切り替えます
- キーボード主体の操作に加え、マウスクリックにも対応します
- 兄弟ディレクトリを自然順で辿って、次の巻へ移動できます
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
| ターミナル | Kitty または WezTerm |
| Pillow | **強く推奨・標準インストール**。画像のアスペクト比を正確に判定します |

### インストール

#### 1. ソースコードを取得する

```bash
git clone https://github.com/radiconkid/TerminalMangaViewer.git
cd TerminalMangaViewer
```

#### 2. 標準インストールを行う

```bash
python3 -m pip install Pillow
python3 -m pip install .
```

`pip install .` では Pillow が標準で入るため、通常はこの手順で十分です。
`pipx install .` を使う場合も、Pillow は標準インストールとして含まれます。

#### 3. そのまま実行する

```bash
python3 terma.py /path/to/manga/volume01
```

#### 4. pipx でインストールする

```bash
pipx install .
```

#### 5. pipx の更新・再インストール

```bash
pipx upgrade terma
pipx reinstall terma
pipx install . --force
```

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

### キーバインド

| キー | 動作 |
|------|------|
| `j` / `←` / `Enter` | 次のページへ |
| `k` / `l` / `→` | 前のページへ |
| `0` | 最初のページ（表紙）へ |
| `1`〜`9` | 全体の 10%〜90% の位置へ移動 |
| `,` | 次の巻へ |
| `.` | 前の巻へ |
| `q` / `Q` / `h` | 終了 |

### マウス操作

> ⚠️ マウス操作は現在不具合が多く、未完成です。

| 操作 | 動作 |
|------|------|
| 左クリック | 次のページへ |
| 右クリック | 前のページへ |
| 中クリック | 終了 |

### ターミナル対応

| ターミナル | プロトコル | 検出方法 |
|------------|-----------|---------|
| Kitty | Kitty Graphics Protocol（icat） | `KITTY_WINDOW_ID` 環境変数 |
| WezTerm | imgcat | `WEZTERM_PANE` 環境変数 |

tmux 経由でも環境変数による判定が有効です。

### デバッグ

```bash
MANGA_VIEWER_DEBUG=1 ./terma.py /path/to/manga/volume01
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

TerMa is a terminal manga viewer for **Kitty** and **WezTerm**.
It shows the cover page in the center and, from the second page onward, displays spreads in right-to-left reading order.

### Features

- The first page is shown as a centered cover page.
- From the second page onward, the viewer displays spreads using a right-bound layout.
- Kitty and WezTerm are detected automatically, and the corresponding image protocol is selected.
- The application is keyboard-first and also supports mouse clicks.
- Sibling directories are traversed in natural sort order so the next volume is discovered automatically.
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
| Terminal | Kitty or WezTerm |
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

### Key Bindings

| Key | Action |
|------|--------|
| `j` / `←` / `Enter` | Move to the next page |
| `k` / `l` / `→` | Move to the previous page |
| `0` | Jump to the first page (cover) |
| `1`〜`9` | Jump to 10% through 90% progress |
| `,` | Move to the next volume |
| `.` | Move to the previous volume |
| `q` / `Q` / `h` | Quit |

### Mouse Controls

> ⚠️ Mouse support is still incomplete and can be unreliable.

| Action | Behavior |
|--------|----------|
| Left click | Move to the next page |
| Right click | Move to the previous page |
| Middle click | Quit |

### Terminal Support

| Terminal | Protocol | Detection |
|----------|----------|-----------|
| Kitty | Kitty Graphics Protocol (`icat`) | `KITTY_WINDOW_ID` environment variable |
| WezTerm | imgcat | `WEZTERM_PANE` environment variable |

The environment variables above also work when the app is launched from tmux.

### Debug

```bash
MANGA_VIEWER_DEBUG=1 ./terma.py /path/to/manga/volume01
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
