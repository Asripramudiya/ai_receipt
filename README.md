# AI Receipt (Struk Belanja) Classification & OCR

Final project: aplikasi AI Vision end-to-end untuk klasifikasi dan OCR **struk belanja**,
menggunakan **OpenRouter Vision API**, validasi **Business Rule**, penyimpanan ke
**Database (SQLite)**, dan dashboard **Streamlit**.

## Struktur Project

```
receipt_ocr_project/
├── app.py                  # Aplikasi Streamlit (Home, Upload & Process, Database History)
├── ai_client.py            # Fungsi pemanggilan OpenRouter Vision API (klasifikasi + OCR)
├── validation.py           # Business rule validation (Python murni)
├── database.py             # Operasi SQLite (simpan & ambil data)
├── requirements.txt
├── .env.example
├── data/
│   └── receipts.db         # Dibuat otomatis saat pertama kali dijalankan
└── testing/
    ├── test_cases_template.csv
    └── run_batch_test.py
```

---

## STEP 1 — Siapkan API Key OpenRouter

1. Buka https://openrouter.ai dan buat akun.
2. Buka https://openrouter.ai/keys → buat API key baru (contoh: `sk-or-xxxxxxxx`).
3. Pastikan akun memiliki sedikit kredit (beberapa model vision gratis/murah,
   misal `google/gemini-2.0-flash-001`), atau gunakan model berbayar seperti
   `openai/gpt-4o-mini`.

## STEP 2 — Install Environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## STEP 3 — Konfigurasi API Key

Salin `.env.example` menjadi `.env`, lalu isi:

```
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=openai/gpt-4o-mini
```

(API key juga bisa dimasukkan langsung lewat kolom konfigurasi di halaman
aplikasi saat runtime, tidak wajib lewat `.env`.)

## STEP 4 — Pahami Alur Kode (Workflow)

**1. Upload Image** — `app.py`, `st.file_uploader` menerima gambar struk belanja.

**2. AI Classification** — `ai_client.classify_receipt()` mengirim gambar ke
OpenRouter dengan prompt "apakah ini struk belanja?" dan mengembalikan
`{"is_receipt": true/false, "reason": "..."}`. Jika `false`, proses dihentikan
(`st.stop()`), sesuai diagram alur pada spesifikasi project.

**3. OCR Extraction** — `ai_client.extract_receipt_data()` memanggil AI Vision
untuk membaca seluruh isi struk (nama toko, tanggal, daftar item, subtotal,
pajak, diskon, total, dst) dan mengembalikannya sebagai **JSON**. Tidak ada
regex yang dipakai untuk membaca isi dokumen — pembacaan teks 100% dilakukan
oleh model AI Vision.

**4. JSON Result** — hasil OCR ditampilkan mentah (`st.json`) dan dalam bentuk
tabel (`st.table` / `st.dataframe`).

**5. Business Rule Validation** — `validation.run_business_rules()` mengecek
data hasil OCR dengan Python murni:
   - `nama_toko` tidak boleh kosong
   - `tanggal_transaksi` harus bisa diparse ke format tanggal yang valid dan masuk akal
   - Setiap `item` harus punya qty > 0, harga_satuan ≥ 0, dan subtotal ≈ qty × harga_satuan
   - `total` harus konsisten dengan `subtotal + pajak - diskon` (toleransi pembulatan)
   - `nomor_struk` dicek keberadaannya (opsional, tidak menggugurkan validasi)

   Field regex di `validation.py` **hanya** dipakai untuk membersihkan format
   angka (mis. `"Rp 12.000"` → `12000.0`), bukan untuk membaca dokumen — sesuai
   ketentuan "tidak diperbolehkan menggunakan Regex untuk OCR".

**6A/6B. Save Database / Tampilkan Error** — jika status keseluruhan `VALID`
maupun `INVALID`, data tetap disimpan ke SQLite (`database.save_receipt()`)
lengkap dengan status validasinya, sehingga histori tetap tercatat dan bisa
ditelusuri di halaman *Database History*.

## STEP 5 — Jalankan Aplikasi

```bash
streamlit run app.py
```

Buka `http://localhost:8501`. Tidak ada sidebar — konfigurasi API key & model
ada di bagian atas halaman (`⚙️ Konfigurasi API Key & Model`), dan navigasi
antar halaman memakai **`st.tabs`**:

| Tab | Isi |
|---|---|
| **📤 Upload & Process** | Upload gambar → Classification → OCR Result → Validation Result → Save DB |
| **📊 Database History** | Tabel seluruh histori data + tombol Export CSV |

## STEP 6 — Testing (Minimal 20 Gambar)

1. Kumpulkan minimal 20 gambar: sebagian struk belanja asli, sebagian bukan
   (KTP, SIM, plat nomor, foto random, dll) — lihat contoh di
   `testing/test_cases_template.csv`.
2. Simpan gambar-gambar tersebut di `testing/images/`.
3. Jalankan:
   ```bash
   export OPENROUTER_API_KEY=sk-or-xxxx   # Windows: set OPENROUTER_API_KEY=...
   python testing/run_batch_test.py
   ```
4. Script akan mencetak prediksi tiap gambar dan menyimpan hasil ke
   `testing/test_results.csv`, beserta persentase akurasi klasifikasi.

## STEP 7 — Deployment

Pilih salah satu platform berikut:

### A. Streamlit Community Cloud
1. Push project ini ke repository GitHub (jangan commit file `.env` / API key asli).
2. Buka https://share.streamlit.io → "New app" → pilih repo & `app.py`.
3. Di menu **Secrets**, tambahkan:
   ```
   OPENROUTER_API_KEY = "sk-or-xxxx"
   OPENROUTER_MODEL = "openai/gpt-4o-mini"
   ```
4. Deploy.

### B. Hugging Face Spaces
1. Buat Space baru dengan SDK **Streamlit**.
2. Upload seluruh file project.
3. Tambahkan `OPENROUTER_API_KEY` di **Settings → Repository secrets**.

### C. Railway / Render
1. Buat service baru dari repo GitHub.
2. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
3. Tambahkan environment variable `OPENROUTER_API_KEY`.

## Catatan Business Rule Struk Belanja

Contoh kasus INVALID yang akan terdeteksi otomatis:
- `"NIK tidak valid"` (untuk KTP) → analognya di sini: **"Total tidak konsisten:
  subtotal + pajak - diskon ≠ total tertulis"**
- Tanggal transaksi di masa depan atau format tidak dikenali → `INVALID`
- Tidak ada item belanja terdeteksi sama sekali → `INVALID`

## Catatan Penting

- Ganti `OPENROUTER_MODEL` sesuai model vision yang tersedia & sesuai budget di
  akun OpenRouter Anda (cek daftar model terbaru di https://openrouter.ai/models,
  filter kapabilitas "Image input").
- Aplikasi ini menyimpan **semua** hasil (baik VALID maupun INVALID) ke database
  agar histori validasi tetap lengkap dan bisa diaudit — ini praktik umum di
  sistem industri (hasil AI selalu diverifikasi, bukan langsung dibuang).
