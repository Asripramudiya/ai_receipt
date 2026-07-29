"""
app.py
Aplikasi Streamlit: AI Receipt (Struk Belanja) Classification & OCR
menggunakan OpenRouter Vision API.

Jalankan dengan:
    streamlit run app.py
"""

import os
import io
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_client import classify_receipt, extract_receipt_data, DEFAULT_MODEL
from validation import run_business_rules
from database import init_db, save_receipt, get_all_receipts

load_dotenv()
init_db()

st.set_page_config(page_title="AI Receipt OCR", page_icon="🧾", layout="wide")

def get_config(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default
 

# ---------------------------------------------------------------------------
# Header + Konfigurasi (tanpa sidebar)
# ---------------------------------------------------------------------------
st.title("🧾 AI Receipt Classification & OCR")
st.caption(
    "Klasifikasi & OCR struk belanja menggunakan AI Vision (OpenRouter)"
)

api_key = os.getenv("OPENROUTER_API_KEY", "")
model_name = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
 
with st.expander("ℹ️ Tentang Project & Model AI", expanded=True):
    st.markdown(
        f"""
        ### AI Receipt Classification & OCR
 
        AI Receipt adalah aplikasi berbasis AI Vision yang mampu mengidentifikasi dokumen receipt, 
        melakukan OCR, mengekstrak informasi transaksi secara otomatis, memvalidasi hasil menggunakan business rules, 
        dan menyimpan data ke dalam database. Aplikasi ini membantu mempercepat digitalisasi dokumen transaksi, 
        mengurangi kesalahan input manual, dan meningkatkan efisiensi pengelolaan data receipt.

        **Model AI Vision:** `{model_name}`
        """
    )
    if not api_key:
        st.warning(
            "OPENROUTER_API_KEY belum diset. Isi variabel environment "
            "`OPENROUTER_API_KEY` di file `.env` sebelum menjalankan aplikasi."
        )
 
# ---------------------------------------------------------------------------
# Navigasi halaman menggunakan st.tabs
# ---------------------------------------------------------------------------
tab_process, tab_history = st.tabs(["📤 Upload & Process", "📊 Database History"])

# ---------------------------------------------------------------------------
# UPLOAD & PROCESS  (mencakup: Upload Image, Classification, OCR Result, Validation Result)
# ---------------------------------------------------------------------------
with tab_process:
    st.subheader("📤 Upload & Proses Struk Belanja")

    uploaded_file = st.file_uploader(
        "Upload gambar struk belanja (jpg/png)", type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        st.image(image_bytes, caption=uploaded_file.name, width=350)

        if not api_key:
            st.warning("Masukkan OpenRouter API Key pada bagian Konfigurasi di atas terlebih dahulu.")
        elif st.button("🚀 Proses Dokumen", type="primary"):

            # ---------------- 1. AI Classification ----------------
            with st.spinner("AI sedang mengklasifikasikan gambar..."):
                try:
                    classification = classify_receipt(api_key, image_bytes, model_name)
                except Exception as e:
                    st.error(f"Gagal memanggil AI Classification: {e}")
                    st.stop()

            st.subheader("1️⃣ Classification Result")
            is_receipt = bool(classification.get("is_receipt"))
            if is_receipt:
                st.success(f"✅ Prediction: **Struk Belanja** — {classification.get('reason','')}")
            else:
                st.error(f"❌ Prediction: **Bukan Struk Belanja** — {classification.get('reason','')}")
                st.warning("Proses dihentikan karena gambar bukan dokumen target.")
                st.stop()

            # ---------------- 2. OCR Extraction ----------------
            with st.spinner("AI sedang melakukan OCR..."):
                try:
                    ocr_data = extract_receipt_data(api_key, image_bytes, model_name)
                except Exception as e:
                    st.error(f"Gagal memanggil AI OCR: {e}")
                    st.stop()

            st.subheader("2️⃣ OCR Result")
            with st.expander("Lihat JSON mentah hasil OCR"):
                st.json(ocr_data)

            flat_rows = []
            for k, v in ocr_data.items():
                if k != "items":
                    flat_rows.append({"Field": k, "Value": v})
            st.table(pd.DataFrame(flat_rows))

            if ocr_data.get("items"):
                st.markdown("**Daftar Item**")
                st.dataframe(pd.DataFrame(ocr_data["items"]), use_container_width=True)

            # ---------------- 3. Business Rule Validation ----------------
            st.subheader("3️⃣ Validation Result")
            validation_result = run_business_rules(ocr_data)

            val_rows = []
            for field, res in validation_result.items():
                if field == "overall_status":
                    continue
                val_rows.append(
                    {"Field": field, "Status": res["status"], "Keterangan": res["message"]}
                )
            val_df = pd.DataFrame(val_rows)

            val_df["Status"] = val_df["Status"].apply(
                lambda s: f"✅ {s}" if s == "VALID" else f"❌ {s}"
            )

            def highlight(row):
                if "VALID" in row["Status"] and "❌" not in row["Status"]:
                    bg, fg = "#14532d", "#dcfce7"   # hijau tua bg, hijau muda teks
                else:
                    bg, fg = "#7f1d1d", "#fee2e2"   # merah tua bg, merah muda teks
                return [f"background-color: {bg}; color: {fg}"] * len(row)

            st.dataframe(val_df.style.apply(highlight, axis=1), use_container_width=True)

            overall = validation_result["overall_status"]
            if overall == "VALID":
                st.success("✅ Status Keseluruhan: VALID")
            else:
                st.error("❌ Status Keseluruhan: INVALID")

            # ---------------- 4. Save to Database ----------------
            st.subheader("4️⃣ Simpan ke Database")
            new_id = save_receipt(ocr_data, validation_result, uploaded_file.name)
            st.success(f"Data berhasil disimpan ke database dengan ID #{new_id}.")

# ---------------------------------------------------------------------------
# DATABASE HISTORY
# ---------------------------------------------------------------------------
with tab_history:
    st.subheader("📊 Database History")

    records = get_all_receipts()
    if not records:
        st.info("Belum ada data tersimpan.")
    else:
        df = pd.DataFrame(records)
        display_df = df[
            ["id", "nama", "nomor_dokumen", "jenis_dokumen", "tanggal_upload",
             "status_validasi", "total_belanja", "image_name"]
        ].rename(columns={
            "id": "ID",
            "nama": "Nama Toko",
            "nomor_dokumen": "Nomor Struk",
            "jenis_dokumen": "Jenis Dokumen",
            "tanggal_upload": "Tanggal Upload",
            "status_validasi": "Status Validasi",
            "total_belanja": "Total",
            "image_name": "File Gambar",
        })
        st.dataframe(display_df, use_container_width=True)

        csv_buffer = io.StringIO()
        display_df.to_csv(csv_buffer, index=False)
        st.download_button(
            "⬇️ Export CSV",
            data=csv_buffer.getvalue(),
            file_name="receipt_history.csv",
            mime="text/csv",
        )

        with st.expander("Lihat detail JSON per record"):
            selected_id = st.selectbox("Pilih ID", df["id"].tolist())
            selected_row = df[df["id"] == selected_id].iloc[0]
            st.json(json.loads(selected_row["data_json"]))
