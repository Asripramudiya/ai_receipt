"""
ai_client.py
Wrapper untuk memanggil OpenRouter Vision API (AI Vision) untuk:
1. Klasifikasi gambar (apakah struk belanja atau bukan)
2. OCR / ekstraksi data dari struk belanja dalam format JSON

Tidak ada penggunaan Regex untuk membaca isi dokumen -- seluruh pembacaan
teks/angka dilakukan oleh model AI Vision melalui OpenRouter.
"""

import base64
import json
import os
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model vision default. Bisa diganti lewat environment variable OPENROUTER_MODEL.
# Contoh model vision yang tersedia di OpenRouter: "openai/gpt-4o-mini",
# "google/gemini-2.0-flash-001", "anthropic/claude-3.5-sonnet", dll.
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def _encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _call_openrouter(api_key: str, image_bytes: bytes, prompt: str, model: str = None) -> str:
    b64_image = _encode_image(image_bytes)
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict:
    """Membersihkan output model (mis. dibungkus ```json ... ```) lalu parse ke dict."""
    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def classify_receipt(api_key: str, image_bytes: bytes, model: str = None) -> dict:
    """
    Tahap 1: AI Classification.
    Menanyakan ke AI Vision apakah gambar adalah struk belanja (receipt) atau bukan.
    Return: {"is_receipt": true/false, "reason": "..."}
    """
    prompt = (
        "Apakah gambar ini merupakan struk belanja (receipt)? "
        "Struk belanja biasanya berisi nama toko, daftar barang, harga, dan total pembayaran. "
        'Jawab HANYA dengan format JSON murni tanpa markdown, contoh: '
        '{"is_receipt": true, "reason": "penjelasan singkat"} atau '
        '{"is_receipt": false, "reason": "penjelasan singkat"}'
    )
    raw = _call_openrouter(api_key, image_bytes, prompt, model)
    return _extract_json(raw)


def extract_receipt_data(api_key: str, image_bytes: bytes, model: str = None) -> dict:
    """
    Tahap 2: OCR Extraction.
    Mengekstrak data terstruktur dari struk belanja dalam format JSON.
    """
    prompt = """
Kamu adalah sistem OCR untuk struk belanja (receipt) Indonesia.
Baca gambar struk belanja berikut dan ekstrak informasinya.
Jawab HANYA dengan JSON murni tanpa markdown, tanpa penjelasan tambahan,
sesuai struktur berikut (kosongkan string "" atau list [] jika data tidak ditemukan):

{
  "nama_toko": "",
  "alamat_toko": "",
  "tanggal_transaksi": "",
  "waktu_transaksi": "",
  "nomor_struk": "",
  "kasir": "",
  "items": [
    {"nama_item": "", "qty": 0, "harga_satuan": 0, "subtotal": 0}
  ],
  "subtotal": 0,
  "pajak": 0,
  "diskon": 0,
  "total": 0,
  "metode_pembayaran": ""
}

Aturan:
- qty, harga_satuan, subtotal, pajak, diskon, total harus berupa angka (number), bukan string.
- tanggal_transaksi gunakan format DD-MM-YYYY jika memungkinkan.
- Jika ada beberapa item, masukkan semua ke dalam list "items".
"""
    raw = _call_openrouter(api_key, image_bytes, prompt, model)
    return _extract_json(raw)
