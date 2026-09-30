# -*- coding: utf-8 -*-
"""
app.py — Giao dien Streamlit cho ung dung xuat Bang Tong Hop KSK.

Chay thu: streamlit run app.py

LUU Y BAO MAT (muc 5 khung nguyen tac):
  File du lieu kham thuc te CHI di qua phien lam viec Streamlit nay trong bo
  nho, KHONG duoc luu vao repo/GitHub. Khong ghi log ten/CCCD ra ngoai
  (console, file log) o bat ky dau trong ung dung.
"""
import io
import json
from collections import Counter

import streamlit as st

import reader
import mapping as mapping_mod
import pipeline
import report as report_mod

st.set_page_config(page_title="Bảng Tổng Hợp KSK", layout="wide")

LAB_ID_TO_KEY = {"alt": "alt", "ast": "ast", "ure": "ure", "cre": "creatinin",
                  "aciduric": "acid_uric", "glu": "glucose", "cho": "cholesterol",
                  "tri": "triglycerid", "hdl": "hdl", "ldl": "ldl"}
NO_KEYWORD_LAB_IDS = ["aciduric", "cho", "tri", "hdl", "ldl"]  # chua co keyword mac dinh trong mapping.json


@st.cache_data(show_spinner=False)
def _load_configs():
    cfg = mapping_mod.load_mapping("mapping.json")
    with open("lab_reference.json", "r", encoding="utf-8") as f:
        lab_ref = json.load(f)
    with open("cbc_reference.json", "r", encoding="utf-8") as f:
        cbc_ref = json.load(f)
    return cfg, lab_ref, cbc_ref


def main():
    st.title("Bảng Tổng Hợp Phân Loại Sức Khỏe — từ file Mẫu 03")
    cfg, lab_ref, cbc_ref = _load_configs()

    if lab_ref["meta"]["trang_thai"] != "":
        for key, ref in lab_ref["mau"].items():
            if ref.get("can_xac_nhan"):
                st.warning(
                    f"Ngưỡng tham chiếu cho **{key}** chưa được xác nhận lại "
                    f"({ref.get('ghi_chu', '')}). Đang dùng tạm {ref['duoi']}–{ref['tren']} {ref['don_vi']}."
                )

    uploaded = st.file_uploader("Tải lên file Mẫu 03 (.xlsx)", type=["xlsx"])
    if not uploaded:
        st.info("Tải lên file Mẫu 03 (sheet ThongTinHanhChinh) để bắt đầu.")
        return

    try:
        rr = reader.read_m03(io.BytesIO(uploaded.getvalue()))
    except Exception as e:
        st.error(f"Không đọc được file: {e}")
        return

    with st.expander("Kiểm tra đầu vào (bấm để xem chi tiết)", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Số dòng đã quét", rr.total_rows_scanned)
        c2.metric("Số người hợp lệ", rr.total_valid_rows)
        c3.metric("Dòng bỏ qua", len(rr.skipped_rows))
        if rr.skipped_rows:
            st.write("Lý do bỏ qua:", rr.skipped_rows)
        if rr.duplicate_keywords:
            st.warning(f"Keyword trùng vị trí trong file: {rr.duplicate_keywords} "
                       f"(ứng dụng đang lấy giá trị ở vị trí đầu tiên tìm thấy).")
        found = sorted(rr.kw_to_cols.keys())
        st.caption(f"Đã nhận diện {len(found)} keyword ở hàng {rr.keyword_row}.")

        # CCCD trung
        cccds = [row.get("dinh_danh_ca_nhan") for row in rr.rows]
        dup = [k for k, v in Counter([c for c in cccds if c]).items() if v > 1]
        if dup:
            st.warning(f"Có {len(dup)} CCCD xuất hiện nhiều lần — kiểm tra lại trước khi gộp: {dup}")

    st.subheader("1. Thông tin tiêu đề báo cáo")
    colA, colB = st.columns(2)
    with colA:
        don_vi_chu_quan = st.text_input("Đơn vị chủ quản", "ỦY BAN NHÂN DÂN PHƯỜNG NHIÊU LỘC")
        tram_y_te = st.text_input("Tên trạm/cơ sở", "TRẠM Y TẾ")
        doi_tuong = st.text_input("Đối tượng khám (điền sau 'PHÂN LOẠI SỨC KHỎE')", "CB-NV ...")
    with colB:
        nam = st.text_input("Năm khám", "2026")
        nguoi_lap_bang = st.text_input("Người lập bảng", "Nguyễn Thị Ngọc Sương")
        giam_doc = st.text_input("Tên Giám đốc (để trống nếu chưa cần)", "")

    st.subheader("2. Cấu hình xử lý")
    c1, c2, c3 = st.columns(3)
    with c1:
        hb_unit = st.selectbox(
            "Đơn vị Hb thực tế trong file này", ["g/dL", "g/L"], index=0,
            help="Header M03 ghi (g/L) nhưng dữ liệu thực tế thường nhập dạng g/dL. "
                 "Chọn đúng đơn vị thực tế — ứng dụng KHÔNG tự đoán theo độ lớn số liệu.",
        )
    with c2:
        urine_enabled = st.checkbox("Tự đánh giá bt/x cho nước tiểu (tỉ trọng/pH)", value=True)
    with c3:
        icd_fallback = st.checkbox("Cho phép ghép ICD khi Ghi rõ & Kết luận đều trống", value=True)
    sort_by_ten = st.checkbox("Sắp xếp theo cột TÊN (A→Z, theo bảng chữ cái tiếng Việt)", value=True)

    st.subheader("3. Ánh xạ thủ công cho các chỉ số chưa có keyword mặc định")
    st.caption("Cholesterol/Triglycerid/HDL/LDL/Acid Uric/Siêu âm tổng quát thường KHÔNG có keyword cố định "
               "trong Mẫu 03 — chọn đúng cột nguồn nếu file này có đo các chỉ số này. Để trống nếu không có.")
    available_keywords = [""] + sorted(rr.kw_to_cols.keys())
    manual_map = {}
    cols_ui = st.columns(3)
    default_kw = {"alt": "kskdk_shm_alat_gpt", "ast": "kskdk_shm_asat_got",
                  "ure": "kskdk_shm_ure", "creatinin": "kskdk_shm_creatinin",
                  "glucose": "kskdk_shm_duongmau"}
    for key, kw in default_kw.items():
        manual_map[key] = kw if kw in rr.kw_to_cols else None
    for i, col_id in enumerate(NO_KEYWORD_LAB_IDS):
        key = LAB_ID_TO_KEY[col_id]
        with cols_ui[i % 3]:
            choice = st.selectbox(f"Cột cho '{key}'", available_keywords, key=f"map_{key}")
            manual_map[key] = choice or None
    manual_map_satq = st.selectbox("Cột cho 'Siêu âm tổng quát' (satq)", available_keywords, key="map_satq")

    cfg_local = dict(cfg)
    availability_preview = {"aciduric": bool(manual_map.get("acid_uric")),
                            "cho": bool(manual_map.get("cholesterol")),
                            "tri": bool(manual_map.get("triglycerid")),
                            "hdl": bool(manual_map.get("hdl")),
                            "ldl": bool(manual_map.get("ldl"))}

    if st.button("Xử lý dữ liệu", type="primary"):
        records = pipeline.process_all(
            rr, {**manual_map, "satq": manual_map_satq or None}, lab_ref, cbc_ref,
            hb_source_unit=hb_unit, urine_enabled=urine_enabled,
            icd_fallback_enabled=icd_fallback, sort_by_ten=sort_by_ten,
        )
        st.session_state["records"] = records
        st.session_state["meta"] = dict(
            don_vi_chu_quan=don_vi_chu_quan, tram_y_te=tram_y_te, doi_tuong=doi_tuong,
            nam=nam, nguoi_lap_bang=nguoi_lap_bang, giam_doc=giam_doc,
        )

    if "records" not in st.session_state:
        return

    records = st.session_state["records"]
    meta = st.session_state["meta"]

    avail = pipeline.column_availability(records)
    avail.update(availability_preview)
    enabled_cols = mapping_mod.ordered_enabled_columns(cfg, availability=avail)

    st.subheader("4. Chọn cột hiển thị trong báo cáo")
    mode = st.radio("Chế độ cột", ["Giống mẫu BTH (tự động ẩn cột trống)", "Tự chọn cột"], index=0)
    if mode == "Tự chọn cột":
        all_ids = [c["id"] for c in cfg["columns"]]
        labels = {c["id"]: c["label"].replace("\n", " ") for c in cfg["columns"]}
        default_selected = [c["id"] for c in enabled_cols]
        chosen = st.multiselect("Các cột sẽ xuất ra báo cáo", all_ids,
                                default=default_selected, format_func=lambda i: labels[i])
        enabled_cols = [mapping_mod.get_column(cfg, i) for i in chosen]
        enabled_cols = sorted(enabled_cols, key=lambda c: c["order"])

    st.subheader("5. Thống kê xếp loại")
    dist = Counter(r.get("xeploai") for r in records)
    st.write({f"Loại {k}" if k else "Chưa xếp loại": v for k, v in sorted(dist.items(), key=lambda x: (x[0] is None, x[0]))})

    st.subheader("6. Xem trước & chỉnh sửa thủ công (Ghi chú / CTM / Cảnh báo)")
    st.caption("Sửa trực tiếp trong bảng bên dưới nếu cần — nội dung đã sửa sẽ được dùng khi xuất Excel. "
               "Không tự động ghi chẩn đoán bệnh vào CTM.")
    import pandas as pd
    preview_rows = []
    for r in records:
        preview_rows.append({
            "STT": r["stt"], "Họ tên": r["hoten"], "CCCD": r["cccd"],
            "Xếp loại": r["xeploai"], "CTM": r["ctm"], "Ghi chú": r["ghichu"],
            "Cảnh báo": r["canhbao"],
        })
    df = pd.DataFrame(preview_rows)
    edited = st.data_editor(df, use_container_width=True, num_rows="fixed", key="editor")

    # ap dung chinh sua thu cong nguoc lai vao records (theo STT)
    edited_by_stt = {row["STT"]: row for row in edited.to_dict("records")}
    for r in records:
        e = edited_by_stt.get(r["stt"])
        if e:
            if e["CTM"] != r["ctm"]:
                r["ctm"] = e["CTM"]
                r["canhbao"] = (r["canhbao"] + " | CTM đã chỉnh tay.").strip(" |")
            r["ghichu"] = e["Ghi chú"]
            r["canhbao"] = e["Cảnh báo"]

    st.subheader("7. Xuất báo cáo")
    if st.button("Tạo file Excel"):
        out_path = "/tmp/BTH_KSK_output.xlsx"
        report_mod.build_report(records, enabled_cols, meta, out_path)
        with open(out_path, "rb") as f:
            st.download_button(
                "Tải file Bảng Tổng Hợp (.xlsx)", f,
                file_name=f"BTH_KSK_{nam}_{doi_tuong.replace(' ', '_') or 'baocao'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.success("Đã tạo file. Vui lòng người phụ trách chuyên môn rà soát cột Cảnh báo trước khi dùng chính thức, "
                   "sau đó xóa cột Cảnh báo khi hoàn tất.")


if __name__ == "__main__":
    main()
