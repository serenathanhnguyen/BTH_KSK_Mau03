# -*- coding: utf-8 -*-
"""Kiem tra nhanh (khong dung pytest de don gian): chay het pipeline tren
sample_data/mau_03_sample_fake.xlsx (du lieu hu cau) va in ket qua."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import reader
import mapping as mapping_mod
import pipeline
import report as report_mod

def main():
    rr = reader.read_m03("sample_data/mau_03_sample_fake.xlsx")
    assert rr.total_valid_rows == 3, f"Expected 3 people, got {rr.total_valid_rows}"
    print("OK reader:", rr.total_valid_rows, "nguoi, keyword row =", rr.keyword_row)

    cfg = mapping_mod.load_mapping("mapping.json")
    with open("lab_reference.json", encoding="utf-8") as f:
        lab_ref = json.load(f)
    with open("cbc_reference.json", encoding="utf-8") as f:
        cbc_ref = json.load(f)

    manual_map = {"alt": "kskdk_shm_alat_gpt", "ast": "kskdk_shm_asat_got",
                  "ure": "kskdk_shm_ure", "creatinin": "kskdk_shm_creatinin",
                  "glucose": "kskdk_shm_duongmau",
                  "acid_uric": None, "cholesterol": None, "triglycerid": None,
                  "hdl": None, "ldl": None, "satq": None}

    records = pipeline.process_all(rr, manual_map, lab_ref, cbc_ref,
                                    hb_source_unit="g/dL", urine_enabled=True,
                                    icd_fallback_enabled=True, sort_by_ten=True)
    assert len(records) == 3
    print("OK pipeline: 3 ban ghi")

    for r in records:
        print(" -", r["stt"], r["ten"], "| Xếp loại:", r["xeploai"], "| CTM:", r["ctm"],
              "| Ghi chú:", r["ghichu"], "| Cảnh báo:", r["canhbao"][:80])

    # kiem tra thi luc: nguoi 2 (Trần Thị B) chi co cap kinh lo (8,9) -> phai chon dung cap nay
    b = [r for r in records if r["cccd"] == "000000000002"][0]
    assert (b["matphai"], b["mattrai"]) == (8, 9), b
    print("OK vision pair chon dung cap co du lieu")

    # kiem tra CTM: nguoi 2 co Hb=10.5 (<11.0 -> giam), WBC=11.2 (>10.0 -> tang)
    # -> ngoai tham chieu -> cot T phai rut gon thanh "x" (30/09/2026), chi tiet nam trong Canh bao
    assert b["ctm"] == "x", b["ctm"]
    assert "Hb giảm" in b["canhbao"] and "tăng" in b["canhbao"], b["canhbao"]
    print("OK CTM rut gon dung 'x' khi co chi so ngoai tham chieu, chi tiet o Canh bao:", b["ctm"])

    # nguoi 1 (A) co du 4 chi so CTM deu binh thuong trong sample -> phai la "bt"
    a = [r for r in records if r["cccd"] == "000000000001"][0]
    assert a["ctm"] == "bt", a["ctm"]
    print("OK CTM rut gon dung 'bt' khi tat ca chi so doc duoc deu binh thuong")

    # Ghi chu gio chi hoa CHU CAI DAU DONG (khong con Proper Case tung tu) - 30/09/2026
    assert a["ghichu"] == "Bình thường, hẹn khám định kỳ lần sau", a["ghichu"]
    print("OK Ghi chu dung sentence case (chi hoa chu dau dong):", a["ghichu"])

    # Danh gia (moi 30/09/2026): nguoi 1 co ma ICD noikhoa_chandoanxacdinh_icd=A00.9
    # ("Bệnh tả, không xác định") -> phai bo hau to ", không xác định" va ghi
    # "đang bị bệnh tả"; dong thoi co ma rhm_chandoanxacdinh_icd=K08.1 (mat rang)
    # -> PHAI bi loai khoi Danh gia hoan toan.
    assert a["danhgia"] == "Đang bị bệnh tả", a["danhgia"]
    assert "mất răng" not in (a["danhgia"] or "").lower(), a["danhgia"]
    print("OK Danh gia: bo ', khong xac dinh' va loai 'mat rang':", a["danhgia"])

    # nguoi 2 co ma rhm_chandoansobo_icd=K02.8 ("Sâu răng khác") -> phai giu lai
    # (benh ly rang thuc su, khac voi mat rang) duoi dang "theo dõi bệnh ...";
    # dong thoi co them ma rhm_chandoanxacdinh_icd=Z98.89 (chuong Z - "tinh
    # trang sau can thiep", vd dung de test truong hop nhu tien su sinh mo o
    # San phu khoa) -> PHAI bi loai hoan toan khoi Danh gia (khong phai benh ly,
    # yeu cau Jo 30/09/2026 - loai ca chuong Z, khong rieng Rang Ham Mat).
    assert b["danhgia"] == "Theo dõi bệnh sâu răng khác", b["danhgia"]
    print("OK Danh gia giu lai benh ly rang mieng thuc su, bo ma chuong Z (tinh trang sau can thiep):", b["danhgia"])

    avail = pipeline.column_availability(records)
    enabled_cols = mapping_mod.ordered_enabled_columns(cfg, availability=avail)
    enabled_ids = [c["id"] for c in enabled_cols]
    assert "cho" not in enabled_ids and "tri" not in enabled_ids, "Cot Cholesterol/Triglycerid phai bi an vi khong co du lieu"
    assert "glu" in enabled_ids, "Cot Glucose phai HIEN vi sample co du lieu glucose (kiem tra manual_map co map dung keyword)"
    assert "danhgia" in enabled_ids, "Cot Danh gia phai HIEN (enabled_default=true)"
    for r in records:
        assert r["lab"]["glucose"]["value"] is not None, f"Glucose bi None cho {r['ten']} - kiem tra keyword mapping"
    print("OK auto-hide cot khong co du lieu:", enabled_ids)

    meta = dict(don_vi_chu_quan="ỦY BAN NHÂN DÂN PHƯỜNG X", tram_y_te="TRẠM Y TẾ",
                doi_tuong="CB-NV TEST", nam="2026", nguoi_lap_bang="Test", giam_doc="")
    out_path = "/tmp/smoke_test_output.xlsx"
    report_mod.build_report(records, enabled_cols, meta, out_path)
    assert os.path.exists(out_path)
    print("OK report.build_report ->", out_path)

    # doc lai file xuat ra de kiem tra co du 3 dong + tieu de
    import openpyxl
    wb = openpyxl.load_workbook(out_path)
    ws = wb.active
    assert ws["A9"].value == 1
    assert ws["A11"].value == 3
    print("OK file xuat co du 3 dong du lieu (row 9-11)")

    # cot DANH GIA (moi 30/09/2026) phai xuat hien dung vi tri, truoc GHI CHU,
    # va noi dung dung nhu ban ghi da xu ly o tren
    from openpyxl.utils import get_column_letter
    danhgia_letter = None
    ghichu_letter = None
    for c in range(1, ws.max_column + 1):
        v7 = ws.cell(row=7, column=c).value
        if v7 == "ĐÁNH GIÁ":
            danhgia_letter = get_column_letter(c)
        elif v7 and str(v7).startswith("GHI CHÚ"):
            ghichu_letter = get_column_letter(c)
    assert danhgia_letter is not None, "Khong tim thay cot DANH GIA trong file xuat"
    assert ghichu_letter is not None, "Khong tim thay cot GHI CHU trong file xuat"
    from openpyxl.utils import column_index_from_string
    assert column_index_from_string(danhgia_letter) == column_index_from_string(ghichu_letter) - 1, \
        f"Cot DANH GIA ({danhgia_letter}) phai nam NGAY TRUOC cot GHI CHU ({ghichu_letter})"
    assert ws[f"{danhgia_letter}9"].value == "Đang bị bệnh tả", ws[f"{danhgia_letter}9"].value
    print("OK cot DANH GIA xuat dung vi tri (ngay truoc GHI CHU) va dung noi dung")
    print("\nTAT CA KIEM TRA DEU PASS.")

if __name__ == "__main__":
    main()
