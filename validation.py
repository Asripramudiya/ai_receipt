"""
validation.py
Business Rule Validation untuk hasil OCR Struk Belanja (Receipt).

PENTING: Validasi di sini murni logika Python (bukan AI, bukan regex untuk
membaca teks dokumen -- regex di sini hanya dipakai untuk mengecek FORMAT
angka/tanggal hasil ekstraksi AI, sesuai ketentuan project).
"""

import re
from datetime import datetime


def _to_float(value):
    """Konversi string/angka hasil OCR ke float, aman terhadap format 'Rp 12.000'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    s = re.sub(r"[^\d,.-]", "", s)  # buang 'Rp', spasi, dll
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") > 1 else s
    try:
        return float(s.replace(",", ""))
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def validate_nama_toko(data: dict) -> tuple[bool, str]:
    nama = (data.get("nama_toko") or "").strip()
    if len(nama) < 2:
        return False, "Nama toko tidak ditemukan / terlalu pendek"
    return True, "Nama toko valid"


def validate_tanggal(data: dict) -> tuple[bool, str]:
    tgl = (data.get("tanggal_transaksi") or "").strip()
    if not tgl:
        return False, "Tanggal transaksi kosong"

    formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d",
        "%d %B %Y", "%d %b %Y", "%d-%m-%y", "%d/%m/%y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(tgl, fmt)
            if parsed.year < 2000 or parsed > datetime.now():
                return False, f"Tanggal tidak masuk akal: {tgl}"
            return True, "Format tanggal valid"
        except ValueError:
            continue
    return False, f"Format tanggal tidak dikenali: {tgl}"


def validate_items(data: dict) -> tuple[bool, str]:
    items = data.get("items") or []
    if not isinstance(items, list) or len(items) == 0:
        return False, "Tidak ada item belanja terdeteksi"

    for idx, item in enumerate(items, start=1):
        qty = _to_float(item.get("qty"))
        harga = _to_float(item.get("harga_satuan"))
        subtotal = _to_float(item.get("subtotal"))

        if qty is None or qty <= 0:
            return False, f"Item #{idx}: qty tidak valid"
        if harga is None or harga < 0:
            return False, f"Item #{idx}: harga_satuan tidak valid"
        if subtotal is not None and harga is not None and qty is not None:
            expected = round(qty * harga, 0)
            if abs(expected - round(subtotal, 0)) > max(50, expected * 0.02):
                return False, f"Item #{idx}: subtotal ({subtotal}) tidak sesuai qty x harga ({expected})"
    return True, "Semua item valid"


def validate_total(data: dict) -> tuple[bool, str]:
    subtotal = _to_float(data.get("subtotal"))
    pajak = _to_float(data.get("pajak")) or 0
    diskon = _to_float(data.get("diskon")) or 0
    total = _to_float(data.get("total"))

    if total is None or total <= 0:
        return False, "Total belanja tidak valid / tidak ditemukan"

    if subtotal is not None:
        expected_total = subtotal + pajak - diskon
        # toleransi pembulatan 2% atau minimal 100
        tolerance = max(100, expected_total * 0.02)
        if abs(expected_total - total) > tolerance:
            return False, (
                f"Total tidak konsisten: subtotal({subtotal}) + pajak({pajak}) "
                f"- diskon({diskon}) = {expected_total}, tapi total tertulis {total}"
            )
    return True, "Total valid dan konsisten"


def validate_nomor_struk(data: dict) -> tuple[bool, str]:
    nomor = (data.get("nomor_struk") or "").strip()
    if not nomor:
        # nomor struk tidak selalu wajib ada di semua struk, jadi hanya warning ringan
        return True, "Nomor struk kosong (opsional, tidak menggugurkan validasi)"
    return True, "Nomor struk ditemukan"


def run_business_rules(data: dict) -> dict:
    """
    Menjalankan seluruh business rule untuk data hasil OCR struk belanja.
    Mengembalikan dict berisi status per-field dan status keseluruhan.
    """
    checks = {
        "nama_toko": validate_nama_toko(data),
        "tanggal_transaksi": validate_tanggal(data),
        "items": validate_items(data),
        "total": validate_total(data),
        "nomor_struk": validate_nomor_struk(data),
    }

    results = {}
    overall_valid = True
    for field, (is_valid, message) in checks.items():
        results[field] = {
            "status": "VALID" if is_valid else "INVALID",
            "message": message,
        }
        if not is_valid:
            overall_valid = False

    results["overall_status"] = "VALID" if overall_valid else "INVALID"
    return results
