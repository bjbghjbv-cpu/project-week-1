# GazeCart — Proxy Buying Hands-Free

> **Program yang membantu penyandang disabilitas checkout barang berbasis website dan terintegrasi dengan AI (pelacakan mata).**  
> Dikendalikan sepenuhnya oleh **tatapan mata** — tatap produk, tutup mata 1,5 detik, pesan terkirim ke personal shopper.

---

## 🎯 Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Pelacakan Mata (Gaze Tracking)** | MediaPipe Face Mesh + Iris → kursor mengikuti pandangan |
| **Klik Tanpa Tangan** | Tutup mata **1,5 detik** dengan sengaja = klik (kedipan biasa diabaikan) |
| **Kalibrasi Cepat** | 2 detik lihat tengah layar → siap pakai |
| **Proxy Buying (Jastip)** | Produk impor dibeli personal shopper terverifikasi, dikirim ke rumah |
| **UI Aksesibel** | Desain kontras tinggi, font besar, navigasi keyboard/mata |
| **Keranjang & Checkout** | Kelola keranjang via mata, checkout menghasilkan nomor pesanan |

---

## 📦 Library / Dependensi

### Python (backend + computer vision)

| Package | Versi | Fungsi |
|---------|-------|--------|
| `opencv-contrib-python` | 4.10.0.84 | Akses webcam, gambar, GUI preview |
| `mediapipe` | 0.10.14 | Face Mesh + Iris landmark (pelacakan mata) |
| `pyautogui` | 0.9.54 | Kontrol kursor & klik sistem (cross-platform) |
| `fastapi` | 0.115.0 | Web server ringan (serve HTML frontend) |
| `uvicorn` | 0.30.6 | ASGI server untuk FastAPI |
| `numpy` | 1.26.4 | Operasi array (dependensi OpenCV/MediaPipe) |

> Semua tercantum di `requirements.txt`.

### Frontend (templates/index.html)

| Teknologi | Cara Load |
|-----------|-----------|
| **Tailwind CSS** | CDN (`https://cdn.tailwindcss.com`) |
| **Google Fonts (Plus Jakarta Sans)** | CDN |
| **Vanilla JS (ES6)** | Inline di `index.html` — tanpa build step, tanpa npm |

---

## 🖥️ Persyaratan Sistem

| Kebutuhan | Detail |
|-----------|--------|
| **OS** | Windows 10/11 (tested), Linux/macOS *harus* ubah `cv2.CAP_DSHOW` & DPI awareness |
| **Python** | 3.9 – 3.11 (direkomendasikan 3.11) |
| **Webcam** | Internal/eksternal, minimal 640×480 |
| **Layar** | Resolusi apa saja (kursor dipetakan ke `pyautogui.size()`) |
| **Internet** | Hanya saat pertama kali (download model MediaPipe + CDN Tailwind/Fonts) |

---

## ⚙️ Instalasi

```powershell
# 1. Clone repo (jika belum)
git clone https://github.com/bjbghjbv-cpu/project-week-1.git
cd project-week-1

# 2. Buat virtual environment (direkomendasikan)
python -m venv venv
venv\Scripts\activate

# 3. Pasang dependensi
pip install -r requirements.txt
```

> **Catatan Windows:** `opencv-contrib-python` & `mediapipe` butuh Visual C++ Redistributable. Jika error saat `pip install`, pasang [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) dulu.

---

## 🚀 Cara Menjalankan

```powershell
# Masuk folder project
cd C:\project1

# Aktifkan venv (jika pakai)
venv\Scripts\activate

# Jalankan aplikasi
python main.py
```

**Apa yang terjadi:**
1. FastAPI server start di `http://127.0.0.1:8000`
2. Browser terbuka otomatis ke halaman katalog
3. Jendela kamera **GazeCart Vision** muncul (kanan bawah)
4. **Kalibrasi otomatis 2 detik** — lihat lurus ke tengah layar, mata terbuka
5. Siap dipakai!

---

## 🎮 Kontrol & Navigasi

### Via Mata (Setelah Kalibrasi)

| Aksi | Cara |
|------|------|
| **Gerakkan kursor** | Lihat ke arah yang diinginkan (kursor mengikuti pandangan) |
| **Klik** | Tutup **kedua mata** selama **1,5 detik** (bilah progres di kamera) |
| **Kalibrasi ulang** | Tekan **C** pada jendela kamera → lihat tengah layar 2 detik |
| **Jeda / Lanjutkan** | Tekan **P** pada jendela kamera |
| **Sensitifitas** | Tekan **+** (naik) / **-** (turun) pada jendela kamera |
| **Keluar** | Tekan **Q** atau **ESC** pada jendela kamera / tutup jendela |

### Via Keyboard (Browser)

| Tombol | Fungsi |
|--------|--------|
| `Tab` / `Shift+Tab` | Navigasi elemen fokus |
| `Enter` / `Space` | Klik elemen fokus (Add to Cart, Checkout, dll) |
| `Escape` | Tutup panel keranjang |
| `F11` | Layar penuh (direkomendasikan) |

### Via Mouse/Touch (Fallback)

Semua tombol & kartu produk **bisa diklik normal** — aplikasi tetap berfungsi penuh tanpa pelacakan mata.

---

## 🗂️ Struktur Project

```
project-week-1/
├── main.py              # Entry point: FastAPI server + CV loop (MediaPipe + pyautogui)
├── requirements.txt     # Dependensi Python
├── .gitignore
├── templates/
│   └── index.html       # Frontend: katalog, keranjang, UI gaze-aware (Tailwind + vanilla JS)
├── images/              # Gambar produk (gerjorvan.jpg, anyai_peningg.jpg, dll)
└── venv/                # Virtual environment (tidak di-commit)
```

---

## 🖼️ Menambah Produk Baru

1. Taruh gambar produk di folder `images/` (contoh: `produk_baru.jpg`)
2. Edit `templates/index.html`:
   - Tambah entri di objek `PRODUCTS` (baris ~364):
     ```js
     const PRODUCTS = {
       'gerjorvan': { name: 'gerjorvan', price: 1250000, img: 'gerjorvan.jpg' },
       'anyai-peningg': { name: 'anyai peningg', price: 980000, img: 'anyai_peningg.jpg' },
       'produk-baru': { name: 'Nama Produk', price: 500000, img: 'produk_baru.jpg' }, // ← tambah
     };
     ```
   - Duplikasikan blok `<article data-product="...">` di section `#katalog` (baris 242–295), ganti `data-product`, gambar, nama, harga, deskripsi.
3. Selesai — refresh browser.

---

## ⚙️ Konfigurasi Lanjutan (main.py)

Semua parameter utama ada di **bagian atas `main.py` (baris 19–53)**:

| Variabel | Default | Kegunaan |
|----------|---------|----------|
| `CAMERA_INDEX` | `0` | Indeks webcam (coba `1` jika kamera utama tidak kebaca) |
| `FRAME_W`, `FRAME_H` | `640`, `480` | Resolusi capture (lebih tinggi = lebih akurat tapi lebih berat) |
| `RANGE_X`, `RANGE_Y` | `0.10`, `0.07` | Rentang gerak kepala→kursor (lebih kecil = lebih sensitif) |
| `IRIS_WEIGHT` | `2.0` | Bobot iris vs hidung untuk titik fokus |
| `SMOOTHING` | `0.25` | Penghalusan gerak kursor (0.1 halus–0.6 cepat) |
| `EAR_RATIO` | `0.70` | Ambang klik: mata tertutup jika EAR < `baseline * 0.70` |
| `CLICK_HOLD_SECONDS` | `1.0` | Durasi tutup mata untuk klik (detik) |
| `CALIBRATION_SECONDS` | `2.0` | Durasi kalibrasi awal (detik) |

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| **`cv2.VideoCapture` gagal / kamera tidak kebuka** | Tutup aplikasi lain yang pakai kamera (Zoom, Teams, Browser). Coba ubah `CAMERA_INDEX = 1` di `main.py`. |
| **`ImportError: DLL load failed` (MediaPipe/OpenCV)** | Pasang [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe). Pastikan Python 64-bit. |
| **Kursor melompat-lompat / tidak akurat** | Tekan **C** untuk kalibrasi ulang. Pastikan pencahayaan cukup, wajah terlihat jelas. Atur `SMOOTHING` naik (0.3–0.4). |
| **Klik terlalu sensitif / tidak klik** | Atur `EAR_RATIO` (naik = butuh tutup mata lebih lama/tutup lebih rapat). Atur `CLICK_HOLD_SECONDS`. |
| **Browser tidak terbuka otomatis** | Buka manual `http://127.0.0.1:8000`. Pastikan port 8000 tidak dipakai. |
| **Gambar produk tidak muncul** | Pastikan file `.jpg` ada di folder `images/` dan nama cocok dengan `PRODUCTS[id].img`. |
| **Linux/macOS: error `CAP_DSHOW` / DPI awareness** | Hapus/ubah baris 57–64 & 145 (`cv2.CAP_DSHOW` → `0` atau `cv2.CAP_V4L2`). Hapus `ctypes.windll` block. |

---


---

## 📄 Lisensi

MIT License — bebas gunakan, modifikasi, distribusi.

---

## 🙏 Acknowledgments

- **MediaPipe** (Google) — Face Mesh & Iris tracking
- **OpenCV** — Computer vision backbone
- **FastAPI + Uvicorn** — Web server modern & cepat
- **Tailwind CSS + Plus Jakarta Sans** — UI modern tanpa build step
- **pyautogui** — Kontrol OS cross-platform

---

> **GazeCart** — Belanja impor, cukup dengan tatapan. 👁️✨
