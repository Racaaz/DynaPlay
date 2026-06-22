import json
import os
import shutil
import random
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# ─────────────────────────────────────────────
#  INISIALISASI PYGAME (AUDIO ENGINE)
# ─────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
    MUSIC_END_EVENT  = pygame.USEREVENT + 1
    pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
except ImportError:
    PYGAME_AVAILABLE = False
    MUSIC_END_EVENT  = None
    print("Peringatan: Library 'pygame' belum diinstal. Jalankan: pip install pygame")


# ══════════════════════════════════════════════
#  1. MODEL — NODE & DOUBLY LINKED LIST
# ══════════════════════════════════════════════

class Node:
    """Satu simpul dalam playlist (Doubly Linked List)."""

    def __init__(self, song_id: str, judul: str, artis: str,
                 durasi: int, genre: str, play_count: int = 0):
        clean_id = song_id.strip()
        # Pastikan ekstensi .mp3 ada tepat sekali
        while clean_id.lower().endswith(".mp3.mp3"):
            clean_id = clean_id[:-4]
        if not clean_id.lower().endswith(".mp3"):
            clean_id += ".mp3"

        self.id         = clean_id
        self.judul      = judul
        self.artis      = artis
        self.durasi     = max(0, int(durasi))
        self.genre      = genre
        self.play_count = int(play_count)   # statistik putar
        self.prev: "Node | None" = None
        self.next: "Node | None" = None

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "judul":      self.judul,
            "artis":      self.artis,
            "durasi":     self.durasi,
            "genre":      self.genre,
            "play_count": self.play_count,
        }


class DoublyLinkedList:
    """Playlist berbasis Doubly Linked List dengan dukungan shuffle & pencarian."""

    def __init__(self):
        self.head:    Node | None = None
        self.tail:    Node | None = None
        self.current: Node | None = None
        self.size:    int = 0
        self._shuffle_order: list[Node] = []   # urutan acak (terpisah dari DLL asli)
        self._shuffle_idx:   int = 0

    # ── Insertion ──────────────────────────────
    def insert_tail(self, node: Node) -> None:
        if not self.head:
            self.head = self.tail = self.current = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self.size += 1

    def insert_at(self, posisi: int, node: Node) -> bool:
        if posisi < 1 or posisi > self.size + 1:
            return False
        if posisi == 1:
            if not self.head:
                self.head = self.tail = self.current = node
            else:
                node.next = self.head
                self.head.prev = node
                self.head = node
            self.size += 1
            return True
        if posisi == self.size + 1:
            self.insert_tail(node)
            return True
        temp = self.head
        for _ in range(posisi - 2):
            temp = temp.next
        node.next = temp.next
        node.prev = temp
        if temp.next:
            temp.next.prev = node
        temp.next = node
        self.size += 1
        return True

    # ── Deletion ───────────────────────────────
    def delete_by_id(self, song_id: str) -> bool:
        target = song_id.strip()
        if not target.lower().endswith(".mp3"):
            target += ".mp3"

        temp = self.head
        while temp:
            if temp.id.lower() == target.lower():
                if temp == self.current:
                    self.current = temp.next or temp.prev
                if temp.prev:
                    temp.prev.next = temp.next
                else:
                    self.head = temp.next
                if temp.next:
                    temp.next.prev = temp.prev
                else:
                    self.tail = temp.prev
                self.size -= 1
                return True
            temp = temp.next
        return False

    # ── Navigation ─────────────────────────────
    def next_song(self, shuffle_mode: bool = False) -> "Node | None":
        """Pindah ke lagu berikutnya. Jika shuffle_mode aktif, ikuti
        urutan acak (_shuffle_order) tanpa mengubah pointer next/prev asli."""
        if not self.current:
            return None
        if shuffle_mode and self._shuffle_order:
            self._shuffle_idx = (self._shuffle_idx + 1) % len(self._shuffle_order)
            self.current = self._shuffle_order[self._shuffle_idx]
            return self.current
        self.current = self.current.next or self.head
        return self.current

    def prev_song(self, shuffle_mode: bool = False) -> "Node | None":
        """Pindah ke lagu sebelumnya, juga mengikuti shuffle bila aktif."""
        if not self.current:
            return None
        if shuffle_mode and self._shuffle_order:
            self._shuffle_idx = (self._shuffle_idx - 1) % len(self._shuffle_order)
            self.current = self._shuffle_order[self._shuffle_idx]
            return self.current
        if self.current.prev:
            self.current = self.current.prev
        return self.current

    # ── Shuffle ────────────────────────────────
    def build_shuffle(self) -> None:
        """Bangun urutan pemutaran acak dari semua node di DLL.

        PENTING: ini hanya membuat daftar urutan pemutaran terpisah
        (_shuffle_order). Struktur DLL asli (head/tail/next/prev) TIDAK
        diubah sama sekali, sehingga urutan data lain (tampilan tabel,
        sort, simpan ke JSON) tetap utuh sesuai posisi aslinya.
        """
        nodes: list[Node] = []
        temp = self.head
        while temp:
            nodes.append(temp)
            temp = temp.next
        random.shuffle(nodes)
        # Lagu yang sedang berjalan ditempatkan di depan supaya playback
        # tidak melompat ke lagu lain saat shuffle baru diaktifkan.
        if self.current and self.current in nodes:
            nodes.remove(self.current)
            nodes.insert(0, self.current)
        self._shuffle_order = nodes
        self._shuffle_idx   = 0

    # ── Search ─────────────────────────────────
    def search(self, keyword: str) -> list[Node]:
        """Cari node berdasarkan judul atau artis (case-insensitive)."""
        kw = keyword.lower().strip()
        results = []
        temp = self.head
        while temp:
            if kw in temp.judul.lower() or kw in temp.artis.lower() or kw in temp.genre.lower():
                results.append(temp)
            temp = temp.next
        return results

    # ── Sort ───────────────────────────────────
    def sort_by(self, key: str = "judul") -> None:
        """Urutkan DLL berdasarkan key: 'judul', 'artis', 'durasi', 'genre', 'play_count'."""
        if self.size < 2:
            return
        nodes: list[Node] = []
        temp = self.head
        while temp:
            nodes.append(temp)
            temp = temp.next
        nodes.sort(key=lambda n: (getattr(n, key) or "").lower()
                   if isinstance(getattr(n, key), str) else getattr(n, key))
        # Susun ulang pointer
        self.head = nodes[0]
        self.tail = nodes[-1]
        for i, n in enumerate(nodes):
            n.prev = nodes[i - 1] if i > 0 else None
            n.next = nodes[i + 1] if i < len(nodes) - 1 else None


# ══════════════════════════════════════════════
#  2. CONTROLLER — AUDIO ENGINE & DATA MANAGER
# ══════════════════════════════════════════════

class AudioEngine:
    FOLDER       = "music"
    is_paused    = False
    _volume      = 0.7       # 0.0 – 1.0
    _last_play_t = 0.0       # waktu (epoch) terakhir play() dipanggil

    @classmethod
    def play(cls, node: Node | None, loop: bool = False) -> None:
        """Putar lagu. Jika loop=True, pygame mengulang track ini sendiri
        secara native (loops=-1) tanpa bergantung pada timer Python atau
        akurasi nilai durasi yang tersimpan — sehingga repeat tidak akan
        pernah membuat audio terputus/diam."""
        if not node:
            return
        os.makedirs(cls.FOLDER, exist_ok=True)
        file_path = os.path.join(cls.FOLDER, node.id)
        cls.is_paused = False
        node.play_count += 1
        cls._last_play_t = time.time()
        if PYGAME_AVAILABLE:
            try:
                if os.path.exists(file_path):
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.set_volume(cls._volume)
                    pygame.mixer.music.play(loops=-1 if loop else 0)
                else:
                    print(f"[Simulasi] File tidak ditemukan: {file_path}")
            except Exception as e:
                print(f"Gagal memutar: {e}")

    @classmethod
    def toggle_pause(cls) -> bool:
        """Return True jika sekarang dalam kondisi pause."""
        if not PYGAME_AVAILABLE:
            return cls.is_paused
        if cls.is_paused:
            pygame.mixer.music.unpause()
            cls.is_paused = False
        else:
            pygame.mixer.music.pause()
            cls.is_paused = True
        return cls.is_paused

    @classmethod
    def stop(cls) -> None:
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        cls.is_paused = False

    @classmethod
    def set_volume(cls, vol: float) -> None:
        cls._volume = max(0.0, min(1.0, vol))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(cls._volume)

    @classmethod
    def is_playing(cls) -> bool:
        if not PYGAME_AVAILABLE:
            return False
        # Beri waktu toleransi 0.3s setelah play() agar tidak false-negative
        if time.time() - cls._last_play_t < 0.3:
            return True
        return pygame.mixer.music.get_busy()

    @staticmethod
    def get_duration(filepath: str) -> int:
        """Baca durasi file MP3 (detik) menggunakan pygame."""
        if not PYGAME_AVAILABLE:
            return 0
        try:
            snd = pygame.mixer.Sound(filepath)
            return int(snd.get_length())
        except Exception:
            return 0


class DataManager:
    FILE_PATH = "playlist.json"

    @staticmethod
    def load_playlist() -> DoublyLinkedList:
        dll = DoublyLinkedList()
        if not os.path.exists(DataManager.FILE_PATH):
            return dll
        try:
            with open(DataManager.FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                node = Node(
                    item.get("id", ""),
                    item.get("judul", ""),
                    item.get("artis", ""),
                    item.get("durasi", 0),
                    item.get("genre", ""),
                    item.get("play_count", 0),
                )
                dll.insert_tail(node)
        except Exception as e:
            print(f"Error memuat JSON: {e}")
        return dll

    @staticmethod
    def save_playlist(dll: DoublyLinkedList) -> None:
        data = []
        temp = dll.head
        while temp:
            data.append(temp.to_dict())
            temp = temp.next
        try:
            with open(DataManager.FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error menyimpan JSON: {e}")


# ══════════════════════════════════════════════
#  3. VIEW 1 — COMMAND LINE INTERFACE (CLI)
# ══════════════════════════════════════════════

class PlaylistCLI:
    def __init__(self, dll: DoublyLinkedList):
        self.dll          = dll
        self.repeat_mode  = False
        self.shuffle_mode = False

    def _play_current(self) -> None:
        """Putar lagu current; jika repeat aktif, pygame loop sendiri."""
        AudioEngine.play(self.dll.current, loop=self.repeat_mode)

    @staticmethod
    def fmt(detik: int) -> str:
        return f"{detik // 60:02d}:{detik % 60:02d}"

    def tampilkan_playlist(self) -> None:
        W = 70
        batas = "═" * W
        print(f"\n╔{batas}╗")
        print(f"║  DAFTAR PLAYLIST{'':<{W-17}}║")
        print(f"╠{batas}╣")
        if self.dll.size == 0:
            print(f"║  (Playlist masih kosong){'':<{W-25}}║")
        else:
            header = f"  {'No':<4}{'Judul':<24}{'Artis':<20}{'Durasi':^8}{'Genre'}"
            print(f"║{header:<{W}}║")
            print(f"╠{'─' * W}╣")
            temp = self.dll.head
            idx  = 1
            while temp:
                marker = ">" if temp == self.dll.current else " "
                row = (f"  {marker} {idx:<3}{temp.judul[:22]:<24}"
                       f"{temp.artis[:18]:<20}[{self.fmt(temp.durasi)}]  {temp.genre[:10]}")
                print(f"║{row:<{W}}║")
                temp = temp.next
                idx += 1
        print(f"╚{batas}╝")

    def menu_utama(self) -> str:
        # _song_ended: diset True oleh watcher saat lagu habis (thread-safe)
        # _manual_skip: diset True saat user next/prev manual agar watcher
        #               tidak salah menganggap lagu selesai secara alami
        self._song_ended  = False
        self._manual_skip = False

        def _watcher():
            """Background thread: polling get_busy() untuk deteksi lagu selesai.
            HANYA set flag — tidak pernah memanggil pygame.mixer atau AudioEngine
            karena pygame audio calls HARUS dari main thread."""
            if not PYGAME_AVAILABLE:
                return
            time.sleep(0.8)   # beri waktu play() pertama agar benar-benar mulai
            while getattr(self, '_watcher_running', True):
                if AudioEngine.is_paused:
                    time.sleep(0.3)
                    continue
                if not pygame.mixer.music.get_busy():
                    if not self._manual_skip:
                        self._song_ended = True
                    self._manual_skip = False
                    # Tunggu sampai main thread memproses (play lagu baru)
                    # sebelum mulai polling lagi
                    time.sleep(1.0)
                else:
                    time.sleep(0.3)

        self._watcher_running = True
        threading.Thread(target=_watcher, daemon=True).start()

        if self.dll.current:
            self._play_current()

        while True:
            # ── Main thread: proses flag lagu selesai (SATU-SATUNYA tempat
            #    memanggil _play_current agar pygame dipanggil dari main thread)
            if self._song_ended:
                self._song_ended = False
                if not self.repeat_mode:
                    self.dll.next_song(self.shuffle_mode)
                self._play_current()

            os.system("cls" if os.name == "nt" else "clear")
            curr = self.dll.current
            W = 54

            batas = "=" * W
            print(f"+{batas}+")
            print(f"|{'  DYNAPLAY MUSIC PLAYER':^{W}}|")
            print(f"+{batas}+")
            if curr:
                print(f"|  Lagu   : {curr.judul[:W-12]:<{W-12}} |")
                print(f"|  Artis  : {curr.artis[:W-12]:<{W-12}} |")
                status_txt = "JEDA" if AudioEngine.is_paused else "BERMAIN"
                print(f"|  Status : {status_txt:<{W-12}} |")
            else:
                print(f"|{'  Tidak ada lagu yang diputar':<{W}}|")

            rep_txt = "Aktif" if self.repeat_mode  else "Mati"
            shf_txt = "Aktif" if self.shuffle_mode else "Mati"
            vol_bar = "#" * int(AudioEngine._volume * 10)
            vol_pct = int(AudioEngine._volume * 100)
            print(f"|{'-' * W}|")
            rep_shf = f"  Repeat: {rep_txt:<8}  Shuffle: {shf_txt}"
            print(f"|{rep_shf:<{W}}|")
            vol_line = f"  Volume: [{vol_bar:<10}] {vol_pct:>3}%"
            print(f"|{vol_line:<{W}}|")
            print(f"+{batas}+")
            menu_items = [
                (" 1. Lagu Berikutnya",  " 8. Shuffle"),
                (" 2. Lagu Sebelumnya",  " 9. Volume (+/-)"),
                (" 3. Pause / Resume",   "10. Cari Lagu"),
                (" 4. Tambah Lagu",      "11. Urutkan Playlist"),
                (" 5. Hapus Lagu",       "12. Pindah ke GUI"),
                (" 6. Lihat Playlist",   "13. Keluar"),
                (" 7. Repeat One",       "")
            ]
            for kiri, kanan in menu_items:
                baris = f"  {kiri:<24}  {kanan}"
                print(f"|{baris:<{W}}|")
            print(f"+{batas}+")

            # Jalankan input() di thread terpisah agar main thread tetap
            # bisa mengecek _song_ended setiap 0.5 detik (non-blocking wait).
            _hasil = [None]
            def _baca_input():
                try:
                    _hasil[0] = input("Pilih Menu: ").strip()
                except EOFError:
                    _hasil[0] = ""
            _t = threading.Thread(target=_baca_input, daemon=True)
            _t.start()
            while _hasil[0] is None:
                # Proses flag lagu selesai sambil menunggu input user
                if self._song_ended:
                    self._song_ended = False
                    if not self.repeat_mode:
                        self.dll.next_song(self.shuffle_mode)
                    self._play_current()
                _t.join(timeout=0.5)
            pilihan = _hasil[0]

            if pilihan == "1":
                self._manual_skip = True
                self.dll.next_song(self.shuffle_mode)
                self._play_current()

            elif pilihan == "2":
                self._manual_skip = True
                self.dll.prev_song(self.shuffle_mode)
                self._play_current()

            elif pilihan == "3":
                if self.dll.current:
                    AudioEngine.toggle_pause()

            elif pilihan == "4":
                self._cli_tambah()

            elif pilihan == "5":
                self._cli_hapus()

            elif pilihan == "6":
                self.tampilkan_playlist()
                input("Tekan Enter...")

            elif pilihan == "7":
                self.repeat_mode = not self.repeat_mode
                # Terapkan langsung ke audio yang sedang berjalan
                if self.dll.current and not AudioEngine.is_paused:
                    self._play_current()

            elif pilihan == "8":
                self.shuffle_mode = not self.shuffle_mode
                if self.shuffle_mode:
                    self.dll.build_shuffle()
                    print(f"\n[✓] Shuffle AKTIF — urutan putar diacak ({self.dll.size} lagu)")
                else:
                    print("\n[✗] Shuffle MATI — kembali ke urutan normal")
                input("Tekan Enter...")

            elif pilihan == "9":
                self._cli_volume()

            elif pilihan == "10":
                self._cli_cari()

            elif pilihan == "11":
                self._cli_sort()

            elif pilihan == "12":
                self._watcher_running = False
                return "GUI"

            elif pilihan == "13":
                self._watcher_running = False
                AudioEngine.stop()
                DataManager.save_playlist(self.dll)
                print("\nTerima kasih telah menggunakan DynaPlay! 🎵")
                sys.exit()

    def _cli_tambah(self) -> None:
        print("\n── Tambah Lagu ──────────────────")
        try:
            pos    = int(input(f"Posisi sisip (1–{self.dll.size + 1}): "))
            sid    = input("Nama file (misal: lagu.mp3): ")
            judul  = input("Judul lagu: ")
            artis  = input("Nama artis: ")
            durasi = int(input("Durasi (detik): "))
            genre  = input("Genre: ")
            node   = Node(sid, judul, artis, durasi, genre)
            if self.dll.insert_at(pos, node):
                DataManager.save_playlist(self.dll)
                print("[✓] Lagu berhasil ditambahkan!")
                if self.dll.size == 1:
                    self._play_current()
            else:
                print("[✗] Posisi di luar jangkauan!")
        except ValueError:
            print("[✗] Input tidak valid!")
        input("Tekan Enter...")

    def _cli_hapus(self) -> None:
        print("\n── Hapus Lagu ───────────────────")
        sid = input("ID/Nama file lagu: ")
        prev_curr = self.dll.current
        if self.dll.delete_by_id(sid):
            DataManager.save_playlist(self.dll)
            print("[✓] Lagu berhasil dihapus!")
            if prev_curr != self.dll.current:
                self._play_current()
        else:
            print("[✗] ID tidak ditemukan!")
        input("Tekan Enter...")

    def _cli_volume(self) -> None:
        print(f"\n── Atur Volume ──────────────────")
        print(f"  Volume saat ini : {int(AudioEngine._volume * 100)}%")
        print(f"  Masukkan angka antara 0 hingga 100")
        try:
            raw = input("  Volume baru (0-100): ").strip()
            vol = float(raw)
            if vol < 0 or vol > 100:
                print("[✗] Volume harus antara 0 sampai 100!")
            else:
                AudioEngine.set_volume(vol / 100)
                vol_bar = "#" * int(AudioEngine._volume * 10)
                print(f"[✓] Volume diatur ke {int(AudioEngine._volume * 100)}% [{vol_bar:<10}]")
        except ValueError:
            print("[✗] Input tidak valid! Masukkan angka antara 0 sampai 100.")
        input("Tekan Enter...")

    def _cli_cari(self) -> None:
        kw      = input("Kata kunci pencarian: ")
        results = self.dll.search(kw)
        if results:
            print(f"\nDitemukan {len(results)} lagu:")
            for i, n in enumerate(results, 1):
                print(f"  {i}. {n.judul} – {n.artis} [{self.fmt(n.durasi)}]")
        else:
            print("Tidak ada lagu yang cocok.")
        input("Tekan Enter...")

    def _cli_sort(self) -> None:
        print("Urutkan berdasarkan: 1.Judul  2.Artis  3.Durasi  4.Genre  5.Sering Diputar")
        pilihan = input("Pilih (1–5): ").strip()
        keys    = {"1": "judul", "2": "artis", "3": "durasi", "4": "genre", "5": "play_count"}
        if pilihan in keys:
            self.dll.sort_by(keys[pilihan])
            DataManager.save_playlist(self.dll)
            print("[✓] Playlist berhasil diurutkan!")
        else:
            print("[✗] Pilihan tidak valid!")
        input("Tekan Enter...")


# ══════════════════════════════════════════════
#  4. VIEW 2 — GRAPHICAL USER INTERFACE (GUI)
# ══════════════════════════════════════════════

# Palet warna DynaPlay (Spotify-inspired dark mode)
C = {
    "bg":      "#0D0D0D",
    "surface": "#181818",
    "card":    "#242424",
    "hover":   "#2A2A2A",
    "accent":  "#1DB954",
    "accent2": "#1ED760",
    "danger":  "#E22134",
    "warn":    "#F59B23",
    "text":    "#FFFFFF",
    "muted":   "#B3B3B3",
    "dim":     "#535353",
}

VISUALIZER_FRAMES = [
    "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁",
    "▂▃▄▅▆▇█▇▆▅▄▃▂▁▂",
    "▄▅▆▇█▇▆▅▄▃▂▁▂▃▄",
    "▆▇█▇▆▅▄▃▂▁▂▃▄▅▆",
    "█▇▆▅▄▃▂▁▂▃▄▅▆▇█",
    "▇▆▅▄▃▂▁▂▃▄▅▆▇█▇",
]


class PlaylistGUI:
    def __init__(self, root: tk.Tk, dll: DoublyLinkedList):
        self.root         = root
        self.dll          = dll
        self.repeat_mode  = False
        self.shuffle_mode = False
        self._prog_secs   = 0
        self._anim_run    = False
        self._after_id    = None
        self._vis_idx     = 0
        self._search_var  = tk.StringVar()

        self._setup_window()
        self._build_ui()
        self._refresh_ui()

        if self.dll.current:
            self._play_current()
            self._anim_run = True

        self._tick()

    def _play_current(self) -> None:
        """Putar lagu current. Jika repeat aktif, pygame meloop sendiri
        (loops=-1) sehingga audio tidak pernah terputus oleh timer Python."""
        AudioEngine.play(self.dll.current, loop=self.repeat_mode)

    # ── Window Setup ───────────────────────────
    def _setup_window(self) -> None:
        self.root.title("DynaPlay — Premium Music Player")
        self.root.geometry("950x620")
        self.root.minsize(780, 520)
        self.root.configure(bg=C["bg"])
        try:
            self.root.iconbitmap("")        # kosong = default
        except Exception:
            pass

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                         background=C["surface"], foreground=C["text"],
                         rowheight=34, fieldbackground=C["surface"],
                         borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                         background=C["bg"], foreground=C["muted"],
                         relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", C["card"])],
                  foreground=[("selected", C["accent"])])
        style.configure("TScrollbar",
                         background=C["card"], troughcolor=C["surface"],
                         arrowcolor=C["dim"], borderwidth=0)
        style.configure("Progress.Horizontal.TProgressbar",
                         troughcolor=C["card"], background=C["accent"],
                         thickness=4, borderwidth=0)
        style.configure("Vol.Horizontal.TProgressbar",
                         troughcolor=C["card"], background=C["muted"],
                         thickness=3, borderwidth=0)

    # ── UI Builder ─────────────────────────────
    def _build_ui(self) -> None:
        # ── TOP BAR (Search + Title)
        top = tk.Frame(self.root, bg=C["bg"], height=46)
        top.pack(fill="x", padx=18, pady=(10, 0))
        top.pack_propagate(False)

        tk.Label(top, text="🎵 DynaPlay", font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(side="left")

        # Search bar
        search_frame = tk.Frame(top, bg=C["card"], padx=8, pady=4)
        search_frame.pack(side="right", padx=(0, 0))
        tk.Label(search_frame, text="🔍", font=("Segoe UI", 10),
                 bg=C["card"], fg=C["muted"]).pack(side="left")
        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                bg=C["card"], fg=C["text"], insertbackground=C["text"],
                                bd=0, font=("Segoe UI", 10), width=22)
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_tree())
        tk.Label(search_frame, text="Cari lagu…", font=("Segoe UI", 9),
                 bg=C["card"], fg=C["dim"]).pack(side="right")

        # ── BODY (sidebar + playlist)
        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=10)

        # LEFT sidebar
        sidebar = tk.Frame(body, bg=C["surface"], width=190)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="LIBRARY", font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["dim"]).pack(anchor="w", padx=14, pady=(14, 6))

        self._btn_add = self._sidebar_btn(sidebar, "➕  Tambah Lagu", self._popup_insert,
                                           bg=C["accent"], fg="black")
        self._sidebar_btn(sidebar, "❌  Hapus Terpilih", self._action_delete,
                           bg=C["danger"], fg="white")

        sep = tk.Frame(sidebar, bg=C["card"], height=1)
        sep.pack(fill="x", padx=14, pady=10)

        tk.Label(sidebar, text="URUTKAN", font=("Segoe UI", 8, "bold"),
                 bg=C["surface"], fg=C["dim"]).pack(anchor="w", padx=14, pady=(0, 6))
        sort_keys = [("Judul", "judul"), ("Artis", "artis"),
                     ("Durasi", "durasi"), ("Sering Diputar", "play_count")]
        for label, key in sort_keys:
            self._sidebar_btn(sidebar, f"⇅  {label}", lambda k=key: self._sort(k))

        tk.Button(sidebar, text="💻  Mode CLI",
                  font=("Segoe UI", 9, "bold"), bg=C["hover"], fg=C["muted"],
                  activebackground=C["card"], activeforeground=C["text"],
                  bd=0, relief="flat", cursor="hand2", padx=10, pady=6,
                  command=self._switch_to_cli).pack(side="bottom", fill="x",
                                                     padx=14, pady=12)

        # PLAYLIST TABLE
        tbl_frame = tk.Frame(body, bg=C["bg"])
        tbl_frame.pack(side="right", fill="both", expand=True)

        # Column info: (id, header, width, anchor)
        cols_cfg = [
            ("#", 34, "center"),
            ("judul", 160, "w"),
            ("artis", 120, "w"),
            ("durasi", 64, "center"),
            ("genre", 90, "w"),
            ("plays", 56, "center"),
        ]
        col_ids = [c[0] for c in cols_cfg]
        self.tree = ttk.Treeview(tbl_frame, columns=col_ids, show="headings",
                                  selectmode="browse")
        headers = {"#": "#", "judul": "JUDUL", "artis": "ARTIS",
                   "durasi": "DURASI", "genre": "GENRE", "plays": "▶"}
        for cid, w, anc in cols_cfg:
            self.tree.heading(cid, text=headers[cid],
                              command=lambda c=cid: self._sort_from_heading(c))
            self.tree.column(cid, width=w, anchor=anc, minwidth=30)

        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<Double-1>", self._on_double_click)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(fill="y", side="right")

        # ── BOTTOM PLAYER BAR
        bar = tk.Frame(self.root, bg=C["surface"], height=96)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # Song meta (left)
        meta = tk.Frame(bar, bg=C["surface"], width=240)
        meta.pack(side="left", fill="y", padx=20)
        meta.pack_propagate(False)
        self.lbl_title  = tk.Label(meta, text="Tidak ada lagu",
                                    font=("Segoe UI", 11, "bold"),
                                    bg=C["surface"], fg=C["text"], anchor="w")
        self.lbl_title.pack(fill="x", pady=(18, 2))
        self.lbl_sub    = tk.Label(meta, text="—",
                                    font=("Segoe UI", 9),
                                    bg=C["surface"], fg=C["muted"], anchor="w")
        self.lbl_sub.pack(fill="x")

        # Visualizer (left-center)
        self.lbl_vis = tk.Label(bar, text="", font=("Consolas", 9),
                                 bg=C["surface"], fg=C["accent"], width=18)
        self.lbl_vis.pack(side="left", padx=10)

        # Volume (right)
        vol_frame = tk.Frame(bar, bg=C["surface"])
        vol_frame.pack(side="right", padx=20, pady=20, fill="y")
        tk.Label(vol_frame, text="🔊", font=("Segoe UI", 10),
                 bg=C["surface"], fg=C["muted"]).pack(side="left")
        self.vol_bar = ttk.Scale(vol_frame, from_=0, to=100, orient="horizontal",
                                  length=90, command=self._on_volume)
        self.vol_bar.set(AudioEngine._volume * 100)
        self.vol_bar.pack(side="left", padx=4)

        # Center controls
        center = tk.Frame(bar, bg=C["surface"])
        center.pack(fill="both", expand=True, pady=6)

        btn_row = tk.Frame(center, bg=C["surface"])
        btn_row.pack()

        self.btn_shuf   = self._ctrl_btn(btn_row, "🔀", self._toggle_shuffle, small=True)
        self.btn_prev   = self._ctrl_btn(btn_row, "⏮", self._action_prev)
        self.btn_play   = self._ctrl_btn(btn_row, "⏸", self._action_pause, primary=True)
        self.btn_next   = self._ctrl_btn(btn_row, "⏭", self._action_next)
        self.btn_rep    = self._ctrl_btn(btn_row, "🔁", self._toggle_repeat, small=True)

        # Progress row
        prog_row = tk.Frame(center, bg=C["surface"])
        prog_row.pack(fill="x", padx=50, pady=(4, 0))

        self.lbl_curr = tk.Label(prog_row, text="0:00", font=("Segoe UI", 8),
                                  bg=C["surface"], fg=C["muted"], width=5)
        self.lbl_curr.pack(side="left")

        self.progress = ttk.Progressbar(prog_row, orient="horizontal",
                                         mode="determinate",
                                         style="Progress.Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True, padx=6)

        self.lbl_total = tk.Label(prog_row, text="0:00", font=("Segoe UI", 8),
                                   bg=C["surface"], fg=C["muted"], width=5)
        self.lbl_total.pack(side="right")

        # Click on progress bar to seek (simulated)
        self.progress.bind("<Button-1>", self._on_progress_click)

    # ── UI Helpers ─────────────────────────────
    def _sidebar_btn(self, parent, text, cmd, bg=None, fg=None) -> tk.Button:
        bg = bg or C["hover"]
        fg = fg or C["text"]
        btn = tk.Button(parent, text=text, font=("Segoe UI", 9, "bold"),
                        bg=bg, fg=fg, activebackground=C["card"],
                        activeforeground=C["text"], bd=0, relief="flat",
                        cursor="hand2", padx=10, pady=7, anchor="w",
                        command=cmd)
        btn.pack(fill="x", padx=14, pady=2)
        return btn

    def _ctrl_btn(self, parent, text, cmd, primary=False, small=False) -> tk.Button:
        if primary:
            cfg = dict(bg=C["text"], fg="black", font=("Segoe UI", 15, "bold"),
                       width=3, relief="flat")
        elif small:
            cfg = dict(bg=C["surface"], fg=C["dim"], font=("Segoe UI", 12),
                       relief="flat")
        else:
            cfg = dict(bg=C["surface"], fg=C["muted"], font=("Segoe UI", 16),
                       relief="flat")
        btn = tk.Button(parent, text=text, bd=0, cursor="hand2",
                        activebackground=C["surface"], **cfg, command=cmd)
        btn.pack(side="left", padx=10 if primary else 6)
        return btn

    @staticmethod
    def _fmt(s: int) -> str:
        return f"{s // 60}:{s % 60:02d}"

    # ── Tree Refresh ───────────────────────────
    def _refresh_tree(self) -> None:
        kw = self._search_var.get().lower().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        temp = self.dll.head
        idx  = 1
        while temp:
            if kw and kw not in temp.judul.lower() and kw not in temp.artis.lower() \
               and kw not in temp.genre.lower():
                temp = temp.next
                idx += 1
                continue
            tag = "playing" if temp == self.dll.current else "normal"
            self.tree.insert("", "end", iid=temp.id,
                              values=(idx, temp.judul, temp.artis,
                                      self._fmt(temp.durasi), temp.genre,
                                      temp.play_count),
                              tags=(tag,))
            temp = temp.next
            idx += 1
        self.tree.tag_configure("playing", background="#1E3A2A", foreground=C["accent"])
        self.tree.tag_configure("normal",  background=C["surface"], foreground=C["text"])

    def _refresh_ui(self) -> None:
        curr = self.dll.current
        if curr:
            self.lbl_title.config(text=curr.judul)
            self.lbl_sub.config(text=f"{curr.artis}  •  {curr.genre}  •  ▶ {curr.play_count}×")
            self.lbl_total.config(text=self._fmt(curr.durasi))
            self.btn_play.config(text="⏸" if not AudioEngine.is_paused else "▶")
        else:
            self.lbl_title.config(text="Tidak ada lagu")
            self.lbl_sub.config(text="—")
            self.lbl_total.config(text="0:00")
            self.lbl_curr.config(text="0:00")
            self.progress["value"] = 0
            self.btn_play.config(text="▶")

        # Indikator warna tombol repeat/shuffle (hijau = aktif)
        self.btn_rep.config(fg=C["accent"]  if self.repeat_mode  else C["dim"])
        self.btn_shuf.config(fg=C["accent"] if self.shuffle_mode else C["dim"])

        self._refresh_tree()

    # ── Playback Controls ──────────────────────
    def _action_next(self) -> None:
        self.dll.next_song(self.shuffle_mode)
        self._play_current()
        self._prog_secs = 0
        self._anim_run  = True
        self._refresh_ui()

    def _action_prev(self) -> None:
        self.dll.prev_song(self.shuffle_mode)
        self._play_current()
        self._prog_secs = 0
        self._anim_run  = True
        self._refresh_ui()

    def _action_pause(self) -> None:
        if not self.dll.current:
            return
        paused = AudioEngine.toggle_pause()
        self._anim_run = not paused
        self._refresh_ui()

    def _toggle_repeat(self) -> None:
        self.repeat_mode = not self.repeat_mode
        # Terapkan langsung ke audio yang sedang berjalan supaya pygame
        # mengaktifkan/melepas mode loop tanpa harus next/prev dulu.
        if self.dll.current and not AudioEngine.is_paused:
            self._play_current()
            self._prog_secs = 0
        self._refresh_ui()

    def _toggle_shuffle(self) -> None:
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.dll.build_shuffle()
        self._refresh_ui()

    def _on_volume(self, val) -> None:
        AudioEngine.set_volume(float(val) / 100)

    def _on_progress_click(self, event) -> None:
        """Klik pada progress bar untuk seek (simulasi)."""
        if not self.dll.current:
            return
        w = self.progress.winfo_width()
        if w == 0:
            return
        ratio = event.x / w
        self._prog_secs = int(ratio * self.dll.current.durasi)
        self.progress["value"] = ratio * 100
        self.lbl_curr.config(text=self._fmt(self._prog_secs))

    def _on_double_click(self, event) -> None:
        """Double-click baris untuk langsung memutar lagu itu."""
        sel = self.tree.selection()
        if not sel:
            return
        song_id = sel[0]          # iid = node.id
        temp = self.dll.head
        while temp:
            if temp.id == song_id:
                self.dll.current = temp
                self._play_current()
                self._prog_secs = 0
                self._anim_run  = True
                self._refresh_ui()
                return
            temp = temp.next

    # ── CRUD Popups ────────────────────────────
    def _popup_insert(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Tambah Lagu Baru")
        win.geometry("400x380")
        win.configure(bg=C["surface"])
        win.resizable(False, False)
        win.grab_set()

        GENRE_OPTIONS = ["Pop", "Hip-Hop", "EDM", "R&B", "Jazz",
                         "Rock", "Classic", "Country", "Traditional"]

        # Field biasa (baris 0–4): Posisi, File/ID, Judul, Artis, Durasi
        plain_fields = [
            ("Posisi:", str(self.dll.size + 1)),
            ("File / ID:", ""),
            ("Judul:", ""),
            ("Artis:", ""),
            ("Durasi (detik):", "0"),
        ]
        entries: list[tk.Entry] = []

        for i, (lbl, default) in enumerate(plain_fields):
            tk.Label(win, text=lbl, bg=C["surface"], fg=C["muted"],
                     font=("Segoe UI", 9, "bold"), width=16,
                     anchor="e").grid(row=i, column=0, padx=(14, 4), pady=7, sticky="e")
            ent = tk.Entry(win, bg=C["card"], fg=C["text"],
                           insertbackground=C["text"], bd=0, relief="solid",
                           font=("Segoe UI", 10), width=22)
            ent.insert(0, default)
            ent.grid(row=i, column=1, padx=4, pady=7, sticky="ew")
            entries.append(ent)
        win.columnconfigure(1, weight=1)

        # Baris 5 — Genre (Combobox dropdown)
        tk.Label(win, text="Genre:", bg=C["surface"], fg=C["muted"],
                 font=("Segoe UI", 9, "bold"), width=16,
                 anchor="e").grid(row=5, column=0, padx=(14, 4), pady=7, sticky="e")

        style = ttk.Style()
        style.configure("Genre.TCombobox",
                         fieldbackground=C["card"],
                         background=C["card"],
                         foreground=C["text"],
                         selectbackground=C["accent"],
                         selectforeground="black",
                         arrowcolor=C["accent"])
        style.map("Genre.TCombobox",
                  fieldbackground=[("readonly", C["card"])],
                  selectbackground=[("readonly", C["hover"])],
                  foreground=[("readonly", C["text"])])

        genre_var = tk.StringVar(value="Pop")
        genre_cb = ttk.Combobox(win, textvariable=genre_var,
                                values=GENRE_OPTIONS, state="readonly",
                                font=("Segoe UI", 10), width=20,
                                style="Genre.TCombobox")
        genre_cb.grid(row=5, column=1, padx=4, pady=7, sticky="ew")

        def browse() -> None:
            path = filedialog.askopenfilename(
                title="Pilih file MP3",
                filetypes=[("Audio MP3", "*.mp3"), ("Semua File", "*.*")])
            if not path:
                return
            fname = os.path.basename(path)
            entries[1].delete(0, "end"); entries[1].insert(0, fname)
            entries[2].delete(0, "end"); entries[2].insert(0, os.path.splitext(fname)[0])
            os.makedirs(AudioEngine.FOLDER, exist_ok=True)
            dest = os.path.join(AudioEngine.FOLDER, fname)
            try:
                if not os.path.exists(dest):
                    shutil.copy(path, dest)
                dur = AudioEngine.get_duration(dest)
                entries[4].delete(0, "end"); entries[4].insert(0, str(dur or 180))
            except Exception as e:
                messagebox.showerror("Error", f"Gagal memproses file:\n{e}", parent=win)

        tk.Button(win, text="📁 Browse", font=("Segoe UI", 9),
                  bg=C["card"], fg=C["accent"], bd=0, cursor="hand2",
                  command=browse).grid(row=1, column=2, padx=6)

        def simpan() -> None:
            try:
                pos   = int(entries[0].get())
                sid   = entries[1].get().strip()
                if not sid:
                    messagebox.showerror("Error", "Nama file tidak boleh kosong!", parent=win)
                    return
                genre_val = genre_var.get()
                node = Node(sid, entries[2].get(), entries[3].get(),
                            int(entries[4].get() or 0), genre_val)
                if self.dll.insert_at(pos, node):
                    DataManager.save_playlist(self.dll)
                    if self.dll.size == 1:
                        self._play_current()
                        self._anim_run = True
                    self._prog_secs = 0
                    self._refresh_ui()
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Posisi tidak valid!", parent=win)
            except ValueError:
                messagebox.showerror("Error", "Posisi dan Durasi harus angka!", parent=win)

        tk.Button(win, text="  Simpan  ", font=("Segoe UI", 10, "bold"),
                  bg=C["accent"], fg="black", bd=0, relief="flat",
                  cursor="hand2", pady=7,
                  command=simpan).grid(row=6, column=0, columnspan=3, pady=18)

    def _action_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Peringatan", "Pilih lagu di playlist terlebih dahulu!")
            return
        song_id  = sel[0]           # iid = node.id
        # cari judul untuk tampilan
        temp = self.dll.head
        judul = song_id
        while temp:
            if temp.id == song_id:
                judul = temp.judul
                break
            temp = temp.next
        if not messagebox.askyesno("Konfirmasi Hapus",
                                    f'Hapus lagu:\n\u201c{judul}\u201d?'):
            return
        prev_curr = self.dll.current
        if self.dll.delete_by_id(song_id):
            DataManager.save_playlist(self.dll)
            if prev_curr != self.dll.current:
                self._play_current()
                self._anim_run = True
            self._prog_secs = 0
            self._refresh_ui()

    def _sort(self, key: str) -> None:
        self.dll.sort_by(key)
        DataManager.save_playlist(self.dll)
        self._refresh_tree()

    def _sort_from_heading(self, col: str) -> None:
        key_map = {"judul": "judul", "artis": "artis",
                   "durasi": "durasi", "genre": "genre", "plays": "play_count"}
        if col in key_map:
            self._sort(key_map[col])

    # ── Animation Tick (1 detik) ───────────────
    def _tick(self) -> None:
        curr = self.dll.current

        if self._anim_run and curr and not AudioEngine.is_paused:
            self._prog_secs += 1

            if self._prog_secs >= curr.durasi:
                if self.repeat_mode:
                    # Audio sudah di-loop secara NATIVE oleh pygame
                    # (AudioEngine.play(..., loop=True) → loops=-1), jadi
                    # di sini kita HANYA mereset tampilan progress bar
                    # visual dan menambah statistik putar — TIDAK
                    # memanggil play() lagi, agar audio tidak terputus.
                    self._prog_secs = 0
                    curr.play_count += 1
                    self.progress["value"] = 0
                    self.lbl_curr.config(text="0:00")
                    self._refresh_ui()
                else:
                    # Lagu habis → lanjut ke lagu berikutnya
                    self._action_next()
            else:
                # ── Masih berjalan ───────────────────────
                pct = (self._prog_secs / curr.durasi) * 100
                self.progress["value"] = pct
                self.lbl_curr.config(text=self._fmt(self._prog_secs))
                self._vis_idx = (self._vis_idx + 1) % len(VISUALIZER_FRAMES)
                self.lbl_vis.config(text=VISUALIZER_FRAMES[self._vis_idx])

        elif AudioEngine.is_paused:
            self.lbl_vis.config(text="  ||  ")

        else:
            # Tidak ada yang diputar
            self.lbl_vis.config(text="")
            if not curr:
                self.progress["value"] = 0
                self.lbl_curr.config(text="0:00")

        self._after_id = self.root.after(1000, self._tick)

    # ── Switch ─────────────────────────────────
    def _switch_to_cli(self) -> None:
        if self._after_id:
            self.root.after_cancel(self._after_id)
        AudioEngine.stop()
        DataManager.save_playlist(self.dll)
        self.root.destroy()


# ══════════════════════════════════════════════
#  5. MAIN ORCHESTRATOR
# ══════════════════════════════════════════════

def main() -> None:
    playlist = DataManager.load_playlist()
    mode     = "CLI"   # mulai dari CLI dulu

    while True:
        if mode == "CLI":
            cli  = PlaylistCLI(playlist)
            mode = cli.menu_utama()      # returns "GUI"

        elif mode == "GUI":
            root = tk.Tk()
            PlaylistGUI(root, playlist)
            root.mainloop()
            mode = "CLI"


if __name__ == "__main__":
    main()