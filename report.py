# -*- coding: utf-8 -*-
"""
report.py
Dung file Excel Bang Tong Hop tu danh sach ban ghi da xu ly (pipeline.py) va
cau hinh cot dang bat (mapping.py). Xay dung workbook TRUC TIEP bang
openpyxl (khong sua-xoa-cong-tru cot tren file mau goc) de dam bao dung khi
so cot bat/tat thay doi giua cac lan chay - day la nguyen nhan chinh gay loi
merge-cell/cong-thuc-lech khi thao tac truc tiep tren mau co san (da gap
nhieu lan trong qua trinh lam thu cong truoc khi co ung dung nay).
"""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

THIN = Side(style="thin", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

GROUPED_PREFIX_COLUMNS = {"matphai": "MẮT 10/10", "mattrai": "MẮT 10/10",
                          "noi": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "ngoai": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "dalieu": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "sanphukhoa": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "mat": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "tmh": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)",
                          "rhm": "KHÁM LÂM SÀNG\n(Phân loại từ 1 đến 5)"}

LAB_COL_IDS = {"alt": "alt", "ast": "ast", "ure": "ure", "cre": "creatinin",
               "aciduric": "acid_uric", "glu": "glucose", "cho": "cholesterol",
               "tri": "triglycerid", "hdl": "hdl", "ldl": "ldl"}


def _record_value(rec, col_id):
    if col_id in LAB_COL_IDS:
        return rec["lab"][LAB_COL_IDS[col_id]]["value"]
    return rec.get(col_id)


def _record_font_flags(rec, col_id):
    if col_id in LAB_COL_IDS:
        info = rec["lab"][LAB_COL_IDS[col_id]]
        return info["bold"], info["italic"]
    return False, False


def build_report(records, enabled_columns, meta, out_path):
    """
    records: list tu pipeline.process_all()
    enabled_columns: list cac dict cot (tu mapping.ordered_enabled_columns),
                      DA loai 'stt' va 'canhbao'/'ghichu' o cuoi neu can - ham
                      nay tu dong dat dung vi tri chuan (dau: STT..; cuoi:
                      Xếp loại, Ghi chú, Cảnh báo).
    meta: dict {don_vi, tram_y_te, tieu_de, nam, nguoi_lap_bang, giam_doc}
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # dam bao thu tu chuan: cac cot 'giua' truoc, xeploai/ghichu/canhbao luon cuoi cung
    middle = [c for c in enabled_columns if c["id"] not in ("xeploai", "ghichu", "canhbao")]
    tail_order = ["xeploai", "ghichu", "canhbao"]
    tail = [c for tid in tail_order for c in enabled_columns if c["id"] == tid]
    ordered = middle + tail
    n_cols = len(ordered)

    # ---- tieu de ----
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(7, n_cols // 2))
    ws.cell(row=1, column=1, value=meta.get("don_vi_chu_quan", "ỦY BAN NHÂN DÂN PHƯỜNG NHIÊU LỘC")).font = Font(bold=True)
    ws.merge_cells(start_row=1, start_column=n_cols - 6 if n_cols > 13 else max(8, n_cols // 2 + 1),
                   end_row=1, end_column=n_cols)
    ws.cell(row=1, column=(n_cols - 6 if n_cols > 13 else max(8, n_cols // 2 + 1)),
            value="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM").font = Font(bold=True)

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(7, n_cols // 2))
    ws.cell(row=2, column=1, value=meta.get("tram_y_te", "TRẠM Y TẾ")).font = Font(bold=True)
    ws.merge_cells(start_row=2, start_column=n_cols - 6 if n_cols > 13 else max(8, n_cols // 2 + 1),
                   end_row=2, end_column=n_cols)
    ws.cell(row=2, column=(n_cols - 6 if n_cols > 13 else max(8, n_cols // 2 + 1)),
            value="Độc lập - Tự do - Hạnh phúc").font = Font(italic=True)

    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=n_cols)
    c = ws.cell(row=4, column=1, value=f"BẢNG TỔNG HỢP PHÂN LOẠI SỨC KHỎE {meta.get('doi_tuong', '')}")
    c.font = Font(bold=True, size=13)
    c.alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=n_cols)
    c = ws.cell(row=5, column=1, value=f"KHÁM SỨC KHỎE ĐỊNH KỲ NĂM {meta.get('nam', '')}")
    c.font = Font(bold=True, size=12)
    c.alignment = Alignment(horizontal="center")

    # ---- header hang 7-8 ----
    HEADER_ROW, SUBHEADER_ROW = 7, 8
    col_idx = 1
    group_spans = {}  # group_label -> (start_col, end_col)
    for col in ordered:
        label = col["label"]
        group = GROUPED_PREFIX_COLUMNS.get(col["id"]) or (
            "CẬN LÂM SÀNG" if col.get("group") == "CẬN LÂM SÀNG" else None
        )
        if group:
            group_spans.setdefault(group, [col_idx, col_idx])
            group_spans[group][1] = col_idx
            ws.cell(row=SUBHEADER_ROW, column=col_idx, value=label)
        else:
            ws.merge_cells(start_row=HEADER_ROW, start_column=col_idx, end_row=SUBHEADER_ROW, end_column=col_idx)
            ws.cell(row=HEADER_ROW, column=col_idx, value=label)
        col_idx += 1
    for group, (c1, c2) in group_spans.items():
        ws.merge_cells(start_row=HEADER_ROW, start_column=c1, end_row=HEADER_ROW, end_column=c2)
        ws.cell(row=HEADER_ROW, column=c1, value=group)

    for r in (HEADER_ROW, SUBHEADER_ROW):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = Font(bold=True)
            cell.fill = HEADER_FILL
            cell.border = BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # ---- du lieu ----
    DATA_START = 9
    for i, rec in enumerate(records):
        r = DATA_START + i
        for j, col in enumerate(ordered, start=1):
            if col["id"] == "stt":
                val = i + 1
            elif col["id"] == "bmi":
                val = rec.get("bmi")
            else:
                val = _record_value(rec, col["id"])
            cell = ws.cell(row=r, column=j, value=val)
            cell.border = BORDER
            bold, italic = _record_font_flags(rec, col["id"])
            if bold or italic:
                cell.font = Font(bold=bold, italic=italic)
            if col["id"] in ("ghichu", "canhbao"):
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    last_row = DATA_START + len(records) - 1

    # ---- TONG CONG ----
    tong_row = last_row + 1
    ws.cell(row=tong_row, column=1, value="TỔNG CỘNG").font = Font(bold=True)
    xeploai_col_letter = None
    for j, col in enumerate(ordered, start=1):
        if col["id"] in ("ghichu", "canhbao"):
            continue
        if col["id"] == "xeploai":
            xeploai_col_letter = get_column_letter(j)
        if j == 1:
            continue
        letter = get_column_letter(j)
        cell = ws.cell(row=tong_row, column=j, value=f"=COUNTA({letter}{DATA_START}:{letter}{last_row})")
        cell.font = Font(bold=True)
        cell.border = BORDER
    ws.cell(row=tong_row, column=1).border = BORDER

    # ---- thong ke xep loai ----
    stat_start = tong_row + 2
    ws.cell(row=stat_start, column=2, value="Tổng số:")
    ws.cell(row=stat_start, column=3, value=f"=SUM(C{stat_start + 1}:C{stat_start + 5})")
    ws.cell(row=stat_start, column=5, value="Người")
    for k in range(1, 6):
        rr = stat_start + k
        ws.cell(row=rr, column=2, value=f"Loại {k}:")
        if xeploai_col_letter:
            ws.cell(row=rr, column=3,
                    value=f'=COUNTIF(${xeploai_col_letter}${DATA_START}:${xeploai_col_letter}${last_row},"{k}")')
        ws.cell(row=rr, column=5, value="Người")

    note_row = stat_start + 6
    ws.cell(row=note_row, column=2,
            value="Ghi chú: chỉ số cận lâm sàng in đậm = cao hơn giá trị tham chiếu; "
                  "in nghiêng = thấp hơn giá trị tham chiếu.")

    date_row = note_row + 1
    date_col = max(1, n_cols - 6)
    ws.cell(row=date_row, column=date_col, value="Ngày ......... tháng ......... năm .........")

    sign_row = date_row + 1
    ws.cell(row=sign_row, column=2, value="Người Lập Bảng")
    ws.cell(row=sign_row, column=date_col, value="GIÁM ĐỐC")

    name_row = sign_row + 6
    ws.cell(row=name_row, column=2, value=meta.get("nguoi_lap_bang", "Nguyễn Thị Ngọc Sương"))
    if meta.get("giam_doc"):
        ws.cell(row=name_row, column=date_col, value=meta["giam_doc"])

    # ---- do rong cot ----
    for j, col in enumerate(ordered, start=1):
        letter = get_column_letter(j)
        if col["id"] in ("ghichu", "canhbao"):
            ws.column_dimensions[letter].width = 32
        elif col["id"] == "hoten":
            ws.column_dimensions[letter].width = 22
        else:
            ws.column_dimensions[letter].width = 12

    ws.print_title_rows = f"{HEADER_ROW}:{SUBHEADER_ROW}"
    ws.print_area = f"A1:{get_column_letter(n_cols)}{name_row}"
    _set_a4_landscape_fit_width(ws)

    wb.save(out_path)
    return out_path


def _set_a4_landscape_fit_width(ws):
    """In vừa 1 trang KHỔ NGANG A4 theo chiều rộng: toàn bộ số cột nằm gọn
    trên 1 trang ngang, số dòng thì tự chảy xuống nhiều trang nếu cần (không
    ép co chữ theo chiều cao — chỉ ép vừa khổ ngang).
    Lưu ý: chỉ đặt fitToWidth/fitToHeight KHÔNG đủ để Excel áp dụng — phải
    bật thêm cờ pageSetUpPr.fitToPage, nếu không Excel vẫn in theo scale 100%
    mặc định và bảng nhiều cột sẽ bị tràn/cắt trang ngang."""
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0  # 0 = không giới hạn số trang theo chiều dọc
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(
        left=0.3, right=0.3, top=0.4, bottom=0.4, header=0.2, footer=0.2
    )
