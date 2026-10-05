import ctypes
import math
import sys
import threading
import time
import webbrowser
from pathlib import Path
from statistics import median
from fastapi.staticfiles import StaticFiles

import cv2
import mediapipe as mp
import pyautogui
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

# ============================================================
# KONFIGURASI (ubah angka di sini untuk menyetel kenyamanan)
# ============================================================
HOST = "127.0.0.1"
PORT = 8000

CAMERA_INDEX = 0
FRAME_W = 640
FRAME_H = 480

# Setengah rentang gerak kepala/mata (satuan: fraksi lebar/tinggi frame kamera)
# dari titik tengah ke tepi layar. Makin kecil = kursor makin sensitif.
RANGE_X = 0.10
RANGE_Y = 0.07

# Bobot kontribusi posisi iris terhadap titik fokus (hidung + iris)
IRIS_WEIGHT = 2.0

# Penghalusan gerak kursor (0.1 = sangat halus tapi lambat, 0.6 = cepat tapi bergetar)
SMOOTHING = 0.25
DEADZONE_PX = 4
SCREEN_MARGIN = 2

# Logika klik: mata dianggap tertutup jika EAR < baseline * EAR_RATIO
EAR_RATIO = 0.70
CLICK_HOLD_SECONDS = 1

# Iris hanya dibaca ketika mata cukup terbuka agar tidak melompat saat berkedip
IRIS_VALID_RATIO = 0.85

CALIBRATION_SECONDS = 2.0

WINDOW_NAME = "GazeCart Vision"
PREVIEW_W = 280
PREVIEW_H = 210

# ============================================================
# INISIALISASI SISTEM
# ============================================================
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "templates" / "index.html"

# Indeks landmark MediaPipe Face Mesh
LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
NOSE_TIP = 1
# (pusat iris, sudut mata luar, sudut mata dalam)
LEFT_IRIS = (468, 33, 133)
RIGHT_IRIS = (473, 362, 263)

# ============================================================
# SERVER FASTAPI (hanya menyajikan file HTML)
# ============================================================
app = FastAPI(title="GazeCart")


@app.get("/")
def home():
    return FileResponse(INDEX_FILE, media_type="text/html")


app.mount("/", StaticFiles(directory=BASE_DIR / "images"), name="images")


def start_server():
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_at = time.time()
    while not server.started and time.time() - started_at < 10:
        time.sleep(0.1)
    return server


# ============================================================
# FUNGSI BANTU COMPUTER VISION
# ============================================================
def eye_aspect_ratio(lm, idx, w, h):
    p1, p2, p3, p4, p5, p6 = [(lm[i].x * w, lm[i].y * h) for i in idx]
    vertical = math.dist(p2, p6) + math.dist(p3, p5)
    horizontal = 2.0 * math.dist(p1, p4)
    if horizontal == 0:
        return 0.0
    return vertical / horizontal


def iris_offset(lm):
    total_x = 0.0
    total_y = 0.0
    for iris, a, b in (LEFT_IRIS, RIGHT_IRIS):
        center_x = (lm[a].x + lm[b].x) / 2.0
        center_y = (lm[a].y + lm[b].y) / 2.0
        total_x += lm[iris].x - center_x
        total_y += lm[iris].y - center_y
    return total_x / 2.0, total_y / 2.0


def clamp01(value):
    return min(max(value, 0.0), 1.0)


def draw_text(frame, text, pos, scale=0.5, color=(255, 255, 255), thickness=1):
    cv2.putText(frame, text, (pos[0] + 1, pos[1] + 1), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


# ============================================================
# LOOP UTAMA COMPUTER VISION
# ============================================================
def run_vision(server):
    screen_w, screen_h = pyautogui.size()

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("GAGAL: webcam tidak dapat dibuka. Tutup aplikasi lain yang memakai kamera,")
        print("atau ubah CAMERA_INDEX di main.py (coba 1).")
        server.should_exit = True
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, PREVIEW_W, PREVIEW_H)
    cv2.moveWindow(WINDOW_NAME, screen_w - PREVIEW_W - 20, screen_h - PREVIEW_H - 90)
    try:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    except Exception:
        pass

    calibrating = True
    calib_end = time.time() + CALIBRATION_SECONDS
    calib_feats = []
    calib_ears = []
    center = (0.5, 0.5)
    ear_baseline = 0.30
    ear_threshold = ear_baseline * EAR_RATIO

    sens = 1.0
    paused = False
    smooth = None
    iris_off = (0.0, 0.0)
    closed_since = None
    click_fired = False
    flash_until = 0.0
    last_face_time = time.time()

    print("Kalibrasi dimulai: lihat lurus ke tengah layar dengan mata terbuka.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            result = face_mesh.process(rgb)
            now = time.time()

            status = "Wajah tidak terdeteksi"
            progress = 0.0

            if result.multi_face_landmarks:
                last_face_time = now
                lm = result.multi_face_landmarks[0].landmark
                ear = (eye_aspect_ratio(lm, LEFT_EYE, w, h) +
                       eye_aspect_ratio(lm, RIGHT_EYE, w, h)) / 2.0
                nose = lm[NOSE_TIP]
                cv2.circle(frame, (int(nose.x * w), int(nose.y * h)), 4, (0, 255, 0), -1)

                if calibrating:
                    off = iris_offset(lm)
                    calib_feats.append((nose.x + IRIS_WEIGHT * off[0],
                                        nose.y + IRIS_WEIGHT * off[1]))
                    calib_ears.append(ear)
                    remaining = max(0.0, calib_end - now)
                    status = "KALIBRASI: lihat lurus (%.1f dtk)" % remaining
                    if now >= calib_end:
                        if len(calib_feats) >= 15:
                            center = (median([f[0] for f in calib_feats]),
                                      median([f[1] for f in calib_feats]))
                            ear_baseline = median(calib_ears)
                            ear_threshold = ear_baseline * EAR_RATIO
                            calibrating = False
                            smooth = None
                            print("Kalibrasi selesai. Baseline EAR = %.3f, ambang = %.3f"
                                  % (ear_baseline, ear_threshold))
                        else:
                            calib_feats = []
                            calib_ears = []
                            calib_end = now + CALIBRATION_SECONDS
                else:
                    if closed_since is None:
                        closed = ear < ear_threshold
                    else:
                        closed = ear < ear_threshold * 1.15

                    if closed:
                        # Kursor dibekukan agar klik tepat sasaran
                        if closed_since is None:
                            closed_since = now
                        elapsed = now - closed_since
                        progress = min(elapsed / CLICK_HOLD_SECONDS, 1.0)
                        status = "Mata tertutup: tahan untuk klik"
                        if elapsed >= CLICK_HOLD_SECONDS and not click_fired and not paused:
                            pyautogui.click()
                            click_fired = True
                            flash_until = now + 0.6
                    else:
                        closed_since = None
                        click_fired = False

                        if ear >= ear_baseline * IRIS_VALID_RATIO:
                            iris_off = iris_offset(lm)

                        fx = nose.x + IRIS_WEIGHT * iris_off[0]
                        fy = nose.y + IRIS_WEIGHT * iris_off[1]

                        nx = clamp01(0.5 + (fx - center[0]) / (2.0 * RANGE_X / sens))
                        ny = clamp01(0.5 + (fy - center[1]) / (2.0 * RANGE_Y / sens))
                        target_x = SCREEN_MARGIN + nx * (screen_w - 1 - 2 * SCREEN_MARGIN)
                        target_y = SCREEN_MARGIN + ny * (screen_h - 1 - 2 * SCREEN_MARGIN)

                        if smooth is None:
                            smooth = (target_x, target_y)
                        else:
                            dx = target_x - smooth[0]
                            dy = target_y - smooth[1]
                            dist = math.hypot(dx, dy)
                            if dist > DEADZONE_PX:
                                alpha = min(0.7, SMOOTHING + dist / 1500.0)
                                smooth = (smooth[0] + alpha * dx, smooth[1] + alpha * dy)

                        if paused:
                            status = "DIJEDA (tekan P untuk lanjut)"
                        else:
                            pyautogui.moveTo(int(smooth[0]), int(smooth[1]), _pause=False)
                            status = "Kursor aktif | EAR %.2f" % ear
            else:
                if now - last_face_time > 0.5:
                    closed_since = None
                    click_fired = False

            # ---------- Tampilan pratinjau ----------
            draw_text(frame, status, (8, 20), 0.5, (0, 255, 255), 1)
            draw_text(frame, "Sens x%.1f | C kalibrasi | P jeda | Q keluar" % sens,
                      (8, h - 8), 0.42, (255, 255, 255), 1)
            if progress > 0:
                cv2.rectangle(frame, (8, h - 40), (208, h - 22), (255, 255, 255), 1)
                cv2.rectangle(frame, (8, h - 40), (8 + int(200 * progress), h - 22),
                              (0, 200, 255), -1)
            if now < flash_until:
                draw_text(frame, "KLIK!", (w // 2 - 70, h // 2), 2.0, (0, 255, 0), 4)

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                break
            elif key == ord("c"):
                calibrating = True
                calib_feats = []
                calib_ears = []
                calib_end = time.time() + CALIBRATION_SECONDS
                closed_since = None
                click_fired = False
                print("Kalibrasi ulang: lihat lurus ke tengah layar.")
            elif key == ord("p"):
                paused = not paused
            elif key in (ord("="), ord("+")):
                sens = min(sens * 1.1, 4.0)
            elif key in (ord("-"), ord("_")):
                sens = max(sens / 1.1, 0.4)

            try:
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break
    finally:
        cap.release()
        face_mesh.close()
        cv2.destroyAllWindows()
        server.should_exit = True


def main():
    if not INDEX_FILE.exists():
        print("File tidak ditemukan: %s" % INDEX_FILE)
        print("Pastikan templates/index.html ada di folder yang sama dengan main.py.")
        return

    server = start_server()
    url = "http://%s:%d" % (HOST, PORT)
    webbrowser.open(url)
    print("GazeCart berjalan di %s" % url)
    print("Tekan F11 di browser untuk layar penuh, lalu kalibrasi dengan menekan C pada jendela kamera.")

    try:
        run_vision(server)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        time.sleep(0.3)


if __name__ == "__main__":
    main()