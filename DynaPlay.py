import json
import os
import random
import sys
import tkinter as tk
from tkinter import messagebox, ttk

# Inisialisasi Pygame Mixer untuk Audio Realistis
try:
    import pygame
    pygame.mixer.init()
except ImportError:
    print("Peringatan: Library 'pygame' belum diinstal. Jalankan: pip install pygame")

# ==========================================
# 1. MODEL: NODE & DOUBLY LINKED LIST (DLL)
# ==========================================

class Node:
    def __init__(self, song_id, judul, artis, durasi, genre):
        # Otomatis bersihkan nama ID agar selalu berakhiran single '.mp3'
        clean_id = song_id.strip()
        if clean_id.lower().endswith(".mp3"):
            # Jika user mengetik .mp3.mp3 secara tidak sengaja, kita bersihkan
            while clean_id.lower().endswith(".mp3.mp3"):
                clean_id = clean_id[:-4]
        else:
            clean_id += ".mp3"
            
        self.id = clean_id  
        self.judul = judul
        self.artis = artis
        self.durasi = int(durasi)  
        self.genre = genre
        self.prev = None
        self.next = None

    def to_dict(self):
        return {
            "id": self.id,
            "judul": self.judul,
            "artis": self.artis,
            "durasi": self.durasi,
            "genre": self.genre
        }

class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.current = None
        self.size = 0

    def insert_tail(self, node):
        if not self.head:
            self.head = node
            self.tail = node
            self.current = node
        else:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
        self.size += 1

    def insert_at(self, posisi, node):
        if posisi < 1 or posisi > self.size + 1:
            return False

        if posisi == 1:
            if not self.head:
                self.head = node
                self.tail = node
                self.current = node
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

    def delete_by_id(self, song_id):
        if not self.head:
            return False

        # Cek keselarasan ekstensi untuk penghapusan aman
        target_id = song_id.strip()
        if not target_id.lower().endswith(".mp3"):
            target_id += ".mp3"

        temp = self.head
        while temp:
            if temp.id.lower() == target_id.lower():
                if temp == self.current:
                    self.current = temp.next if temp.next else temp.prev

                if temp == self.head:
                    self.head = temp.next
                    if self.head:
                        self.head.prev = None
                    else:
                        self.tail = None
                elif temp == self.tail:
                    self.tail = temp.prev
                    if self.tail:
                        self.tail.next = None
                    else:
                        self.head = None
                else:
                    temp.prev.next = temp.next
                    temp.next.prev = temp.prev

                self.size -= 1
                return True
            temp = temp.next
        return False

    def next_song(self, repeat_mode=False):
        if not self.current:
            return None
        if self.current.next:
            self.current = self.current.next
        elif repeat_mode:
            self.current = self.head
        return self.current

    def prev_song(self):
        if not self.current:
            return None
        if self.current.prev:
            self.current = self.current.prev
        return self.current


# ==========================================
# 2. CONTROLLER: AUDIO ENGINE & DATA MANAGER
# ==========================================

class AudioEngine:
    FOLDER = "music"
    is_paused = False  # State Tracker Fitur Jeda

    @staticmethod
    def play(node):
        if not node:
            return
        
        if not os.path.exists(AudioEngine.FOLDER):
            os.makedirs(AudioEngine.FOLDER)

        file_path = os.path.join(AudioEngine.FOLDER, node.id)
        AudioEngine.is_paused = False
        
        try:
            if 'pygame' in sys.modules and os.path.exists(file_path):
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
            else:
                print(f"\n[Sistem Audio] File '{file_path}' tidak ditemukan (Simulasi Berjalan).")
        except Exception as e:
            print(f"\nGagal memutar audio: {e}")

    @staticmethod
    def toggle_pause():
        """Mengontrol fungsi jeda (Pause / Resume) musik"""
        if 'pygame' not in sys.modules:
            return False
            
        if AudioEngine.is_paused:
            pygame.mixer.music.unpause()  # PERBAIKAN: Menggunakan unpause(), hapus baris unshare()
            AudioEngine.is_paused = False
        else:
            pygame.mixer.music.pause()    # Pause musik
            AudioEngine.is_paused = True
        return AudioEngine.is_paused

    @staticmethod
    def stop():
        if 'pygame' in sys.modules:
            pygame.mixer.music.stop()
        AudioEngine.is_paused = False

class DataManager:
    FILE_PATH = "playlist.json"

    @staticmethod
    def load_playlist():
        dll = DoublyLinkedList()
        if not os.path.exists(DataManager.FILE_PATH):
            return dll
        
        try:
            with open(DataManager.FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    node = Node(item["id"], item["judul"], item["artis"], item["durasi"], item["genre"])
                    dll.insert_tail(node)
        except Exception as e:
            print(f"Error saat memuat data JSON: {e}")
        return dll

    @staticmethod
    def save_playlist(dll):
        data = []
        temp = dll.head
        while temp:
            data.append(temp.to_dict())
            temp = temp.next
        
        try:
            with open(DataManager.FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saat menyimpan ke JSON: {e}")


# ==========================================
# 3. VIEW 1: COMMAND LINE INTERFACE (CLI)
# ==========================================

class PlaylistCLI:
    def __init__(self, dll):
        self.dll = dll
        self.repeat_mode = False

    def format_durasi(self, detik):
        return f"{detik // 60:02d}:{detik % 60:02d}"

    def tampilkan_playlist(self):
        print("\n=== DAFTAR PLAYLIST (TRAVERSAL DLL) ===")
        if self.dll.size == 0:
            print("[Playlist Masih Kosong]")
            return
        
        temp = self.dll.head
        idx = 1
        while temp:
            status = "-> " if temp == self.dll.current else "   "
            print(f"{status}{idx}. [{temp.id}] {temp.judul} - {temp.artis} ({self.format_durasi(temp.durasi)}) | Genre: {temp.genre}")
            temp = temp.next
            idx += 1
        print("=======================================")

    def menu_utama(self):
        if self.dll.current and not pygame.mixer.music.get_busy() and not AudioEngine.is_paused:
            AudioEngine.play(self.dll.current)

        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
                
            print("=============================================")
            print("         DYNAPLAY MUSIC PLAYER (CLI)         ")
            print("=============================================")
            
            if self.dll.current:
                curr = self.dll.current
                print(f" Sedang Memutar : {curr.judul} - {curr.artis}")
                print(f" File Audio     : music/{curr.id}")
                print(f" Status Musik   : {'DIPAUSE (JEDA)' if AudioEngine.is_paused else 'BERPUTAR (PLAYING)'}")
            else:
                print(" Sedang Memutar : Tidak Ada Lagu")
            
            print(f" Status Repeat  : {'AKTIF' if self.repeat_mode else 'MATI'}")
            print("=============================================")
            print(" 1. Lagu Berikutnya (Next)")
            print(" 2. Lagu Sebelumnya (Prev)")
            print(" 3. Pause / Resume Musik (Jeda)")
            print(" 4. Tambah Lagu (Input Bebas Otomatis .mp3)")
            print(" 5. Hapus Lagu (Delete via ID)")
            print(" 6. Lihat Seluruh Rantai Playlist")
            print(" 7. Aktifkan/Matikan Repeat")
            print(" 8. Pindah ke Mode GUI Premium (Spotify Mode)")
            print(" 9. Keluar Aplikasi")
            print("=============================================")
            
            pilihan = input("Pilih Menu (1-9): ").strip()
            
            if pilihan == "1":
                if self.dll.next_song(self.repeat_mode):
                    AudioEngine.play(self.dll.current)
                else:
                    print("\n[Pemberitahuan: Sudah mencapai ujung akhir playlist]")
                    input("Tekan Enter...")
            elif pilihan == "2":
                if self.dll.prev_song():
                    AudioEngine.play(self.dll.current)
                else:
                    print("\n[Pemberitahuan: Sudah mencapai ujung awal playlist]")
                    input("Tekan Enter...")
            elif pilihan == "3":
                if self.dll.current:
                    AudioEngine.toggle_pause()
                else:
                    print("\nTidak ada lagu aktif untuk di-pause.")
                    input("Tekan Enter...")
            elif pilihan == "4":
                print("\n--- Tambah Lagu ---")
                try:
                    posisi = int(input(f"Masukkan Posisi Sisip (1 - {self.dll.size + 1}): "))
                    song_id = input("Masukkan Nama File/ID (Bebas cth: 'shape'): ")
                    judul = input("Masukkan Judul Lagu: ")
                    artis = input("Masukkan Nama Artis: ")
                    durasi = int(input("Masukkan Durasi (dalam hitungan detik): "))
                    genre = input("Masukkan Genre: ")
                    
                    baru = Node(song_id, judul, artis, durasi, genre)
                    if self.dll.insert_at(posisi, baru):
                        DataManager.save_playlist(self.dll)
                        print(f"\n[Sukses] Lagu Berhasil Disisipkan dengan ID Sistem: {baru.id}!")
                        if self.dll.size == 1:
                            AudioEngine.play(self.dll.current)
                    else:
                        print("\n[Gagal] Batasan posisi di luar jangkauan!")
                except ValueError:
                    print("\n[Gagal] Posisi/Durasi harus diisi angka integer!")
                input("Tekan Enter...")
            elif pilihan == "5":
                print("\n--- Hapus Lagu ---")
                song_id = input("Masukkan ID Lagu yang ingin dibuang: ")
                current_before_delete = self.dll.current
                if self.dll.delete_by_id(song_id):
                    DataManager.save_playlist(self.dll)
                    print(f"\n[Sukses] Lagu {song_id} berhasil dihapus!")
                    if current_before_delete != self.dll.current:
                        AudioEngine.play(self.dll.current)
                else:
                    print("\n[Gagal] ID Lagu tidak ditemukan!")
                input("Tekan Enter...")
            elif pilihan == "6":
                self.tampilkan_playlist()
                input("\nTekan Enter untuk kembali ke menu...")
            elif pilihan == "7":
                self.repeat_mode = not self.repeat_mode
            elif pilihan == "8":
                print("\nBeralih ke mode GUI...")
                return "GUI"
            elif pilihan == "9":
                AudioEngine.stop()
                print("\nTerima kasih telah menggunakan DynaPlay!")
                sys.exit()
            else:
                print("\nPilihan menu salah!")
                input("Tekan Enter...")


# ==========================================
# 4. VIEW 2: GRAPHICAL USER INTERFACE (GUI)
# ==========================================

class PlaylistGUI:
    def __init__(self, root, dll):
        self.root = root
        self.dll = dll
        self.repeat_mode = False
        
        self.current_progress_seconds = 0
        self.anim_running = False
        self.after_id = None 

        self.root.title("Spotify Style - DynaPlay Premium")
        self.root.geometry("850x550")
        self.root.configure(bg="#121212")

        self.color_bg = "#121212"
        self.color_surface = "#181818"
        self.color_card = "#282828"
        self.color_spotify = "#1DB954"     
        self.color_text = "#FFFFFF"
        self.color_text_muted = "#AAAAAA"

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=self.color_surface, foreground=self.color_text, rowheight=32, fieldbackground=self.color_surface, borderwidth=0, font=("Helvetica", 10))
        style.configure("Treeview.Heading", background="#121212", foreground=self.color_text_muted, relief="flat", font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[('selected', '#333333')], foreground=[('selected', self.color_spotify)])
        style.configure("Spotify.Horizontal.TProgressbar", troughcolor='#404040', background=self.color_spotify, thickness=6)

        self.main_container = tk.Frame(root, bg=self.color_bg)
        self.main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # SISI KIRI PANEL CRUD
        self.left_frame = tk.LabelFrame(self.main_container, text=" Pointer Manipulations ", font=("Helvetica", 9, "bold"), bg=self.color_surface, fg=self.color_spotify, bd=1, relief="solid", padx=10, pady=10)
        self.left_frame.pack(side="left", fill="y", padx=(0, 10))

        tk.Button(self.left_frame, text="➕ Tambah Lagu (Insert)", font=("Helvetica", 9, "bold"), bg=self.color_spotify, fg="black", activebackground="#1aa34a", bd=0, relief="flat", cursor="hand2", padx=10, pady=6, width=22, command=self.popup_insert).pack(pady=10)
        tk.Button(self.left_frame, text="❌ Hapus Terpilih (Delete)", font=("Helvetica", 9, "bold"), bg="#E91429", fg="white", activebackground="#b1101e", bd=0, relief="flat", cursor="hand2", padx=10, pady=6, width=22, command=self.action_delete).pack(pady=5)
        tk.Button(self.left_frame, text="💻 Pindah ke Mode CLI", font=("Helvetica", 9, "bold"), bg="#282828", fg=self.color_text, activebackground="#404040", bd=0, relief="flat", cursor="hand2", padx=10, pady=6, width=22, command=self.switch_to_cli).pack(side="bottom", pady=10)

        # SISI KANAN TABEL PLAYLIST
        self.right_frame = tk.Frame(self.main_container, bg=self.color_bg)
        self.right_frame.pack(side="right", fill="both", expand=True)

        columns = ("id", "judul", "artis", "durasi", "genre")
        self.tree = ttk.Treeview(self.right_frame, columns=columns, show="headings")
        self.tree.heading("id", text="FILE AUDIO / ID")
        self.tree.heading("judul", text="JUDUL")
        self.tree.heading("artis", text="ARTIS")
        self.tree.heading("durasi", text="DURASI")
        self.tree.heading("genre", text="GENRE")
        
        self.tree.column("id", width=130, anchor="center")
        self.tree.column("judul", width=150)
        self.tree.column("artis", width=110)
        self.tree.column("durasi", width=70, anchor="center")
        self.tree.column("genre", width=90)
        self.tree.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(self.right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(fill="y", side="right")

        # BOTTOM PLAYER KONTROL BAR
        self.player_bar = tk.Frame(root, bg=self.color_surface, height=90, bd=0)
        self.player_bar.pack(fill="x", side="bottom")
        self.player_bar.pack_propagate(False)

        self.meta_frame = tk.Frame(self.player_bar, bg=self.color_surface)
        self.meta_frame.pack(side="left", fill="y", padx=20, pady=15)

        self.lbl_judul = tk.Label(self.meta_frame, text="Tidak Ada Lagu", font=("Helvetica", 12, "bold"), bg=self.color_surface, fg=self.color_text)
        self.lbl_judul.pack(anchor="w")
        self.lbl_detail = tk.Label(self.meta_frame, text="Artis: -", font=("Helvetica", 9), bg=self.color_surface, fg=self.color_text_muted)
        self.lbl_detail.pack(anchor="w")

        self.lbl_visualizer = tk.Label(self.player_bar, text="", font=("Helvetica", 14), bg=self.color_surface, fg=self.color_spotify)
        self.lbl_visualizer.pack(side="left", padx=15)

        self.center_control = tk.Frame(self.player_bar, bg=self.color_surface)
        self.center_control.pack(side="right", fill="both", expand=True, pady=10)

        self.buttons_row = tk.Frame(self.center_control, bg=self.color_surface)
        self.buttons_row.pack()

        self.btn_prev = tk.Button(self.buttons_row, text="⏮", font=("Helvetica", 14), bg=self.color_surface, fg=self.color_text_muted, activebackground=self.color_surface, activeforeground=self.color_text, bd=0, command=self.action_prev, cursor="hand2")
        self.btn_prev.pack(side="left", padx=15)

        # FITUR UTAMA BARU: Tombol Play/Pause Bulat Hijau Spotify
        self.btn_pause = tk.Button(self.buttons_row, text="⏸", font=("Helvetica", 14, "bold"), bg=self.color_text, fg="black", activebackground=self.color_spotify, activeforeground="black", bd=0, width=3, height=1, relief="flat", command=self.action_pause, cursor="hand2")
        self.btn_pause.pack(side="left", padx=15)

        self.btn_next = tk.Button(self.buttons_row, text="⏭", font=("Helvetica", 14), bg=self.color_surface, fg=self.color_text_muted, activebackground=self.color_surface, activeforeground=self.color_text, bd=0, command=self.action_next, cursor="hand2")
        self.btn_next.pack(side="left", padx=15)
        
        self.btn_repeat = tk.Button(self.buttons_row, text="🔁", font=("Helvetica", 12), bg=self.color_surface, fg=self.color_text_muted, activebackground=self.color_surface, activeforeground=self.color_spotify, bd=0, command=self.toggle_repeat, cursor="hand2")
        self.btn_repeat.pack(side="left", padx=15)

        # PROGRESS BAR TIMELINE
        self.progress_row = tk.Frame(self.center_control, bg=self.color_surface)
        self.progress_row.pack(fill="x", padx=40, pady=(5, 0))

        self.lbl_time_current = tk.Label(self.progress_row, text="00:00", font=("Helvetica", 8), bg=self.color_surface, fg=self.color_text_muted)
        self.lbl_time_current.pack(side="left", padx=5)

        self.progress_bar = ttk.Progressbar(self.progress_row, orient="horizontal", mode="determinate", style="Spotify.Horizontal.TProgressbar")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)

        self.lbl_time_max = tk.Label(self.progress_row, text="00:00", font=("Helvetica", 8), bg=self.color_surface, fg=self.color_text_muted)
        self.lbl_time_max.pack(side="right", padx=5)

        self.refresh_ui()
        if self.dll.current:
            AudioEngine.play(self.dll.current)
        self.start_animation_loop()

    def format_durasi(self, detik):
        return f"{detik // 60:02d}:{detik % 60:02d}"

    def refresh_ui(self):
        if self.dll.current:
            curr = self.dll.current
            self.lbl_judul.config(text=curr.judul)
            self.lbl_detail.config(text=f"{curr.artis} • {curr.genre}")
            self.lbl_time_max.config(text=self.format_durasi(curr.durasi))
            self.anim_running = not AudioEngine.is_paused
            
            # Ubah ikon tombol sesuai state putar/jeda
            if AudioEngine.is_paused:
                self.btn_pause.config(text="▶")
            else:
                self.btn_pause.config(text="⏸")
        else:
            self.lbl_judul.config(text="Tidak Ada Lagu")
            self.lbl_detail.config(text="Artis: -")
            self.lbl_time_max.config(text="00:00")
            self.progress_bar['value'] = 0
            self.lbl_time_current.config(text="00:00")
            self.anim_running = False
            self.btn_pause.config(text="▶")
            self.lbl_visualizer.config(text="")

        for row in self.tree.get_children():
            self.tree.delete(row)
            
        temp = self.dll.head
        while temp:
            tag = "playing" if temp == self.dll.current else "normal"
            self.tree.insert("", "end", values=(temp.id, temp.judul, temp.artis, self.format_durasi(temp.durasi), temp.genre), tags=(tag,))
            temp = temp.next
            
        self.tree.tag_configure("playing", background="#1DB954", foreground="black")
        self.tree.tag_configure("normal", background=self.color_surface, foreground=self.color_text)

    def action_next(self):
        if self.dll.next_song(self.repeat_mode):
            AudioEngine.play(self.dll.current)
        self.current_progress_seconds = 0
        self.refresh_ui()

    def action_prev(self):
        if self.dll.prev_song():
            AudioEngine.play(self.dll.current)
        self.current_progress_seconds = 0
        self.refresh_ui()

    def action_pause(self):
        """Aksi saat tombol Play/Pause ditekan di GUI"""
        if self.dll.current:
            state_paused = AudioEngine.toggle_pause()
            self.anim_running = not state_paused
            self.refresh_ui()

    def toggle_repeat(self):
        self.repeat_mode = not self.repeat_mode
        if self.repeat_mode:
            self.btn_repeat.config(fg=self.color_spotify)
        else:
            self.btn_repeat.config(fg=self.color_text_muted)

    def action_delete(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Peringatan", "Pilih baris lagu pada tabel terlebih dahulu!")
            return
        
        values = self.tree.item(selected_item, "values")
        song_id = values[0]
        
        current_before_delete = self.dll.current
        if self.dll.delete_by_id(song_id):
            DataManager.save_playlist(self.dll)
            messagebox.showinfo("Sukses", f"Lagu dengan ID {song_id} berhasil dihapus.")
            if current_before_delete != self.dll.current:
                AudioEngine.play(self.dll.current)
            self.current_progress_seconds = 0
            self.refresh_ui()

    def popup_insert(self):
        win = tk.Toplevel(self.root)
        win.title("Insert Node Baru")
        win.geometry("340x290")
        win.configure(bg=self.color_surface)
        win.resizable(False, False)
        
        labels = ["Posisi (1-Indexed):", "ID / Nama File (Bebas):", "Judul:", "Artis:", "Durasi (Detik):", "Genre:"]
        entries = []
        
        for i, text in enumerate(labels):
            tk.Label(win, text=text, bg=self.color_surface, fg=self.color_text_muted, font=("Helvetica", 9, "bold")).grid(row=i, column=0, padx=15, pady=6, sticky="e")
            ent = tk.Entry(win, bg=self.color_card, fg=self.color_text, insertbackground="white", bd=1, relief="solid", width=18)
            ent.grid(row=i, column=1, padx=5, pady=6)
            entries.append(ent)
            
        entries[0].insert(0, str(self.dll.size + 1))
        
        def simpan():
            try:
                pos = int(entries[0].get())
                song_id = entries[1].get().strip()
                if not song_id:
                    messagebox.showerror("Error", "ID lagu tidak boleh kosong!")
                    return
                
                # Inisialisasi node (pembersihan akhiran ganda dilakukan otomatis di konstruktor Node)
                node = Node(song_id, entries[2].get(), entries[3].get(), int(entries[4].get()), entries[5].get())
                if self.dll.insert_at(pos, node):
                    DataManager.save_playlist(self.dll)
                    if self.dll.size == 1:
                        AudioEngine.play(self.dll.current)
                    self.refresh_ui()
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Gagal menyisipkan data. Periksa nomor posisi!")
            except ValueError:
                messagebox.showerror("Error", "Input Posisi dan Durasi wajib diisi angka bulat!")
                
        tk.Button(win, text="Simpan ke DLL", font=("Helvetica", 10, "bold"), bg=self.color_spotify, fg="black", bd=0, relief="flat", cursor="hand2", padx=10, pady=5, command=simpan).grid(row=6, columnspan=2, pady=15)

    def start_animation_loop(self):
        """Looping jalannya hitungan detik progres musik dan animasi gelombang visualizer"""
        if self.anim_running and self.dll.current:
            total_durasi = self.dll.current.durasi
            self.current_progress_seconds += 1
            
            if self.current_progress_seconds > total_durasi:
                self.action_next()
            else:
                persentase = (self.current_progress_seconds / total_durasi) * 100
                self.progress_bar['value'] = persentase
                self.lbl_time_current.config(text=self.format_durasi(self.current_progress_seconds))

                # Efek animasi grafik equalizer bergerak naik turun acak
                bars = ["█ ▄ █ ▄ ▄", "▄ █ ▄ █ ▄", "█ █ ▄ ▄ █", "▄ ▄ █ █ ▄", "█ ▄ ▄ █ █"]
                self.lbl_visualizer.config(text=random.choice(bars))
        elif AudioEngine.is_paused:
            # Jika di-pause, animasi gelombang berhenti total tetapi progress bar bertahan
            self.lbl_visualizer.config(text="  ⏸ JEDA  ")
        else:
            self.progress_bar['value'] = 0
            self.lbl_time_current.config(text="00:00")
            self.lbl_visualizer.config(text="")
            self.current_progress_seconds = 0

        self.after_id = self.root.after(1000, self.start_animation_loop)

    def switch_to_cli(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        AudioEngine.stop()  
        self.root.destroy()


# ==========================================
# 5. MAIN PROGRAM LOOP (ORCHESTRATOR)
# ==========================================

def main():
    playlist_shared = DataManager.load_playlist()
    mode = "CLI" 
    
    while True:
        if mode == "CLI":
            cli = PlaylistCLI(playlist_shared)
            mode = cli.menu_utama() 
            
        elif mode == "GUI":
            root = tk.Tk()
            gui = PlaylistGUI(root, playlist_shared)
            root.mainloop()
            mode = "CLI"

if __name__ == "__main__":
    main()