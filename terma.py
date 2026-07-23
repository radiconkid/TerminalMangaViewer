#!/usr/bin/env python3
import os
import sys
import subprocess
import signal
import re
import shutil
import zipfile
import tarfile
import tempfile
import json
from pathlib import Path
from typing import List, Optional, Any, Dict
__version__ = "1.0.0"
TURBO_STEP = 10
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
RESUME_FILE_PATH = Path.home() / ".terma_resume.json"
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

def get_image_aspect(path: Path) -> float:
    try:
        if Image:
            with Image.open(path) as img:
                w, h = img.width, img.height
                try:
                    exif = img._getexif()
                    if exif:
                        orientation = exif.get(0x0112)
                        if orientation in (5, 6, 7, 8):
                            w, h = h, w
                except Exception:
                    pass
                return w / h
    except Exception:
        pass
    return 0.7


def _get_cell_pixel_size_win32():
    """Windows: Win32 API を使って端末の1文字セルあたりの物理ピクセルサイズを取得する。
    取得できない場合は None を返す。"""
    try:
        import ctypes
        import ctypes.wintypes
        from ctypes import byref, c_short, c_ushort, c_ulong, c_uint, c_int, Structure, POINTER, sizeof

        class COORD(Structure):
            _fields_ = [("X", c_short), ("Y", c_short)]

        class SMALL_RECT(Structure):
            _fields_ = [("Left", c_short), ("Top", c_short), ("Right", c_short), ("Bottom", c_short)]

        class CONSOLE_SCREEN_BUFFER_INFOEX(Structure):
            _fields_ = [
                ("cbSize", c_ulong),
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", c_ushort),
                ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD),
                ("wPopupAttributes", c_ushort),
                ("bFullscreenSupported", ctypes.c_bool),
                ("ColorTable", c_ulong * 16),
            ]

        class CONSOLE_FONT_INFOEX(Structure):
            _fields_ = [
                ("cbSize", c_ulong),
                ("nFont", c_ulong),
                ("dwFontSize", COORD),
                ("FontFamily", c_uint),
                ("FontWeight", c_uint),
                ("FaceName", ctypes.wintypes.WCHAR * 32),
            ]

        class RECT(Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        GetStdHandle = kernel32.GetStdHandle
        GetStdHandle.argtypes = [c_ulong]
        GetStdHandle.restype = ctypes.c_void_p

        GetConsoleWindow = kernel32.GetConsoleWindow
        GetConsoleWindow.argtypes = []
        GetConsoleWindow.restype = ctypes.c_void_p

        GetConsoleScreenBufferInfoEx = kernel32.GetConsoleScreenBufferInfoEx
        GetConsoleScreenBufferInfoEx.argtypes = [ctypes.c_void_p, POINTER(CONSOLE_SCREEN_BUFFER_INFOEX)]
        GetConsoleScreenBufferInfoEx.restype = ctypes.c_bool

        GetCurrentConsoleFontEx = kernel32.GetCurrentConsoleFontEx
        GetCurrentConsoleFontEx.argtypes = [ctypes.c_void_p, ctypes.c_bool, POINTER(CONSOLE_FONT_INFOEX)]
        GetCurrentConsoleFontEx.restype = ctypes.c_bool

        GetConsoleFontSize = kernel32.GetConsoleFontSize
        GetConsoleFontSize.argtypes = [ctypes.c_void_p, c_ulong]
        GetConsoleFontSize.restype = COORD

        GetClientRect = user32.GetClientRect
        GetClientRect.argtypes = [ctypes.c_void_p, POINTER(RECT)]
        GetClientRect.restype = ctypes.c_bool

        STD_OUTPUT_HANDLE = -11
        h = GetStdHandle(STD_OUTPUT_HANDLE)
        if h is None or h == ctypes.c_void_p(-1).value:
            return None

        # 1. バッファ情報から文字セル数とウィンドウサイズを取得
        buf_info = CONSOLE_SCREEN_BUFFER_INFOEX()
        buf_info.cbSize = sizeof(CONSOLE_SCREEN_BUFFER_INFOEX)
        if not GetConsoleScreenBufferInfoEx(h, byref(buf_info)):
            return None
        cols = buf_info.srWindow.Right - buf_info.srWindow.Left + 1
        rows = buf_info.srWindow.Bottom - buf_info.srWindow.Top + 1

        # 2. フォント情報から1文字セルのピクセルサイズを取得
        font_info = CONSOLE_FONT_INFOEX()
        font_info.cbSize = sizeof(CONSOLE_FONT_INFOEX)
        if not GetCurrentConsoleFontEx(h, False, byref(font_info)):
            return None

        cell_w = font_info.dwFontSize.X
        cell_h = font_info.dwFontSize.Y

        # 3. GetConsoleFontSize で確認 (フォールバック)
        cell_w2 = GetConsoleFontSize(h, font_info.nFont)
        cell_h2 = GetConsoleFontSize(h, font_info.nFont)
        if cell_w2.X > 0 and cell_h2.Y > 0:
            cell_w, cell_h = cell_w2.X, cell_h2.Y

        # 4. コンソールウィンドウのクライアント領域から実ピクセルサイズを逆算 (最も信頼性が高い)
        hwnd = GetConsoleWindow()
        if hwnd:
            rect = RECT()
            if GetClientRect(hwnd, ctypes.byref(rect)):
                client_w = rect.right - rect.left
                client_h = rect.bottom - rect.top
                if client_w > 0 and client_h > 0 and cols > 0 and rows > 0:
                    cell_w_from_client = client_w // cols
                    cell_h_from_client = client_h // rows
                    if cell_w_from_client > 0 and cell_h_from_client > 0:
                        cell_w = cell_w_from_client
                        cell_h = cell_h_from_client

        if cell_w == 0 and cell_h > 0:
            cell_w = cell_h // 2

        if cell_w == 0 or cell_h == 0:
            return None

        return float(cell_w), float(cell_h)

    except Exception:
        return None


def get_cell_pixel_size():
    """端末の1文字セルあたりの物理ピクセルサイズ (幅, 高さ) を取得する。
    取得できない場合は None を返す。"""
    # Windows: Win32 API 経由で実測
    if os.name == 'nt':
        result = _get_cell_pixel_size_win32()
        if result is not None:
            return result

    # Unix/Linux: TIOCGWINSZ 経由で取得
    try:
        import fcntl
        import termios
        import struct
        buf = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b'\0' * 8)
        rows, cols, xpixel, ypixel = struct.unpack('HHHH', buf)
        if cols == 0 or rows == 0 or xpixel == 0 or ypixel == 0:
            return None
        cell_w = xpixel / cols
        cell_h = ypixel / rows
        return cell_w, cell_h
    except Exception:
        return None


def _is_landscape(image_path: Path) -> bool:
    """Check if an image is landscape (width > height).
    Returns True for landscape images that should be displayed as single page."""
    try:
        aspect = get_image_aspect(image_path)
        return aspect > 1.0
    except Exception:
        return False


def get_cell_aspect_ratio() -> float:
    """端末の1文字セルのアスペクト比 (高さ/幅) を取得する。
    取得できない場合はデフォルト値 2.45 を返す。"""
    cell_size = get_cell_pixel_size()
    if cell_size:
        cell_w, cell_h = cell_size
        return cell_h / cell_w
    return 2.45


class ImageRenderer:
    def clear(self):
        pass
    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        pass
    def display_single(self, image_path: Path, term_width: int, term_height: int):
        pass
    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        pass
class SixelRenderer(ImageRenderer):
    """Sixel/Kitty対応ターミナル用レンダラー。

    chafa を使用して画像を変換し出力する。
    端末に応じて sixel または Kitty ネイティブ形式を自動選択する。
    """
    def __init__(self):
        self._use_chafa = shutil.which("chafa") is not None
        # Kitty端末かどうかを検出
        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        self._is_kitty = "kitty" in term_program or "KITTY_WINDOW_ID" in os.environ
        debug(f"SixelRenderer: chafa={self._use_chafa}, kitty={self._is_kitty}")

    def clear(self):
        # Sixelクリアシーケンス: 画面をクリアしてカーソルを左上に
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.flush()

    def _sixel_convert(self, image_path: Path, cols: int, rows: int) -> Optional[bytes]:
        """画像をSixel/Kittyデータに変換して返す。失敗した場合はNone。"""
        if self._use_chafa:
            try:
                # Kittyの場合はネイティブ形式（高品質）、それ以外はsixel形式
                fmt = "kitty" if self._is_kitty else "sixels"
                cmd = [
                    "chafa", "-f", fmt,
                    "--size", f"{cols}x{rows}",
                    "--optimize", "9",
                    image_path.absolute().as_posix()
                ]
                debug("Sixel chafa cmd:", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and result.stdout:
                    return result.stdout
                debug(f"Sixel chafa failed: rc={result.returncode}, stderr={result.stderr[:200]}")
            except Exception as e:
                debug(f"Sixel chafa error: {e}")

        return None

    def _output_sixel(self, sixel_data: bytes):
        """Sixelデータを端末に出力し、カーソルを非表示にする。"""
        if self._is_kitty:
            # Kittyプロトコル: 最初のシーケンスに z=-1 を追加して画像をテキスト背面に配置
            sixel_data = self._inject_kitty_z_index(sixel_data, -1)
        sys.stdout.buffer.write(sixel_data)
        # カーソルを非表示にしてから、ステータス行の後ろ（右下）に移動
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

    def _inject_kitty_z_index(self, data: bytes, z: int) -> bytes:
        """Kittyグラフィックスプロトコルのシーケンスに z-index パラメータを追加する。

        Kittyプロトコル形式: \\x1b_G<params>;<data>\\x1b\\
        <params> は key=value のカンマ区切りリスト。
        最初のシーケンスのパラメータに z=<z> を追加する。
        """
        # 最初の \x1b_G シーケンスを探す
        idx = data.find(b'\x1b_G')
        if idx < 0:
            return data
        # パラメータ部分の終端（; または \x1b\\）を探す
        # 形式: \x1b_G<params>;<data>\x1b\\ または \x1b_G<params>\x1b\\
        rest = data[idx + 2:]  # \x1b_G の後
        # パラメータは ; または \x1b\\ で終わる
        param_end = -1
        for sep in (b';', b'\x1b\\'):
            pos = rest.find(sep)
            if pos >= 0:
                if param_end < 0 or pos < param_end:
                    param_end = pos
        if param_end < 0:
            return data
        params_str = rest[:param_end].decode('ascii', errors='replace')
        # 既に z パラメータがある場合は置き換え、なければ追加
        if 'z=' in params_str:
            import re
            params_str = re.sub(r'z=[^,]*', f'z={z}', params_str)
        else:
            params_str = f'{params_str},z={z}'
        # 置き換え
        new_data = data[:idx + 2] + params_str.encode('ascii') + rest[param_end:]
        return new_data

    def _center_cursor(self, display_cols: int, term_width: int):
        """画像を中央表示するためにカーソルを絶対位置に移動する。"""
        if display_cols < term_width:
            offset = max(0, (term_width - display_cols) // 2)
            if offset > 0:
                # 絶対位置指定でカーソルを1行目、offset列目に移動
                sys.stdout.write(f'\x1b[1;{offset + 1}H')
                sys.stdout.flush()

    def display_cover(self, image_path: Path, term_width: int, term_height: int):
        self.display_single(image_path, term_width, term_height)

    def display_single(self, image_path: Path, term_width: int, term_height: int):
        # カーソルを確実に画面左上に移動
        sys.stdout.write('\x1b[H')
        sys.stdout.flush()

        max_h = max(1, term_height - 2)
        aspect = get_image_aspect(image_path)
        cell_ratio = get_cell_aspect_ratio()
        # 文字セルのアスペクト比を考慮
        display_cols = max(1, int(max_h * aspect * cell_ratio))
        img_height = max_h
        if display_cols > term_width - 2:
            scale = (term_width - 2) / display_cols
            display_cols = term_width - 2
            img_height = max(1, int(img_height * scale))

        sixel_data = self._sixel_convert(image_path, display_cols, img_height)
        if sixel_data:
            self._center_cursor(display_cols, term_width)
            self._output_sixel(sixel_data)
        else:
            debug("Sixel conversion failed, falling back to no-op")

    def display_spread(self, img_right: Path, img_left: Optional[Path], term_width: int, term_height: int):
        # カーソルを確実に画面左上に移動
        sys.stdout.write('\x1b[H')
        sys.stdout.flush()

        max_h = max(1, term_height - 2)
        aspect_r = get_image_aspect(img_right)
        cell_ratio = get_cell_aspect_ratio()
        display_cols_r = max(1, int(max_h * aspect_r * cell_ratio))
        img_height = max_h

        if img_left and Image:
            # PILを使って左右の画像を結合してからSixel変換
            try:
                with Image.open(img_left) as im_l, Image.open(img_right) as im_r:
                    # 高さを揃える
                    target_h = max(im_l.height, im_r.height)
                    w_l = int(im_l.width * (target_h / im_l.height))
                    w_r = int(im_r.width * (target_h / im_r.height))
                    im_l_resized = im_l.resize((w_l, target_h), Image.LANCZOS)
                    im_r_resized = im_r.resize((w_r, target_h), Image.LANCZOS)
                    # 結合
                    combined_w = w_l + w_r
                    combined = Image.new("RGB", (combined_w, target_h))
                    combined.paste(im_l_resized, (0, 0))
                    combined.paste(im_r_resized, (w_l, 0))
                    # 一時ファイルに保存してSixel変換
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp_path = tmp.name
                        combined.save(tmp_path, format="PNG")
                    try:
                        aspect = combined_w / target_h
                        display_cols = max(1, int(max_h * aspect * cell_ratio))
                        img_height = max_h
                        if display_cols > term_width - 2:
                            scale = (term_width - 2) / display_cols
                            display_cols = term_width - 2
                            img_height = max(1, int(img_height * scale))
                        sixel_data = self._sixel_convert(Path(tmp_path), display_cols, img_height)
                        if sixel_data:
                            self._center_cursor(display_cols, term_width)
                            self._output_sixel(sixel_data)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                    return
            except Exception as e:
                debug(f"Sixel spread PIL combine error: {e}")

        # PILが使えない場合や結合に失敗した場合は右側のみ表示
        self.display_single(img_right, term_width, term_height)


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]
def get_sorted_dirs(initial_dir: Path) -> List[Path]:
    parent_dir = initial_dir.parent
    dirs = [d for d in parent_dir.iterdir() if d.is_dir()]
    return sorted(dirs, key=natural_sort_key)
def get_sorted_images(target_dir: Path) -> List[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
    # Priority order for duplicate stems (higher priority first)
    priority = {".jpg": 0, ".jpeg": 0, ".png": 1, ".gif": 2, ".webp": 3, ".bmp": 4, ".avif": 5}
    images = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in extensions]
    # Deduplicate by stem: keep the highest priority file for each stem
    best: Dict[str, Path] = {}
    for img in images:
        stem = img.stem.lower()
        ext = img.suffix.lower()
        if stem not in best or priority.get(ext, 99) < priority.get(best[stem].suffix.lower(), 99):
            best[stem] = img
    return sorted(best.values(), key=natural_sort_key)


def load_resume_data() -> Dict[str, Any]:
    try:
        if RESUME_FILE_PATH.exists():
            with open(RESUME_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        debug(f"Failed to load resume data: {e}")
    return {}


def save_resume_data(data: Dict[str, Any]) -> None:
    try:
        with open(RESUME_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception as e:
        debug(f"Failed to save resume data: {e}")


def get_resume_state(resume_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not resume_key:
        return None
    data = load_resume_data()
    state = data.get(resume_key)
    return state if isinstance(state, dict) else None


def save_resume_state(
    resume_key: Optional[str],
    target_dir: Path,
    images: List[Path],
    img_idx: int,
    is_archive: bool,
    archive_resume_base: Optional[Path] = None,
    cover_mode: bool = True,
    reading_mode: bool = True,
) -> None:
    if not resume_key or not images:
        return
    safe_idx = max(0, min(len(images) - 1, img_idx))
    state: Dict[str, Any] = {
        "image_name": images[safe_idx].name,
        "image_index": safe_idx,
        "is_archive": is_archive,
        "cover_mode": cover_mode,
        "reading_mode": reading_mode,
    }
    if is_archive and archive_resume_base:
        try:
            state["dir_rel"] = target_dir.resolve().relative_to(archive_resume_base.resolve()).as_posix()
        except Exception:
            state["dir_rel"] = "."
    else:
        state["dir_path"] = target_dir.resolve().as_posix()

    data = load_resume_data()
    data[resume_key] = state
    save_resume_data(data)


def find_resume_dir_index(
    dirs_to_browse: List[Path],
    state: Optional[Dict[str, Any]],
    is_archive: bool,
    archive_resume_base: Optional[Path] = None,
) -> Optional[int]:
    if not state:
        return None
    if is_archive:
        saved_rel = state.get("dir_rel")
        if not isinstance(saved_rel, str) or archive_resume_base is None:
            return None
        for i, d in enumerate(dirs_to_browse):
            try:
                if d.resolve().relative_to(archive_resume_base.resolve()).as_posix() == saved_rel:
                    return i
            except Exception:
                continue
    else:
        saved_dir = state.get("dir_path")
        if not isinstance(saved_dir, str):
            return None
        saved_path = Path(saved_dir)
        for i, d in enumerate(dirs_to_browse):
            try:
                if d.resolve() == saved_path.resolve():
                    return i
            except Exception:
                continue
    return None


def find_resume_image_index(images: List[Path], state: Optional[Dict[str, Any]]) -> int:
    if not state or not images:
        return 0
    image_name = state.get("image_name")
    if isinstance(image_name, str):
        for i, image in enumerate(images):
            if image.name == image_name:
                return i
    image_index = state.get("image_index")
    if isinstance(image_index, int):
        return max(0, min(len(images) - 1, image_index))
    return 0


def extract_archive(archive_path: Path, extract_to: Path) -> bool:
    # ZIP / CBZ
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            return True
    except Exception:
        pass

    # RAR / CBR
    try:
        is_rar = archive_path.suffix.lower() in ('.rar', '.cbr')
        if not is_rar:
            try:
                with open(archive_path, 'rb') as f:
                    is_rar = f.read(7).startswith(b'Rar!\x1a\x07')
            except Exception:
                pass
        if is_rar:
            # unrar を試す
            unrar_path = shutil.which("unrar")
            if unrar_path:
                res = subprocess.run([unrar_path, "x", "-y", archive_path.absolute().as_posix(), extract_to.absolute().as_posix() + "/"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if res.returncode == 0:
                    return True
            # 7z を試す
            sevenz_path = shutil.which("7z") or shutil.which("7za")
            if sevenz_path:
                res = subprocess.run([sevenz_path, "x", "-y", f"-o{extract_to.absolute().as_posix()}", archive_path.absolute().as_posix()],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if res.returncode == 0:
                    return True
    except Exception:
        pass

    # TAR
    try:
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_to)
            return True
    except Exception:
        pass

    return False


def extract_nested_archives(root_dir: Path):
    """アーカイブファイル（zip/cbz/rar/cbr）を再帰的に展開する。

    展開後、元のアーカイブファイルは削除される。
    対応形式: zip, cbz, rar, cbr
    """
    archive_exts = {'.zip', '.cbz', '.rar', '.cbr'}
    found = True
    while found:
        found = False
        for arch in sorted(root_dir.rglob('*'), key=lambda p: str(p)):
            if arch.is_file() and arch.suffix.lower() in archive_exts:
                nested_dir = root_dir / arch.stem
                nested_dir.mkdir(exist_ok=True)
                if extract_archive(arch, nested_dir):
                    arch.unlink()
                    found = True


def should_display_single(images: List[Path], current_idx: int, cover_mode: bool = True, force_single: bool = False) -> bool:
    if force_single:
        return True
    if cover_mode and current_idx <= 0:
        return False
    if current_idx == len(images) - 1:
        return True
    # Landscape images (width > height) should be displayed as single page
    if _is_landscape(images[current_idx]):
        return True
    # If the next image in a spread would be landscape, display current as single too
    if current_idx + 1 < len(images) and _is_landscape(images[current_idx + 1]):
        return True
    return False


def get_display_step(images: List[Path], current_idx: int, cover_mode: bool = True, force_single: bool = False) -> int:
    if force_single:
        return 1
    if cover_mode and current_idx <= 0:
        return 1
    # Landscape images are displayed as single page, so advance by 1
    if _is_landscape(images[current_idx]):
        return 1
    # If the next image is landscape, advance by 1
    if current_idx + 1 < len(images) and _is_landscape(images[current_idx + 1]):
        return 1
    return 2


def get_previous_page_index(images: List[Path], current_idx: int, cover_mode: bool = True, force_single: bool = False) -> int:
    if cover_mode and current_idx <= 1:
        return 0
    idx = 1 if cover_mode else 0
    slides = [0]
    while idx < current_idx:
        slides.append(idx)
        step = get_display_step(images, idx, cover_mode, force_single)
        idx += step
    return slides[-1]



def get_progress_index(total_images: int, percent: int) -> int:
    if total_images <= 1:
        return 0
    target = int((total_images * (percent / 100)) - 1 + 0.5)
    return max(0, min(total_images - 1, target))


def _is_sixel_terminal() -> bool:
    """端末がSixelグラフィックスに対応しているかどうかを判定する。

    以下の条件のいずれかを満たす場合にSixel対応とみなす:
    - TERM が "foot" で始まる (foot terminal)
    - TERM が "xterm" を含み、かつ COLORTERM が "truecolor" (多くのxterm互換端末)
    - WT_SESSION が設定されている (Windows Terminal)
    - TERM_PROGRAM が "mintty" (Cygwin/MSYS2)
    - TERM が "mlterm" または "contour"
    - chafa が利用可能 (変換ツールがある)
    """
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    colorterm = os.environ.get("COLORTERM", "").lower()

    # 明らかにSixel非対応の端末を先に除外
    if "kitty" in term_program or "KITTY_WINDOW_ID" in os.environ:
        return False  # Kittyは独自プロトコルを使用

    # Sixel対応端末の検出
    if term.startswith("foot"):
        return True
    if term == "mlterm":
        return True
    if "contour" in term:
        return True
    if term_program == "mintty":
        return True
    if os.environ.get("WT_SESSION"):
        return True
    # xterm互換: TERMにxtermを含み、COLORTERMがtruecolor
    if "xterm" in term and colorterm == "truecolor":
        return True

    # 変換ツールの有無で判断（フォールバック）
    if shutil.which("chafa") is not None:
        # より確実な検出のためにDECRQSS制御シーケンスを試行
        try:
            import termios
            import tty
            import select

            # 端末がttyでなければスキップ
            if not sys.stdin.isatty():
                return False

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                # DECRQSS (Device Control Request Status String) で
                # 端末のグラフィックス属性（Sixel対応有無）を問い合わせ
                # 正しいシーケンス: CSI ? q (0x1b 0x5b 0x3f 0x20 0x71)
                sys.stdout.write('\x1b[?q')
                sys.stdout.flush()

                # 応答を待機 (最大200ms)
                ready, _, _ = select.select([fd], [], [], 0.2)
                if ready:
                    response = os.read(fd, 64)
                    # DECRQSS応答: \x1b[?1;2;4q の "4" がSixel対応を示す
                    # または \x1b[?1;0q の "0" が非対応を示す
                    if b'4' in response:
                        return True
                    # "0" が含まれていればSixel非対応（ただし "4" より優先度を下げる）
                    if b'0' in response:
                        return False
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass

        # DECRQSSが使えない場合、ツールがあるのでSixel対応とみなす
        return True

    return False


def _ime_off():
    """Turn off IME (Japanese input) if possible. Tries fcitx5 then ibus."""
    try:
        subprocess.run(["fcitx5-remote", "-c"], capture_output=True, timeout=1)
    except Exception:
        pass
    try:
        subprocess.run(["ibus", "engine", "xkb:us::eng"], capture_output=True, timeout=1)
    except Exception:
        pass


def _ime_restore():
    """Restore IME to previous state. Currently a no-op placeholder."""
    pass



def _truncate_by_width(text: str, max_width: int) -> str:
    """Truncate text to fit within max_width columns, accounting for wide characters."""
    try:
        import wcwidth
        result = []
        width = 0
        for ch in text:
            w = wcwidth.wcwidth(ch)
            if w < 0:
                w = 0
            if width + w > max_width:
                break
            result.append(ch)
            width += w
        return ''.join(result)
    except ImportError:
        # Fallback: truncate by character count
        return text[:max_width]


def run_app(
    stdscr=None,
    target_path: Optional[Path] = None,
    is_archive: bool = False,
    resume_key: Optional[str] = None,
):
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
            # ANSI escape sequence to clear screen (avoids os.system() which resets console mode on Windows)
            sys.stdout.write('\x1b[2J\x1b[H')
            sys.stdout.flush()
    def refresh_screen():
        if stdscr:
            stdscr.refresh()
        else:
            sys.stdout.flush()
    def draw_status(lines, cols, text, offset=0):
        # Always use direct ANSI escape to stdout (not curses) for status text,
        # because Kitty icat writes directly to the terminal and curses loses
        # track of the cursor position after image output.
        # Write to the second-to-last line to avoid terminal auto-scroll that
        # occurs when writing to the very last line.
        # Use cols-2 to avoid writing to the very last column, which can
        # cause some terminals to wrap to a new line.
        status_line = max(1, lines - 2 + offset)
        # Truncate by display width to handle wide characters (e.g. Japanese)
        max_width = max(0, cols - 2)
        truncated = _truncate_by_width(text, max_width)
        sys.__stdout__.write(f"\033[{status_line};1H{truncated:<{max_width}}")
        sys.__stdout__.flush()
    def normalize_key(key):
        if isinstance(key, int) and 32 <= key <= 126:
            return chr(key)
        return key

    def _read_byte_with_timeout(timeout_ms):
        """Read a single byte from stdin with timeout using threading.
        Returns None on timeout."""
        import threading
        result = []
        def reader():
            try:
                b = sys.stdin.buffer.read(1)
                result.append(b)
            except:
                pass
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        t.join(timeout_ms / 1000)
        if t.is_alive():
            return None
        return result[0] if result else None

    def get_input(timeout_ms=-1):
        if stdscr:
            if timeout_ms >= 0: stdscr.timeout(timeout_ms)
            else: stdscr.timeout(-1)
            try:
                return normalize_key(stdscr.get_wch())
            except curses.error:
                return None
        else:
            # Windows: sys.stdin.buffer.read(1) で VT シーケンスを読み取る
            # msvcrt.getch() は VT 入力処理をバイパスするため使用しない
            if timeout_ms >= 0:
                import time
                start = time.time()
                while not msvcrt.kbhit():
                    if (time.time() - start) * 1000 > timeout_ms:
                        return None
                    time.sleep(0.005)
                ch = sys.stdin.buffer.read(1)
            else:
                ch = sys.stdin.buffer.read(1)
            if not ch:
                return None
            if ch == b'\x03': raise KeyboardInterrupt() # Ctrl+C
            if ch == b'\x1b':
                # ESC シーケンス: 続くバイトを短いタイムアウトで読み取る
                # msvcrt.kbhit() は VT シーケンスバイトを検出しないため、
                # threading を使ってタイムアウト付き読み取りを行う
                seq = b'\x1b'
                import time
                start = time.time()
                while (time.time() - start) * 1000 < 100:
                    next_ch = _read_byte_with_timeout(50)
                    if next_ch:
                        seq += next_ch
                        start = time.time()  # バイトが来るたびにタイムアウトをリセット
                        # SGRマウスシーケンスは終端文字(M/m)まで読み続ける
                        if seq.startswith(b'\x1b[<') and next_ch in (b'M', b'm'):
                            break
                        # 矢印キーやファンクションキーは英字または~で終端
                        if seq.startswith(b'\x1b[') and next_ch in b'ABCDHPQRS~':
                            break
                    else:
                        break
                # SGRマウスシーケンス: \x1b[<Cb;Cx;CyM または m
                if seq.startswith(b'\x1b[<') and seq[-1:] in (b'M', b'm'):
                    try:
                        body = seq[3:-1].decode()
                        btn_code, mx, my = (int(v) for v in body.split(';'))
                        pressed = seq.endswith(b'M')
                        is_motion = bool(btn_code & 32)
                        if is_motion:
                            return None  # ドラッグ/移動イベントは無視
                        btn = btn_code & 3
                        if pressed:
                            if btn == 0:   # 左クリック
                                return 'MOUSE_LEFT'
                            elif btn == 2: # 右クリック
                                return 'MOUSE_RIGHT'
                            elif btn == 1: # 中クリック
                                return 'MOUSE_MIDDLE'
                    except (ValueError, UnicodeDecodeError):
                        pass
                    return None
                # 矢印キー: \x1b[A, \x1b[B, \x1b[C, \x1b[D
                if seq == b'\x1b[A': return 'KEY_UP'
                if seq == b'\x1b[B': return 'KEY_DOWN'
                if seq == b'\x1b[C': return 'KEY_RIGHT'
                if seq == b'\x1b[D': return 'KEY_LEFT'
                # Shift + 矢印: \x1b[1;2D, \x1b[1;2C
                if seq == b'\x1b[1;2D': return 'KEY_SLEFT'
                if seq == b'\x1b[1;2C': return 'KEY_SRIGHT'
                return '\x1b'  # 未知のシーケンスはESCとして扱う
            if ch == b'\r' or ch == b'\n': return '\n'
            try:
                return ch.decode('utf-8')
            except:
                return None
    # ターミナル種別の判定
    # 環境変数の確認
    # Curses 特有の初期設定
    if stdscr:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.cbreak()
        curses.noecho()
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    else:
        # Windows: カーソル非表示 (コンソールモードは main_cli で設定済み)
        sys.stdout.write('\033[?25l') # Hide cursor

    # マウス設定: SGRモード + Win32マウスモードを有効化
    # 1000: 基本マウスレポート, 1006: SGRフォーマット, 1007: Win32マウスモード(WezTerm/Windows Terminal用)
    sys.stdout.write('\x1b[?1000h\x1b[?1006h\x1b[?1007h')
    sys.stdout.flush()

    # レンダラーの自動選択
    # Kitty でも chafa を使用する（icat のオーバーレイ問題を回避）
    renderer = SixelRenderer()
    # 引数チェック
    if target_path:
        initial_dir = target_path
    elif len(sys.argv) > 1:
        initial_dir = Path(sys.argv[1]).absolute()
    else:
        initial_dir = Path.cwd().absolute()

    if is_archive:
        # フォルダが1つのサブフォルダのみを含む場合は自動で下る
        while True:
            try:
                items = list(initial_dir.iterdir())
                subdirs = [i for i in items if i.is_dir()]
                files = [i for i in items if i.is_file()]
                if len(subdirs) == 1 and len(files) == 0:
                    initial_dir = subdirs[0]
                else:
                    break
            except Exception:
                break
        archive_resume_base = initial_dir

        # 画像を含むすべてのディレクトリを検索
        extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
        dirs_with_images = []
        def has_images(d: Path) -> bool:
            try:
                return any(f.suffix.lower() in extensions for f in d.iterdir() if f.is_file())
            except Exception:
                return False

        if has_images(initial_dir):
            dirs_with_images.append(initial_dir)
        for d in sorted(initial_dir.rglob('*'), key=natural_sort_key):
            if d.is_dir() and has_images(d):
                dirs_with_images.append(d)

        if dirs_with_images:
            dirs_to_browse = dirs_with_images
        else:
            dirs_to_browse = [initial_dir]
    else:
        archive_resume_base = None
        dirs_to_browse = get_sorted_dirs(initial_dir)

    try:
        # パス比較をより確実に（正規化して比較）
        dir_idx = next(i for i, d in enumerate(dirs_to_browse) if d.resolve() == initial_dir.resolve())
    except (ValueError, StopIteration):
        dir_idx = 0
    img_idx = 0
    cover_mode = True
    reading_mode = True  # True = Manga (RTL), False = Comic (LTR)
    force_single = False  # True = force current page to display as single
    resume_state = get_resume_state(resume_key)
    if resume_state is not None:
        cover_mode = resume_state.get("cover_mode", True)
        reading_mode = resume_state.get("reading_mode", True)
    resume_dir_idx = find_resume_dir_index(dirs_to_browse, resume_state, is_archive, archive_resume_base)
    if resume_dir_idx is not None:
        dir_idx = resume_dir_idx
        img_idx = find_resume_image_index(get_sorted_images(dirs_to_browse[dir_idx]), resume_state)
    needs_redraw = True
    last_visited_dir = initial_dir
    while 0 <= dir_idx < len(dirs_to_browse):
        # フォルダ移動時は必ず再描画
        needs_redraw = True
        target_dir = dirs_to_browse[dir_idx]
        last_visited_dir = target_dir
        images = get_sorted_images(target_dir)
        num_images = len(images)
        if not images:
            dir_idx += 1
            continue
        if img_idx == -1: # 前のフォルダから戻ってきた場合（最終ページを開く）
            img_idx = num_images - 1 if num_images > 0 else 0
        while 0 <= img_idx < num_images:
            action = None # Ensure 'action' is always initialized at the start of each iteration
            if needs_redraw:
                clear_screen()
                h, w = get_term_size()
                curr_right = images[img_idx]
                use_single = should_display_single(images, img_idx, cover_mode, force_single)
                curr_left = None if use_single else images[img_idx + 1] if img_idx + 1 < num_images else None
                mode_indicator = "Cover" if cover_mode and img_idx == 0 else "NoCover" if not cover_mode else ""
                if cover_mode and img_idx == 0:
                    status = f"DIR: {target_dir.name} | Cover: {curr_right.name}"
                elif use_single:
                    status = f"DIR: {target_dir.name} | Single: {curr_right.name}"
                else:
                    l_name = curr_left.name if curr_left else "END"
                    status = f"DIR: {target_dir.name} | R: {curr_right.name} L: {l_name}"
                if not cover_mode:
                    status += " [NoCover]"
                if force_single:
                    status += " [Single]"
                if reading_mode:
                    status += " [Manga]"
                else:
                    status += " [Comic]"
                save_resume_state(resume_key, target_dir, images, img_idx, is_archive, archive_resume_base, cover_mode, reading_mode)
                # 描画前に画像をクリア（Sixel/WezTermの点滅防止のため必要な時のみ）
                renderer.clear()
                refresh_screen()
                # renderer を使って画像を出力（先に画像を描画）
                if cover_mode and img_idx == 0:
                    renderer.display_cover(curr_right, w, h)
                elif use_single:
                    renderer.display_single(curr_right, w, h)
                else:
                    # display_spread(img_right, img_left): img_left is drawn on the left side,
                    # img_right on the right side.
                    # Manga mode (RTL): lower index (earlier page) on the right, higher index on the left
                    # Comic mode (LTR): lower index (earlier page) on the left, higher index on the right
                    if reading_mode:
                        renderer.display_spread(curr_right, curr_left, w, h)
                    else:
                        renderer.display_spread(curr_left, curr_right, w, h)
                # ステータス行を画像の上に重ねて表示
                if stdscr and not renderer._is_kitty:
                    # curses モード (Kitty以外): curses の addstr/refresh で描画
                    try:
                        max_width = max(0, w - 2)
                        truncated = _truncate_by_width(status, max_width)
                        stdscr.addstr(h - 2, 0, truncated)
                        stdscr.refresh()
                    except Exception:
                        pass
                else:
                    # Kitty または Windows (非 curses) モード: sys.__stdout__ に直接書き込み
                    # Kittyでは画像がz=-1にあるため、cursesのrefreshが画像領域をスペースで上書きするのを防ぐ
                    # Kittyではcursesの行管理と実際の端末表示にズレがあるため、offset=-1で調整
                    offset = 1 if renderer._is_kitty else 0
                    draw_status(h, w, status, offset)
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
            step = get_display_step(images, img_idx, cover_mode)
            debug(f"img_idx={img_idx}, step={step}, num_images={num_images}")
            # Determine key mappings based on reading mode
            # Manga mode (RTL): Left=next, Right=prev
            # Comic mode (LTR): Left=prev, Right=next
            if reading_mode:
                key_next = ('j', curses.KEY_LEFT if stdscr else 'KEY_LEFT', '\n', '\r')
                key_prev = ('k', 'l', curses.KEY_RIGHT if stdscr else 'KEY_RIGHT')
                key_turbo_next = ('J', curses.KEY_SLEFT if stdscr else 'KEY_SLEFT')
                key_turbo_prev = ('K', 'L', curses.KEY_SRIGHT if stdscr else 'KEY_SRIGHT')
            else:
                key_next = ('j', curses.KEY_RIGHT if stdscr else 'KEY_RIGHT', '\n', '\r')
                key_prev = ('k', 'l', curses.KEY_LEFT if stdscr else 'KEY_LEFT')
                key_turbo_next = ('J', curses.KEY_SRIGHT if stdscr else 'KEY_SRIGHT')
                key_turbo_prev = ('K', 'L', curses.KEY_SLEFT if stdscr else 'KEY_SLEFT')
            if key in key_next:
                next_idx = img_idx + (1 if (cover_mode and img_idx == 0) else step)
                debug(f"Next: img_idx={img_idx}, step={step}, next_idx={next_idx}, num_images={num_images}")
                if next_idx >= num_images:
                    if dir_idx < len(dirs_to_browse) - 1:
                        dir_idx += 1
                        img_idx = 0
                        break
                else:
                    img_idx = next_idx
                needs_redraw = True
            elif key in key_turbo_next:
                # Turbo next: Jump TURBO_STEP pages
                img_idx = min(num_images - 1, img_idx + TURBO_STEP)
                needs_redraw = True
            elif key in key_prev:
                if img_idx == 0:
                    if dir_idx > 0:
                        dir_idx -= 1
                        img_idx = -1
                        break
                else:
                    img_idx = get_previous_page_index(images, img_idx, cover_mode)
                needs_redraw = True
            elif key in key_turbo_prev:
                # Turbo prev: Jump TURBO_STEP pages back
                img_idx = max(0, img_idx - TURBO_STEP)
                needs_redraw = True
            elif key == '0':
                img_idx = 0
                needs_redraw = True
            elif key in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
                percent = int(key) * 10
                img_idx = get_progress_index(num_images, percent)
                needs_redraw = True
            elif key == 'c':
                cover_mode = not cover_mode
                # Reset to first page when toggling to ensure consistent display
                img_idx = 0
                needs_redraw = True
            elif key == 'r':
                reading_mode = not reading_mode
                needs_redraw = True
            elif key == 's':
                force_single = not force_single
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
            elif key == 'MOUSE_LEFT':
                action = 'next'
            elif key == 'MOUSE_RIGHT':
                action = 'prev'
            elif key == 'MOUSE_MIDDLE':
                return last_visited_dir
            elif key == '\x1b': # ESC シーケンス (SGRマウス等の手動パース)
                try:
                    # SSH等の遅延を考慮し、timeoutを少し長めにする
                    ch = get_input(timeout_ms=150)
                    if ch == '[':
                        # CSIシーケンスの読み込み
                        seq = "["
                        while True:
                            c = get_input(timeout_ms=100)
                            if c is None:
                                break
                            seq += str(c)
                            # 終端文字 (英文字または '~') に達したら終了
                            if isinstance(c, str) and (c.isalpha() or c == '~'):
                                break
                        debug(f"Read ESC sequence: \\x1b{seq}")
                        # SGRマウスイベントのパース
                        if seq.startswith("[<") and seq.endswith(('M', 'm')):
                            m = re.match(r'\[<(\d+);(\d+);(\d+)([Mm])', seq)
                            if m:
                                btn, mx, state = int(m.group(1)), int(m.group(2)), m.group(4)
                                if state == "M":
                                    if btn in (0, 32):  # 左クリック
                                        action = 'next'
                                    elif btn in (2, 34):  # 右クリック
                                        action = 'prev'
                                    elif btn in (1, 33):  # 中クリック -> 終了
                                        return last_visited_dir
                    # バッファの掃除
                    while get_input(timeout_ms=0) is not None:
                        pass
                except Exception as e:
                    debug(f"ESC parse error: {e}")
                # continueを削除し、下のアクション実行へ流す
            elif stdscr and key == curses.KEY_MOUSE:
                try:
                    m_id, mx, my, m_z, bstate = curses.getmouse()
                    debug(f"Standard Curses Mouse: x={mx}, y={my}, bstate={hex(bstate)}")
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_RELEASED):
                        action = 'next'
                    elif bstate & (curses.BUTTON3_CLICKED | curses.BUTTON3_PRESSED | curses.BUTTON3_RELEASED):
                        action = 'prev'
                    elif bstate & (curses.BUTTON2_CLICKED | curses.BUTTON2_PRESSED | curses.BUTTON2_RELEASED):
                        return last_visited_dir
                except Exception as e:
                    debug(f"getmouse error: {e}")
            # アクションの実行とディレクトリ（巻）跨ぎ処理を一本化
            if action == 'next':
                next_idx = img_idx + (1 if (cover_mode and img_idx == 0) else get_display_step(images, img_idx, cover_mode))
                if next_idx >= num_images:
                    if dir_idx < len(dirs_to_browse) - 1:
                        dir_idx += 1
                        img_idx = 0
                        break # 内側ループを抜けて次のディレクトリへ
                else:
                    img_idx = next_idx
                needs_redraw = True
            elif action == 'prev':
                if img_idx == 0:
                    if dir_idx > 0:
                        dir_idx -= 1
                        img_idx = -1
                        break # 内側ループを抜けて前のディレクトリへ
                else:
                    img_idx = get_previous_page_index(images, img_idx, cover_mode)
                needs_redraw = True
            elif action == 'first':
                img_idx = 0
                needs_redraw = True
            elif action == 'last':
                img_idx = num_images - 2 + (num_images % 2) if num_images > 1 else 0
                needs_redraw = True
            elif action == 'next_vol':
                if dir_idx < len(dirs_to_browse) - 1:
                    dir_idx += 1
                    img_idx = 0
                    break
            elif action == 'prev_vol':
                if dir_idx > 0:
                    dir_idx -= 1
                    img_idx = 0
                    break
        else:
            dir_idx += 1
            img_idx = 0
    renderer.clear()
    print("全てのファイルの表示を終了しました。")
def main_cli():
    """Command line entry point for package installation"""
    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
        print(f"TerMa version {__version__}")
        return
    # ヘルプオプションの場合は curses を使用せずに直接表示
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(f"""TerMa - Terminal Manga Viewer
Usage: terma [directory_or_archive]
Arguments:
  directory_or_archive    Manga directory or archive (zip/tar/cbz) to view (default: current directory)
  -v, --version           Show version information
  --help                  Show this help message
Resume:
  Last viewed positions are saved to ~/.terma_resume.json and restored automatically.
Controls:
  j/Left/Enter  Next page
  k/l/Right     Previous page
  J/Shift+Left  Turbo Next ({TURBO_STEP} pages)
  K/Shift+Right Turbo Previous ({TURBO_STEP} pages)
  0            First page (cover)
  1-9          Jump to 10%-90% progress
  c            Toggle cover mode (first page as cover / start with spread)
  s            Toggle single page mode (force current page as single)
  r            Toggle reading mode (Manga RTL / Comic LTR)
  ,            Next volume
  .            Previous volume
  q/Q/h        Quit""")
        return
    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1]).absolute()
    else:
        target_path = Path.cwd().absolute()
    resume_key = target_path.resolve().as_posix()

    temp_dir_obj = None
    is_archive = False

    try:
        if target_path.is_file():
            temp_dir_obj = tempfile.TemporaryDirectory(prefix="terma_")
            extracted_path = Path(temp_dir_obj.name)
            if extract_archive(target_path, extracted_path):
                target_path = extracted_path
                is_archive = True
                extract_nested_archives(target_path)
            else:
                print(f"Error: {target_path} is not a directory or a supported archive file.")
                temp_dir_obj.cleanup()
                return

        # 初期設定 (マウス有効化、カーソル非表示)
        # Windows: コンソールモードを設定 (ECHO無効化 + VT入出力有効化)
        if os.name == 'nt':
            try:
                import ctypes
                from ctypes import wintypes
                _kernel32 = ctypes.windll.kernel32
                _STD_INPUT_HANDLE = -10
                _STD_OUTPUT_HANDLE = -11
                _ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
                _ENABLE_ECHO_INPUT = 0x0004
                _ENABLE_LINE_INPUT = 0x0002
                _ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                _ENABLE_PROCESSED_OUTPUT = 0x0001
                # 入力モード: ECHO無効 + LINE無効 + VT入力有効
                _h_in = _kernel32.GetStdHandle(_STD_INPUT_HANDLE)
                _old_in_mode = wintypes.DWORD()
                _kernel32.GetConsoleMode(_h_in, ctypes.byref(_old_in_mode))
                _new_in_mode = (
                    _old_in_mode.value
                    & ~_ENABLE_LINE_INPUT
                    & ~_ENABLE_ECHO_INPUT
                ) | _ENABLE_VIRTUAL_TERMINAL_INPUT
                if not _kernel32.SetConsoleMode(_h_in, _new_in_mode):
                    raise ctypes.WinError(ctypes.get_last_error())
                debug(f"Input console mode: 0x{_old_in_mode.value:08X} -> 0x{_new_in_mode:08X}")
                # 出力モード: VT処理有効
                _h_out = _kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
                _old_out_mode = wintypes.DWORD()
                _kernel32.GetConsoleMode(_h_out, ctypes.byref(_old_out_mode))
                _new_out_mode = _old_out_mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING | _ENABLE_PROCESSED_OUTPUT
                if not _kernel32.SetConsoleMode(_h_out, _new_out_mode):
                    raise ctypes.WinError(ctypes.get_last_error())
                debug(f"Output console mode: 0x{_old_out_mode.value:08X} -> 0x{_new_out_mode:08X}")
                # 復元用のデータを関数オブジェクトに保存
                run_app._console_restore = (_kernel32, _h_in, _h_out, _old_in_mode.value, _old_out_mode.value)
            except Exception as e:
                debug(f"Windows console mode setup failed: {e}")
        sys.stdout.write('\x1b[?1000h\x1b[?1006h\x1b[?1007h')
        sys.stdout.write('\033[?25l')
        sys.stdout.flush()
        if os.name == 'nt':
            error_msg = run_app(target_path=target_path, is_archive=is_archive, resume_key=resume_key)
        else:
            error_msg = curses.wrapper(lambda stdscr: run_app(stdscr, target_path=target_path, is_archive=is_archive, resume_key=resume_key))
        if error_msg:
            print(error_msg)
    finally:
        # 終了設定 (マウス無効化、カーソル表示)
        sys.stdout.write('\x1b[?1000l\x1b[?1006l')
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
        # Windows コンソールモードを元に戻す
        if os.name == 'nt':
            try:
                restore = getattr(run_app, '_console_restore', None)
                if restore:
                    _kernel32, _h_in, _h_out, _old_in_mode, _old_out_mode = restore
                    _kernel32.SetConsoleMode(_h_in, _old_in_mode)
                    _kernel32.SetConsoleMode(_h_out, _old_out_mode)
            except Exception as e:
                debug(f"Windows console mode restore failed: {e}")
        if temp_dir_obj:
            try:
                temp_dir_obj.cleanup()
            except Exception:
                pass
if __name__ == "__main__":
    main_cli()
