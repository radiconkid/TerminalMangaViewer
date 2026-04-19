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
import curses
import re
from pathlib import Path
from typing import List, Optional

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
        subprocess.run(["kitty", "+kitten", "icat", "--clear", "--silent"], check=False)

    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        img_height = max(1, term_height - 1)
        cover_width = term_width * 60 // 100
        cover_x_offset = term_width * 20 // 100
        subprocess.run([
            "kitty", "+kitten", "icat", "--silent",
            "--place", f"{cover_width}x{img_height}@{cover_x_offset}x0",
            str(image_path)
        ], check=False)

    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        img_height = max(1, term_height - 1)
        # 余白計算を改善
        img_width = term_width * 35 // 100
        margin = (term_width - (img_width * 2)) // 2

        # 右側の画像 (img_idx)
        right_x = margin + img_width
        subprocess.run([
            "kitty", "+kitten", "icat", "--silent",
            "--place", f"{img_width}x{img_height}@{right_x}x0",
            str(img_right)
        ], check=False)

        # 左側の画像 (img_idx + 1)
        if img_left:
            subprocess.run([
                "kitty", "+kitten", "icat", "--silent",
                "--place", f"{img_width}x{img_height}@{margin}x0",
                str(img_left)
            ], check=False)

class WezTermRenderer(ImageRenderer):
    def clear(self):
        # 画面全体を消すと点滅が激しいため、何もしないか
        # 必要な場合はカーソルを左上に移動させるだけにする
        print("\033[?25l", end="", flush=True)
        curses.curs_set(0)
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

        subprocess.run([
            "wezterm", "imgcat", "--height", str(target_h),
            "--position", f"{pos_x},0", str(image_path)
        ], check=False, env=env, stderr=subprocess.DEVNULL)

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
            subprocess.run(["wezterm", "imgcat", "--height", str(target_h), "--position", f"{pos_l},0", str(img_left)],
                           check=False, env=env, stderr=subprocess.DEVNULL)
            subprocess.run(["wezterm", "imgcat", "--height", str(target_h), "--position", f"{pos_r},0", str(img_right)],
                           check=False, env=env, stderr=subprocess.DEVNULL)
        else:
            # 右側1枚のみ（左側がない場合）
            pos_r = max(0, (term_width - display_w_r) // 2)
            env = os.environ.copy()
            env["COLUMNS"], env["LINES"] = str(term_width), str(term_height)
            subprocess.run(["wezterm", "imgcat", "--height", str(target_h), "--position", f"{pos_r},0", str(img_right)],
                           check=False, env=env, stderr=subprocess.DEVNULL)

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

def main(stdscr):
    # 環境変数の確認
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    # Kitty/WezTerm の判定をより厳密に（tmux越しでも判定できるように）
    is_kitty = "kitty" in term_program or "KITTY_WINDOW_ID" in os.environ
    is_wezterm = "wezterm" in term_program or "WEZTERM_PANE" in os.environ

    # レンダラーの自動選択
    if is_kitty:
        renderer = KittyRenderer()
    else:
        # デフォルトをWezTermとする
        renderer = WezTermRenderer()

    # Curses の基本設定
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.cbreak()
    curses.noecho()
    curses.mousemask(curses.ALL_MOUSE_EVENTS)

    # 引数チェック
    if len(sys.argv) != 2:
        return "Usage: terma.py <directory>"

    initial_dir = Path(sys.argv[1]).resolve()
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
                stdscr.clear()
                h, w = stdscr.getmaxyx()

                curr_right = images[img_idx]
                curr_left = images[img_idx + 1] if img_idx + 1 < num_images and img_idx > 0 else None

                if img_idx == 0:
                    status = f"DIR: {target_dir.name} | Cover: {curr_right.name}"
                else:
                    l_name = curr_left.name if curr_left else "END"
                    status = f"DIR: {target_dir.name} | R: {curr_right.name} L: {l_name}"

                # ステータス行を表示
                try:
                    stdscr.addstr(h - 1, 0, status[:w-1])
                except curses.error:
                    pass

                # 先に curses を refresh して画面を確定させる
                stdscr.refresh()

                # 描画前に画像をクリア（WezTermの点滅防止のため必要な時のみ）
                renderer.clear()

                # renderer を使って画像を出力
                if img_idx == 0:
                    renderer.display_cover(curr_right, w, h)
                else:
                    renderer.display_spread(curr_right, curr_left, w, h)
                needs_redraw = False

            # キー入力待ち
            try:
                key = stdscr.get_wch()
                debug(f"Input received: {repr(key)}")
            except curses.error:
                debug("Input timeout or error")
                continue

            if key == curses.KEY_RESIZE:
                needs_redraw = True
                continue

            if key in ('j', curses.KEY_LEFT, '\n', '\r'):
                next_idx = img_idx + (1 if img_idx == 0 else 2)
                if next_idx >= num_images:
                    if dir_idx < len(dirs_to_browse) - 1:
                        dir_idx += 1
                        img_idx = 0
                        break
                else:
                    img_idx = next_idx
                needs_redraw = True

            elif key in ('k', 'l', curses.KEY_RIGHT):
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

            elif key == '\x1b':
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

            # マウスイベント (Kitty形式の簡易実装)
            elif key == curses.KEY_MOUSE:
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
    def signal_handler(sig, frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # マウス入力を有効化し、テキストカーソルを非表示にする
        sys.stdout.write('\x1b[?1000h\x1b[?1006h\x1b[?25l')
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

        error_msg = curses.wrapper(main)
        if error_msg:
            print(error_msg)
    finally:
        # マウス入力を無効化し、テキストカーソルを再表示する
        sys.stdout.write('\x1b[?1000l\x1b[?1006l\x1b[?25h')
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

if __name__ == "__main__":
    main_cli()
