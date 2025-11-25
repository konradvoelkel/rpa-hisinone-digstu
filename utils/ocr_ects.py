import os
import re
import glob
import platform
import time
import hashlib
import multiprocessing
from multiprocessing.pool import ThreadPool

try:
    from pdf2image import convert_from_path
    import pytesseract
except Exception:
    convert_from_path = None
    pytesseract = None

from utils.ocr_engine import extract_ects_ocr


NOTE_STRICT_RE = re.compile(r"\b([0-6][.,]\d{1,2})\b")


_FILE_HASH_CACHE = {}
_OCR_TEXT_CACHE = {}

_NUM_CPUS = max(1, multiprocessing.cpu_count() or 1)
_MAX_THREADS = max(1, int(_NUM_CPUS * 0.9))


def _compute_file_hash(pdf_path: str) -> str:

    h_cached = _FILE_HASH_CACHE.get(pdf_path)
    if h_cached:
        return h_cached

    h = hashlib.sha1()
    with open(pdf_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    digest = h.hexdigest()
    _FILE_HASH_CACHE[pdf_path] = digest
    return digest


def get_poppler_path():

    FALLBACK_PATHS = [
        r"C:\Users\spenl\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
    ]

    for path in FALLBACK_PATHS:
        if os.path.isdir(path):
            print(f"INFO: Poppler-Pfad über Hardcode-Fallback erkannt: {path}")
            return path

    if platform.system() == "Windows":
        poppler_dirs = glob.glob(r"C:\Program Files\poppler-*")
        if poppler_dirs:
            latest_poppler_dir = max(poppler_dirs, key=os.path.getctime)
            poppler_bin_path = os.path.join(latest_poppler_dir, "bin")
            if os.path.isdir(poppler_bin_path):
                print(
                    f"INFO: Poppler-Pfad automatisch erkannt: {poppler_bin_path}"
                )
                return poppler_bin_path
        print("WARNUNG: Poppler path not found")
        return None

    return None


POPPLER_PATH = get_poppler_path()


def ensure_ocr_available():
    if convert_from_path is None or pytesseract is None:
        raise RuntimeError(
            "OCR nicht verfuegbar (pdf2image/pytesseract fehlen).")
    return True


def _ocr_text_from_pdf_cached(pdf_path: str, dpi: int = 200, psm: int = 6) -> str:

    if convert_from_path is None or pytesseract is None:
        raise RuntimeError("OCR not found")

    file_hash = _compute_file_hash(pdf_path)
    cache_key = (file_hash, dpi, psm)
    if cache_key in _OCR_TEXT_CACHE:
        return _OCR_TEXT_CACHE[cache_key]

    print(f"start OCR for {pdf_path} (dpi={dpi}, psm={psm})")
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=POPPLER_PATH)

    config = f"--psm {psm}"

    def _ocr_page(img):
        try:
            return pytesseract.image_to_string(img, lang="deu+eng", config=config)
        except Exception as e:
            print(f"OCR-Fehler bei {pdf_path}: {e}")
            return ""

    with ThreadPool(min(len(images), _MAX_THREADS)) as pool:
        text_parts = pool.map(_ocr_page, images)

    full_text = "\n".join(text_parts)
    _OCR_TEXT_CACHE[cache_key] = full_text
    return full_text


def ocr_text_from_pdf(pdf_path, dpi=200):

    return _ocr_text_from_pdf_cached(pdf_path, dpi=dpi, psm=6)


def extract_ocr_note(text: str):

    if not text:
        print("error: extract_ocr_note() not found")
        return None

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    keywords = [
        "gesamtnote",
        "abschlussnote",
        "abschlusspruefung",
        "abschlussprüfung",
        "overall grade",
        "overall result",
        "overall mark",
        "final grade",
        "final result",
        "gesamturteil",
        "gesamtbewertung",
        "gesamtprädikat",
        "gesamtpraedikat",
        "gesamtleistung",
    ]

    for ln in lines:
        low = ln.lower()
        if not any(kw in low for kw in keywords):
            continue

        m = NOTE_STRICT_RE.search(ln)
        if m:
            try:
                val = float(m.group(1).replace(",", "."))
                print(
                    f"debug OCR-Note found in  '{ln[:80]}...' -> {val}"
                )
                return val
            except ValueError:
                continue

    print("erro :no grade with keys found")
    return None


def _infer_program_from_categories(categories):

    for c in categories:
        if str(c).strip().lower() == "mathematik":
            return "ai"
    return "bwl"


def extract_ects_hybrid(pdf_path, module_map, categories):

    if not os.path.exists(pdf_path):
        print(f"error: extract_ects_hybrid() not found: {pdf_path}")
        return {cat: 0.0 for cat in categories}, [], [], "ocr_hocr"

    print(
        f" Start OCR-ECTSfor {os.path.basename(pdf_path)}"
    )

    sums, matched_modules, unrecognized, method = extract_ects_ocr(
        pdf_path, module_map, categories
    )

    print(
        f"method={method}, sum ects={sum(sums.values())}"
    )
    return sums, matched_modules, unrecognized, method
