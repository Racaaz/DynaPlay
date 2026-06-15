import tkinter as tk
from tkinter import messagebox, ttk
import random

class Lagu:
    """Struktur Node dengan atribut lengkap (Sub-CPMK 3.1)"""
    def __init__(self, judul: str, artis: str, durasi: str, genre: str):
        self.judul = judul
        self.artis = artis
        self.durasi = durasi
        self.genre = genre
        self.next = None
        self.prev = None

class PlaylistDynaPlay:
    def __init__(self):
        self.head = None
        self.tail = None
        self.lagu_sekarang = None
        self.is_repeat = False

    def insert_tail(self, judul, artis, durasi, genre):
        baru = Lagu(judul, artis, durasi, genre)
        if not self.head:
            self.head = self.tail = self.lagu_sekarang = baru
        else:
            self.tail.next = baru
            baru.prev = self.tail
            self.tail = baru

    def insert_head(self, judul, artis, durasi, genre):
        baru = Lagu(judul, artis, durasi, genre)
        if not self.head:
            self.head = self.tail = self.lagu_sekarang = baru
        else:
            baru.next = self.head
            self.head.prev = baru
            self.head = baru

    def insert_di_posisi(self, posisi: int, judul, artis, durasi, genre):
        if posisi <= 1 or not self.head:
            self.insert_head(judul, artis, durasi, genre)
            return

        baru = Lagu(judul, artis, durasi, genre)
        bantu = self.head
        hitung = 1

        while hitung < posisi - 1 and bantu.next is not None:
            bantu = bantu.next
            hitung += 1

        if bantu.next is None:
            self.insert_tail(judul, artis, durasi, genre)
        else:
            baru.next = bantu.next
            baru.prev = bantu
            bantu.next.prev = baru
            bantu.next = baru

    def delete_lagu(self, judul: str):
        if not self.head:
            return False

        bantu = self.head
        ketemu = False

        while bantu:
            if bantu.judul.lower() == judul.lower():
                ketemu = True
                break
            bantu = bantu.next

        if not ketemu:
            return False

        if bantu == self.lagu_sekarang:
            if self.lagu_sekarang.next:
                self.lagu_sekarang = self.lagu_sekarang.next
            elif self.lagu_sekarang.prev:
                self.lagu_sekarang = self.lagu_sekarang.prev
            else:
                self.lagu_sekarang = None

        if bantu == self.head and bantu == self.tail:
            self.head = self.tail = None
        elif bantu == self.head:
            self.head = self.head.next
            self.head.prev = None
        elif bantu == self.tail:
            self.tail = self.tail.prev
            self.tail.next = None
        else:
            bantu.prev.next = bantu.next
            bantu.next.prev = bantu.prev

        del bantu
        return True

    def shuffle_playlist(self):
        if not self.head or self.head == self.tail:
            return False
        
        node_list = []
        bantu = self.head
        while bantu:
            node_list.append(bantu)
            bantu = bantu.next

        random.shuffle(node_list)

        self.head = node_list[0]
        self.head.prev = None

        for i in range(len(node_list) - 1):
            node_list[i].next = node_list[i+1]
            node_list[i+1].prev = node_list[i]

        self.tail = node_list[-1]
        self.tail.next = None
        self.lagu_sekarang = self.head
        return True


class DynaPlayGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DynaPlay - Pemutar Musik Doubly Linked List")
        self.root.geometry("700x550")
        self.root.configure(bg="#1E1E24")
        
        self.playlist = PlaylistDynaPlay()
        
        # Tambah Dummy Data Awal
        self.playlist.insert_tail("Bohemian Rhapsody", "Queen", "05:55", "Rock")
        self.playlist.insert_tail("Hati-Hati di Jalan", "Tulus", "04:02", "Pop")
        self.playlist.insert_tail("As It Was", "Harry Styles", "02:47", "Synth-Pop")
        
        self.buat_widget()
        self.update_tampilan()

    def buat_widget(self):
        # 1. PANEL UTAMA (NOW PLAYING)
        frame_now_playing = tk.LabelFrame(self.root, text=" Now Playing ", fg="#FFF", bg="#2A2D34", font=("Arial", 10, "bold"))
        frame_now_playing.pack(fill="x", padx=15, pady=15)
        
        self.lbl_judul = tk.Label(frame_now_playing, text="Judul: -", font=("Arial", 14, "bold"), fg="#1DB954", bg="#2A2D34")
        self.lbl_judul.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_artis = tk.Label(frame_now_playing, text="Artis: -", font=("Arial", 11), fg="#DDD", bg="#2A2D34")
        self.lbl_artis.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_info = tk.Label(frame_now_playing, text="Genre: - | Durasi: -", font=("Arial", 9, "italic"), fg="#AAA", bg="#2A2D34")
        self.lbl_info.pack(anchor="w", padx=10, pady=5)

        # 2. PANEL NAVIGASI UTAMA
        frame_nav = tk.Frame(self.root, bg="#1E1E24")
        frame_nav.pack(pady=10)
        
        btn_prev = tk.Button(frame_nav, text="⏮ Prev", width=10, font=("Arial", 10, "bold"), command=self.aksi_prev, bg="#4A4E69", fg="#FFF")
        btn_prev.grid(row=0, column=0, padx=5)
        
        btn_next = tk.Button(frame_nav, text="Next ⏭", width=10, font=("Arial", 10, "bold"), command=self.aksi_next, bg="#4A4E69", fg="#FFF")
        btn_next.grid(row=0, column=1, padx=5)
        
        self.btn_repeat = tk.Button(frame_nav, text="🔁 Repeat: OFF", width=14, font=("Arial", 10), command=self.aksi_repeat, bg="#222222", fg="#FFF")
        self.btn_repeat.grid(row=0, column=2, padx=5)
        
        btn_shuffle = tk.Button(frame_nav, text="🔀 Shuffle", width=10, font=("Arial", 10), command=self.aksi_shuffle, bg="#222222", fg="#FFF")
        btn_shuffle.grid(row=0, column=3, padx=5)

        # 3. LISTBOX PLAYLIST & PANEL CONTROL TAMBAH/HAPUS
        frame_konten = tk.Frame(self.root, bg="#1E1E24")
        frame_konten.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Kiri: Daftar Lagu
        frame_list = tk.LabelFrame(frame_konten, text=" Daftar Lagu ", fg="#FFF", bg="#1E1E24")
        frame_list.pack(side="left", fill="both", expand=True, padx=(0,10))
        
        self.listbox = tk.Listbox(frame_list, bg="#2A2D34", fg="#FFF", selectbackground="#1DB954", font=("Courier", 10))
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Kanan: Form input Manajemen Node
        frame_form = tk.LabelFrame(frame_konten, text=" Kelola Lagu ", fg="#FFF", bg="#1E1E24")
        frame_form.pack(side="right", fill="y")
        
        tk.Label(frame_form, text="Judul:", fg="#FFF", bg="#1E1E24").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.ent_judul = tk.Entry(frame_form, width=20); self.ent_judul.grid(row=0, column=1, padx=5, pady=2)
        
        tk.Label(frame_form, text="Artis:", fg="#FFF", bg="#1E1E24").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.ent_artis = tk.Entry(frame_form, width=20); self.ent_artis.grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(frame_form, text="Durasi:", fg="#FFF", bg="#1E1E24").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.ent_durasi = tk.Entry(frame_form, width=20); self.ent_durasi.grid(row=2, column=1, padx=5, pady=2)
        
        tk.Label(frame_form, text="Genre:", fg="#FFF", bg="#1E1E24").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.ent_genre = tk.Entry(frame_form, width=20); self.ent_genre.grid(row=3, column=1, padx=5, pady=2)
        
        tk.Label(frame_form, text="Posisi (Sisip):", fg="#FFF", bg="#1E1E24").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.ent_posisi = tk.Entry(frame_form, width=20); self.ent_posisi.grid(row=4, column=1, padx=5, pady=2)

        # Tombol Aksi Operasi DLL
        tk.Button(frame_form, text="➕ Tambah Akhir", command=self.aksi_add_tail, bg="#1DB954", fg="#FFF", width=18).grid(row=5, column=0, columnspan=2, pady=3)
        tk.Button(frame_form, text="➕ Tambah Awal", command=self.aksi_add_head, bg="#1DB954", fg="#FFF", width=18).grid(row=6, column=0, columnspan=2, pady=3)
        tk.Button(frame_form, text="🔀 Sisipkan Posisi", command=self.aksi_add_posisi, bg="#1DB954", fg="#FFF", width=18).grid(row=7, column=0, columnspan=2, pady=3)
        
        tk.Button(frame_form, text="🗑 Hapus via Judul", command=self.aksi_hapus, bg="#D90429", fg="#FFF", width=18).grid(row=8, column=0, columnspan=2, pady=10)

    # ==========================================
    # FUNGSI INTERAKSI LOGIKA & UI
    # ==========================================
    def update_tampilan(self):
        # 1. Update teks panel Now Playing
        curr = self.playlist.lagu_sekarang
        if curr:
            self.lbl_judul.config(text=f"Judul: {curr.judul}")
            self.lbl_artis.config(text=f"Artis: {curr.artis}")
            self.lbl_info.config(text=f"Genre: {curr.genre}  |  Durasi: {curr.durasi}")
        else:
            self.lbl_judul.config(text="Judul: -")
            self.lbl_artis.config(text="Artis: -")
            self.lbl_info.config(text="Genre: -  |  Durasi: -")

        # 2. Update Isian Listbox Playlist
        self.listbox.delete(0, tk.END)
        bantu = self.playlist.head
        no = 1
        while bantu:
            status = "▶ " if bantu == curr else "  "
            self.listbox.insert(tk.END, f"{status}{no:02d}. {bantu.judul} - {bantu.artis} ({bantu.durasi})")
            bantu = bantu.next
            no += 1

    def ambil_input_form(self):
        j = self.ent_judul.get()
        a = self.ent_artis.get()
        d = self.ent_durasi.get() if self.ent_durasi.get() else "03:00"
        g = self.ent_genre.get() if self.ent_genre.get() else "Pop"
        
        if not j or not a:
            messagebox.showwarning("Peringatan", "Judul dan Artis wajib diisi!")
            return None
        return j, a, d, g

    def bersihkan_form(self):
        self.ent_judul.delete(0, tk.END)
        self.ent_artis.delete(0, tk.END)
        self.ent_durasi.delete(0, tk.END)
        self.ent_genre.delete(0, tk.END)
        self.ent_posisi.delete(0, tk.END)

    # ==========================================
    # EVENT HANDLER / COMMAND BUTTONS
    # ==========================================
    def aksi_next(self):
        if self.playlist.lagu_sekarang:
            if self.playlist.lagu_sekarang.next:
                self.playlist.lagu_sekarang = self.playlist.lagu_sekarang.next
            elif self.playlist.is_repeat:
                self.playlist.lagu_sekarang = self.playlist.head
            else:
                messagebox.showinfo("DynaPlay", "Sudah mencapai lagu terakhir.")
            self.update_tampilan()

    def aksi_prev(self):
        if self.playlist.lagu_sekarang:
            if self.playlist.lagu_sekarang.prev:
                self.playlist.lagu_sekarang = self.playlist.lagu_sekarang.prev
            elif self.playlist.is_repeat:
                self.playlist.lagu_sekarang = self.playlist.tail
            else:
                messagebox.showinfo("DynaPlay", "Anda berada di lagu pertama.")
            self.update_tampilan()

    def aksi_repeat(self):
        self.playlist.is_repeat = not self.playlist.is_repeat
        if self.playlist.is_repeat:
            self.btn_repeat.config(text="🔁 Repeat: ON", bg="#1DB954")
        else:
            self.btn_repeat.config(text="🔁 Repeat: OFF", bg="#222222")

    def aksi_shuffle(self):
        berhasil = self.playlist.shuffle_playlist()
        if berhasil:
            self.update_tampilan()
            messagebox.showinfo("Sukses", "Playlist berhasil diacak!")
        else:
            messagebox.showwarning("Gagal", "Minimal harus ada 2 lagu untuk melakukan shuffle.")

    def aksi_add_tail(self):
        data = self.ambil_input_form()
        if data:
            self.playlist.insert_tail(*data)
            self.bersihkan_form()
            self.update_tampilan()

    def aksi_add_head(self):
        data = self.ambil_input_form()
        if data:
            self.playlist.insert_head(*data)
            self.bersihkan_form()
            self.update_tampilan()

    def aksi_add_posisi(self):
        data = self.ambil_input_form()
        if data:
            try:
                pos = int(self.ent_posisi.get())
                self.playlist.insert_di_posisi(pos, *data)
                self.bersihkan_form()
                self.update_tampilan()
            except ValueError:
                messagebox.showerror("Error", "Kolom Posisi harus berupa angka integer!")

    def aksi_hapus(self):
        judul = self.ent_judul.get()
        if not judul:
            messagebox.showwarning("Peringatan", "Masukkan Judul lagu pada form untuk menghapus!")
            return
            
        sukses = self.playlist.delete_lagu(judul)
        if sukses:
            messagebox.showinfo("Sukses", f"Lagu '{judul}' berhasil dihapus.")
            self.bersihkan_form()
            self.update_tampilan()
        else:
            messagebox.showerror("Gagal", f"Lagu '{judul}' tidak ditemukan.")

if __name__ == "__main__":
    root = tk.Tk()
    app = DynaPlayGUI(root)
    root.mainloop()