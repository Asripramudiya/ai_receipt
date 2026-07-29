"""
run_batch_test.py
Script sederhana untuk menjalankan pengujian klasifikasi terhadap minimal
20 gambar sesuai ketentuan project (poin 8. Testing).

Cara pakai:
1. Siapkan folder gambar test, misal: testing/images/
2. Isi file test_cases_template.csv (kolom image_filename & expected_prediction)
3. Jalankan: python testing/run_batch_test.py
4. Hasil akan disimpan ke testing/test_results.csv
"""

import os
import sys
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_client import classify_receipt  # noqa: E402

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")
INPUT_CSV = os.path.join(os.path.dirname(__file__), "test_cases_template.csv")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "test_results.csv")


def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Set environment variable OPENROUTER_API_KEY terlebih dahulu.")
        return

    rows = []
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_path = os.path.join(IMAGES_DIR, row["image_filename"])
            if not os.path.exists(img_path):
                row["actual_prediction"] = "FILE NOT FOUND"
                rows.append(row)
                continue
            with open(img_path, "rb") as img_f:
                image_bytes = img_f.read()
            try:
                result = classify_receipt(api_key, image_bytes)
                is_receipt = result.get("is_receipt")
                row["actual_prediction"] = "Struk Belanja" if is_receipt else "Bukan Struk Belanja"
            except Exception as e:
                row["actual_prediction"] = f"ERROR: {e}"
            rows.append(row)
            print(f"{row['image_filename']}: {row['actual_prediction']}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    correct = sum(1 for r in rows if r["expected_prediction"] == r["actual_prediction"])
    print(f"\nAkurasi: {correct}/{len(rows)} ({correct/len(rows)*100:.1f}%)")
    print(f"Hasil lengkap disimpan di: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
