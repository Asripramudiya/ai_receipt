"""
database.py
Modul penyimpanan data hasil OCR struk belanja ke database SQLite.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "receipts.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT,
            nomor_dokumen TEXT,
            jenis_dokumen TEXT,
            tanggal_upload TEXT,
            status_validasi TEXT,
            total_belanja REAL,
            data_json TEXT,
            image_name TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_receipt(ocr_data: dict, validation_result: dict, image_name: str) -> int:
    """Simpan hasil OCR + validasi ke database. Return id record baru."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO receipts
            (nama, nomor_dokumen, jenis_dokumen, tanggal_upload, status_validasi, total_belanja, data_json, image_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ocr_data.get("nama_toko", ""),
            ocr_data.get("nomor_struk", ""),
            "Struk Belanja",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            validation_result.get("overall_status", "UNKNOWN"),
            ocr_data.get("total", 0),
            json.dumps(ocr_data, ensure_ascii=False),
            image_name,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_receipts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM receipts ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def delete_all_receipts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM receipts")
    conn.commit()
    conn.close()
