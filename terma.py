#!/usr/bin/env python3
"""
terma.py: Kitty または WezTerm で動作するマンガビューア
使用法: ./terma.py <ディレクトリパス>
操作: 1枚目は表紙、2枚目以降は見開き。j/Leftで進む、k/Rightで戻る、qで終了
"""

import os
import sys
import subprocess
import signal
import re
import shutil
from pathlib import Path
from typing import List, Optional

if os.name != 'nt':
    import curses
else:
    import msvcrt

# アスペクト比取得のためのオプション。インストールされていない場合はデフォルト値を使用
try:
    from PIL import Image
except ImportError:
    Image = None

# --- デバッグ設定 ---
DEBUG = os.environ.get("TERMA_DEBUG") == "1"
LOG_FILE_PATH = Path.home() / "terma-debug.log"

if DEBUG:
    with open(LOG_FILE_PATH, "w") as f:
        f.write("--- Terma Debug Log ---\n")

def debug(*args):
    """デバッグメッセージをログファイルに書き込む"""
    if not DEBUG:
        return
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")
    with open(LOG_FILE_PATH, "a") as f:
        f.write(f"[{now}] {' '.join(map(str, args))}\n")

class ImageRenderer:
    def clear(self):
        pass

    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        pass

    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        pass

class KittyRenderer(ImageRenderer):
    def clear(self):
        # --silent を追加して不要な出力を抑制
        cmd = ["kitty", "+kitten", "icat", "--clear", "--silent"]
        debug("Command:", " ".join(cmd))
        subprocess.run(cmd, check=False, stdout=sys.__stdout__)

    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        img_height = max(1, term_height - 1)
        cover_width = term_width * 60 // 100
        cover_x_offset = term_width * 20 // 100
        cmd = [
            "kitty", "+kitten", "icat", "--silent",
            "--place", f"{cover_width}x{img_height}@{cover_x_offset}x0",
            str(image_path)
        ]
        debug("Command:", " ".join(cmd))
        subprocess.run(cmd, check=False, stdout=sys.__stdout__)

    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        img_height = max(1, term_height - 1)
        # 余白計算を改善
        img_width = term_width * 35 // 100
        margin = (term_width - (img_width * 2)) // 2

        # 右側の画像 (img_idx)
        right_x = margin + img_width
        cmd_r = [
            "kitty", "+kitten", "icat", "--silent",
            "--place", f"{img_width}x{img_height}@{right_x}x0",
            str(img_right)
        ]
        debug("Command (R):", " ".join(cmd_r))
        subprocess.run(cmd_r, check=False, stdout=sys.__stdout__)

        # 左側の画像 (img_idx + 1)
        if img_left:
            cmd_l = [
                "kitty", "+kitten", "icat", "--silent",
                "--place", f"{img_width}x{img_height}@{margin}x0",
                str(img_left)
            ]
            debug("Command (L):", " ".join(cmd_l))
            subprocess.run(cmd_l, check=False, stdout=sys.__stdout__)

class WezTermRenderer(ImageRenderer):
    def __init__(self):
        # Windows の場合は wezterm.exe を使用
        self.wezterm_bin = "wezterm.exe" if os.name == "nt" else "wezterm"

    def clear(self):
        # 画面全体を消すと点滅が激しいため、何もしないか
        # 必要な場合はカーソルを左上に移動させるだけにする
        pass
        # もし wezterm imgcat --clear が使えるならそれを使う

    def _get_aspect(self, path: Path):
        try:
            if Image:
                with Image.open(path) as img:
                    return img.width / img.height
        except:
            pass
        return 0.7  # デフォルトのアスペクト比（縦長）

    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        target_h = max(1, term_height - 1)
        aspect = self._get_aspect(image_path)
        # セル比率2.2を考慮した幅計算
        display_w = int(target_h * aspect * 2.2)
        pos_x = max(0, ((term_width - display_w) // 2 - 5))

        env = os.environ.copy()
        env["COLUMNS"], env["LINES"] = str(term_width), str(term_height)

        cmd = [
            self.wezterm_bin, "imgcat", "--height", str(target_h),
            "--position", f"{pos_x},0", str(image_path)
        ]
        debug("Command:", " ".join(cmd))
        subprocess.run(cmd, check=False, env=env, stdout=sys.__stdout__, stderr=subprocess.DEVNULL)

    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        target_h = max(1, term_height - 2)
        aspect_r = self._get_aspect(img_right)
        display_w_r = int(target_h * aspect_r * 2.2)

        if img_left:
            aspect_l = self._get_aspect(img_left)
            display_w_l = int(target_h * aspect_l * 2.2)
            total_w = display_w_r + display_w_l

            # 幅が超える場合は縮小
            if total_w > term_width:
                scale = term_width / total_w
                display_w_l = int(display_w_l * scale)
                display_w_r = int(display_w_r * scale)
                target_h = int(target_h * scale)
                total_w = display_w_r + display_w_l

            pos_l = max(0, (term_width - total_w) // 2 - 5)
            pos_r = pos_l + display_w_l

            env = os.environ.copy()
            env["COLUMNS"], env["LINES"] = str(term_width), str(term_height)

            # WezTermは順番に描画
            cmd_l = [self.wezterm_bin, "imgcat", "--height", str(target_h), "--position", f"{pos_l},0", str(img_left)]
            cmd_r = [self.wezterm_bin, "imgcat", "--height", str(target_h), "--position", f"{pos_r},0", str(img_right)]
            debug("Command (L):", " ".join(cmd_l))
            subprocess.run(cmd_l, check=False, env=env, stdout=sys.__stdout__, stderr=subprocess.DEVNULL)
            debug("Command (R):", " ".join(cmd_r))
            subprocess.run(cmd_r, check=False, env=env, stdout=sys.__stdout__, stderr=subprocess.DEVNULL)
        else:
            # 右側1枚のみ（左側がない場合）
            pos_r = max(0, (term_width - display_w_r) // 2)
            env = os.environ.copy()
            env["COLUMNS"], env["LINES"] = str(term_width), str(term_height)
            cmd_r = [self.wezterm_bin, "imgcat", "--height", str(target_h), "--position", f"{pos_r},0", str(img_right)]
            debug("Command:", " ".join(cmd_r))
            subprocess.run(cmd_r, check=False, env=env, stdout=sys.__stdout__, stderr=subprocess.DEVNULL)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def get_sorted_dirs(initial_dir: Path) -> List[Path]:
    parent_dir = initial_dir.parent
    dirs = [d for d in parent_dir.iterdir() if d.is_dir()]
    return sorted(dirs, key=natural_sort_key)

def get_sorted_images(target_dir: Path) -> List[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
    images = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in extensions]
    return sorted(images, key=natural_sort_key)

def run_app(stdscr=None):
    """メインアプリケーションループ。stdscr があれば curses、なければ ANSI+msvcrt (Windows) を使用"""
    is_win = os.name == 'nt'

    def get_term_size():
        if stdscr:
            return stdscr.getmaxyx()
        else:
            size = shutil.get_terminal_size()
            return size.lines, size.columns

    def clear_screen():
        if stdscr:
            stdscr.clear()
        else:
            os.system('cls' if is_win else 'clear')

    def refresh_screen():
        if stdscr:
            stdscr.refresh()
        else:
            sys.stdout.flush()

    def draw_status(lines, cols, text):
        if stdscr:
            try:
                stdscr.addstr(lines - 1, 0, text[:cols-1])
            except curses.error:
                pass
        else:
            # Windows/ANSI: 反転色でステータス表示
            sys.stdout.write(f"\033[{lines};1H\033[7m{text[:cols-1]:<{cols-1}}\033[0m")

    def get_input():
        if stdscr:
            try:
                return stdscr.get_wch()
            except curses.error:
                return None
        else:
            # Windows/msvcrt の入力処理
            ch = msvcrt.getch()
            if ch == b'\x03': raise KeyboardInterrupt() # Ctrl+C
            if ch in (b'\x00', b'\xe0'): # 特殊キー (矢印など)
                ext = msvcrt.getch()
                if ext == b'K': return 'KEY_LEFT'
                if ext == b'M': return 'KEY_RIGHT'
                if ext == b'H': return 'KEY_UP'
                if ext == b'P': return 'KEY_DOWN'
                return None
            if ch == b'\r' or ch == b'\n': return '\n'
            if ch == b'\x1b': return 'ESC'
            try:
                return ch.decode('utf-8')
            except:
                return None

    # ターミナル種別の判定
    # 環境変数の確認
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    is_kitty = "kitty" in term_program or "KITTY_WINDOW_ID" in os.environ

    # Curses 特有の初期設定
    if stdscr:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    else:
        # Windows ANSI 初期化
        os.system('') # Enable ANSI
        sys.stdout.write('\033[?25l') # Hide cursor

    # レンダラーの自動選択
    if is_kitty:
        renderer = KittyRenderer()
    else:
        # デフォルトをWezTermとする
        renderer = WezTermRenderer()

    # 引数チェック
    if len(sys.argv) > 1:
        initial_dir = Path(sys.argv[1]).resolve()
    else:
        initial_dir = Path.cwd().resolve()
    dirs_to_browse = get_sorted_dirs(initial_dir)
    try:
        dir_idx = dirs_to_browse.index(initial_dir)
    except ValueError:
        dir_idx = 0

    img_idx = 0
    needs_redraw = True

    while 0 <= dir_idx < len(dirs_to_browse):
        # フォルダ移動時は必ず再描画
        needs_redraw = True
        target_dir = dirs_to_browse[dir_idx]
        images = get_sorted_images(target_dir)
        num_images = len(images)

        if not images:
            dir_idx += 1
            continue

        if img_idx == -1: # 前のフォルダから戻ってきた場合
            img_idx = num_images - 2 + (num_images % 2) if num_images > 1 else 0

        while 0 <= img_idx < num_images:
            if needs_redraw:
                clear_screen()
                h, w = get_term_size()

                curr_right = images[img_idx]
                curr_left = images[img_idx + 1] if img_idx + 1 < num_images and img_idx > 0 else None

                if img_idx == 0:
                    status = f"DIR: {target_dir.name} | Cover: {curr_right.name}"
                else:
                    l_name = curr_left.name if curr_left else "END"
                    status = f"DIR: {target_dir.name} | R: {curr_right.name} L: {l_name}"

                # ステータス行を表示
                draw_status(h, w, status)
                refresh_screen()

                # 描画前に画像をクリア（WezTermの点滅防止のため必要な時のみ）
                renderer.clear()

                # renderer を使って画像を出力
                if img_idx == 0:
                    renderer.display_cover(curr_right, w, h)
                else:
                    renderer.display_spread(curr_right, curr_left, w, h)
                needs_redraw = False

            # キー入力待ち
            key = get_input()
            if key is None:
                continue
            debug(f"Input received: {repr(key)}")

            # 共通キーロジック
            if stdscr and key == curses.KEY_RESIZE:
                needs_redraw = True
                continue

            if key in ('j', curses.KEY_LEFT if stdscr else 'KEY_LEFT', '\n', '\r'):
                next_idx = img_idx + (1 if img_idx == 0 else 2)
                if next_idx >= num_images:
                    if dir_idx < len(dirs_to_browse) - 1:
                        dir_idx += 1
                        img_idx = 0
                        break
                else:
                    img_idx = next_idx
                needs_redraw = True

            elif key in ('k', 'l', curses.KEY_RIGHT if stdscr else 'KEY_RIGHT'):
                if img_idx == 0:
                    if dir_idx > 0:
                        dir_idx -= 1
                        img_idx = -1
                        break
                else:
                    img_idx = max(0, img_idx - 2)
                needs_redraw = True

            elif key == '0':
                img_idx = 0
                needs_redraw = True
            elif key == '9':
                img_idx = num_images - 2 + (num_images % 2) if num_images > 1 else 0
                needs_redraw = True

            elif key == ',':
                if dir_idx < len(dirs_to_browse) - 1:
                    dir_idx += 1
                    img_idx = 0
                    break
                needs_redraw = True
            elif key == '.':
                if dir_idx > 0:
                    dir_idx -= 1
                    img_idx = 0
                    break
                needs_redraw = True
            elif key in ('q', 'Q', 'h'):
                return

            elif key == '\x1b' and stdscr: # ESC シーケンス (curses のみ)
                stdscr.timeout(40) # 応答を待つ
                try:
                    ch = stdscr.get_wch()
                    if ch == '[':
                        ch2 = stdscr.get_wch()
                        if ch2 == '<':  # SGR形式
                            seq = "<"
                            while True:
                                c = stdscr.get_wch()
                                seq += str(c)
                                if c in "Mm": break
                            debug(f"SGR Mouse: \\x1b[{seq}")
                            m = re.match(r'<(\d+);(\d+);(\d+)([Mm])', seq)
                            if m:
                                btn, mx, state = int(m.group(1)), int(m.group(2)), m.group(4)
                                if state == "M":
                                    if btn in (0, 32):  # 左クリック
                                        next_idx = img_idx + (1 if img_idx == 0 else 2)
                                        if next_idx >= num_images:
                                            if dir_idx < len(dirs_to_browse) - 1:
                                                dir_idx += 1
                                                img_idx = 0
                                        else:
                                            img_idx = next_idx
                                    elif btn in (2, 34):  # 右クリック
                                        if img_idx == 0:
                                            if dir_idx > 0:
                                                dir_idx -= 1
                                                img_idx = -1
                                        else:
                                            img_idx = max(0, img_idx - 2)
                                    elif btn in (1, 33):  # 中クリック -> 終了
                                        return
                                    if img_idx >= num_images or img_idx == -1: break
                                    needs_redraw = True
                        elif ch2 == 'M':  # X10形式
                            def decode_mouse_byte(value):
                                if isinstance(value, int):
                                    return value
                                if isinstance(value, str) and len(value) == 1:
                                    return ord(value)
                                if isinstance(value, bytes) and len(value) == 1:
                                    return value[0]
                                raise ValueError(f"Unsupported mouse byte: {value!r}")

                            b = stdscr.get_wch()
                            x = stdscr.get_wch()
                            y = stdscr.get_wch()
                            btn = decode_mouse_byte(b) - 32
                            mx = decode_mouse_byte(x) - 32
                            if btn == 0: # 左クリック押し下げ
                                next_idx = img_idx + (1 if img_idx == 0 else 2)
                                if next_idx >= num_images:
                                    if dir_idx < len(dirs_to_browse) - 1:
                                        dir_idx += 1
                                        img_idx = 0
                                else:
                                    img_idx = next_idx
                                if img_idx >= num_images or img_idx == -1: break
                                needs_redraw = True
                            elif btn == 2: # 右クリック押し下げ
                                if img_idx == 0:
                                    if dir_idx > 0:
                                        dir_idx -= 1
                                        img_idx = -1
                                else:
                                    img_idx = max(0, img_idx - 2)
                                if img_idx >= num_images or img_idx == -1: break
                                needs_redraw = True
                            elif btn == 1: # 中クリック押し下げ -> 終了
                                return
                        else:
                            # その他の CSI シーケンス (サイズ報告等) を最後まで読み捨てる
                            # 文字 (a-z, A-Z) または特定の終端文字が来るまで読む
                            while not ('a' <= str(ch2) <= 'z' or 'A' <= str(ch2) <= 'Z' or ch2 in '@^~'):
                                ch2 = stdscr.get_wch()

                    # バッファに溜まっている残骸を掃除（ドレイン）
                    stdscr.timeout(0)
                    while True:
                        stdscr.get_wch()
                except curses.error:
                    pass
                finally:
                    stdscr.timeout(-1)
                continue # ESC シーケンスを処理した後は再描画チェックへ
            
            # マウスイベント (curses のみ)
            elif stdscr and key == curses.KEY_MOUSE:
                try:
                    m_id, mx, my, m_z, bstate = curses.getmouse()
                    debug(f"Standard Curses Mouse: x={mx}, y={my}, bstate={hex(bstate)}")
                    # BUTTON1_RELEASED (ボタンを離した時) もクリックとして判定に含める
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_RELEASED):
                        next_idx = img_idx + (1 if img_idx == 0 else 2)
                        if next_idx >= num_images:
                            if dir_idx < len(dirs_to_browse) - 1:
                                dir_idx += 1
                                img_idx = 0
                        else:
                            img_idx = next_idx
                        if img_idx >= num_images or img_idx == -1: break
                        needs_redraw = True
                    elif bstate & (curses.BUTTON3_CLICKED | curses.BUTTON3_PRESSED | curses.BUTTON3_RELEASED):
                        if img_idx == 0:
                            if dir_idx > 0:
                                dir_idx -= 1
                                img_idx = -1
                        else:
                            img_idx = max(0, img_idx - 2)
                        if img_idx >= num_images or img_idx == -1: break
                        needs_redraw = True
                    elif bstate & (curses.BUTTON2_CLICKED | curses.BUTTON2_PRESSED | curses.BUTTON2_RELEASED):
                        return
                except Exception as e:
                    debug(f"getmouse error: {e}")
        else:
            dir_idx += 1
            img_idx = 0

    renderer.clear()
    print("全てのファイルの表示を終了しました。")

def main_cli():
    """Command line entry point for package installation"""
    # ヘルプオプションの場合は curses を使用せずに直接表示
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""TerMa - Terminal Manga Viewer

Usage: terma [directory]

Arguments:
  directory    Manga directory to view (default: current directory)
  --help       Show this help message

Controls:
  j/Left/Enter  Next page
  k/l/Right     Previous page
  0            First page (cover)
  9            Last spread
  ,            Next volume
  .            Previous volume
  q/Q/h        Quit""")
        return

    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 初期設定 (マウス有効化、カーソル非表示)
        if os.name != 'nt': sys.stdout.write('\x1b[?1000h\x1b[?1006h')
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

        if os.name == 'nt':
            error_msg = run_app()
        else:
            error_msg = curses.wrapper(run_app)

        if error_msg:
            print(error_msg)
    finally:
        # 終了設定 (マウス無効化、カーソル表示)
        if os.name != 'nt': sys.stdout.write('\x1b[?1000l\x1b[?1006l')
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

if __name__ == "__main__":
    main_cli()
