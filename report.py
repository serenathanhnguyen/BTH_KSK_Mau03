# -*- coding: utf-8 -*-
"""
report.py
Dung file Excel Bang Tong Hop bang cach NHAN BAN template chuan
(templates/BTH_KSK_template.xlsx) va CHINH SUA truc tiep tren do — dung
CHINH XAC phuong phap da kiem chung nhieu lan trong du an nay (VISSAN,
Hai Thinh, Thai Thinh...): unmerge -> xoa cot khong co du lieu -> chen/xoa
dong cho khop so nguoi -> remerge -> dien du lieu + reset font -> sua lai
cong thuc COUNTA/COUNTIF. KHONG dung Workbook rong dung tu code (ban truoc
da lam vay va lam sai lech cach anh xa/bo cuc cot ma Jo da quen dung) —
xem README/CHANGELOG de biet ly do doi lai cach lam nay ngay 30/09/2026.

mapping.py/pipeline.py/transforms.py KHONG doi — file nay chi lo phan
"ve" ket qua da xu ly ra Excel.
"""
import copy
import os

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter, column_index_from_string

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "BTH_KSK_template.xlsx")

# Vi tri CO DINH cua tung cot trong template goc (truoc khi xoa cot khong dung)
TEMPLATE_COL_LETTER = {
    "stt": "A", "hoten": "B", "ten": "C", "cccd": "D", "ngaysinh": "E", "gioitinh": "F",
    "chieucao": "G", "cannang": "H", "bmi": "I", "huyetap": "J",
    "matphai": "K", "mattrai": "L",
    "noi": "M", "ngoai": "N", "dalieu": "O", "sanphukhoa": "P", "mat": "Q", "tmh": "R", "rhm": "S",
    "ctm": "T", "alt": "U", "ast": "V", "ure": "W", "cre": "X", "aciduric": "Y", "glu": "Z",
    "cho": "AA", "tri": "AB", "hdl": "AC", "ldl": "AD", "nt": "AE", "satq": "AF", "satv": "AG", "xq": "AH",
    "xeploai": "AI", "danhgia": "AJ", "ghichu": "AK", "canhbao": "AL",
}
TEMPLATE_LAST_COL = column_index_from_string("AL")  # 38 (them cot DANH GIA truoc GHI CHU, 30/09/2026)
TEMPLATE_DATA_ROWS = list(range(9, 19))     # 10 dong mau san co
TEMPLATE_TOTAL_ROW = 19
TEMPLATE_STAT_START = 21                    # "Tổng số:" ; Loại 1..5 = 22..26
TEMPLATE_NOTE_ROW = 27
TEMPLATE_DATE_ROW = 28
TEMPLATE_SIGN_ROW = 29
TEMPLATE_NAME_ROW = 35

LAB_COL_IDS = {"alt": "alt", "ast": "ast", "ure": "ure", "cre": "creatinin",
               "aciduric": "acid_uric", "glu": "glucose", "cho": "cholesterol",
               "tri": "triglycerid", "hdl": "hdl", "ldl": "ldl"}


def _record_value(rec, col_id):
    if col_id in LAB_COL_IDS:
        return rec["lab"][LAB_COL_IDS[col_id]]["value"]
    if col_id == "stt":
        return rec["stt"]
    return rec.get(col_id)


def _record_font_flags(rec, col_id):
    if col_id in LAB_COL_IDS:
        info = rec["lab"][LAB_COL_IDS[col_id]]
        return info["bold"], info["italic"]
    return False, False


def _nearest_surviving(col_idx, deleted_set, direction):
    c = col_idx
    while c in deleted_set:
        c += direction
    return c


def build_report(records, enabled_columns, meta, out_path, template_path=TEMPLATE_PATH):
    """
    records: list tu pipeline.process_all() — KHONG doi so voi truoc.
    enabled_columns: list cac dict cot (tu mapping.ordered_enabled_columns) —
                      dung DE QUYET DINH cot nao GIU LAI trong template, khong
                      dung de tu dung cot moi (template da co san du 37 cot).
    meta: dict {don_vi_chu_quan, tram_y_te, doi_tuong, nam, nguoi_lap_bang, giam_doc}
    """
    wb = load_workbook(template_path)
    ws = wb.active

    enabled_ids = {c["id"] for c in enabled_columns}
    all_ids = list(TEMPLATE_COL_LETTER.keys())
    disabled_ids = [cid for cid in all_ids if cid not in enabled_ids]
    deleted_cols = sorted(column_index_from_string(TEMPLATE_COL_LETTER[cid]) for cid in disabled_ids)
    deleted_set = set(deleted_cols)

    # ---- luu lai do rong cot GOC theo tung col_id TRUOC khi xoa cot ----
    # (openpyxl KHONG tu doi cho column_dimensions khi delete_cols/insert_cols
    # - do rong bi "dinh" theo chu cai cu, nen phai tu luu va gan lai theo
    # chu cai MOI sau khi xoa, neu khong cot con lai se bi sai do rong)
    orig_col_widths = {}
    for cid, letter in TEMPLATE_COL_LETTER.items():
        dim = ws.column_dimensions.get(letter)
        if dim is not None and dim.width is not None:
            orig_col_widths[cid] = dim.width

    # ---- unmerge tat ca, ghi lai de remerge sau khi xoa cot/dong ----
    merges_before = [(m.min_row, m.min_col, m.max_row, m.max_col) for m in ws.merged_cells.ranges]
    for m in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(m))

    # ---- xoa cot khong dung (tu phai sang trai de khong lech chi so) ----
    for col_idx in sorted(deleted_cols, reverse=True):
        ws.delete_cols(col_idx, 1)

    def remap_col(c):
        return c - sum(1 for d in deleted_cols if d < c)

    # ---- chen/xoa dong cho khop so nguoi (QUY TAC 5) ----
    n_people = len(records)
    n_template_rows = len(TEMPLATE_DATA_ROWS)
    row_delta = n_people - n_template_rows
    last_sample_row = TEMPLATE_DATA_ROWS[-1]
    if row_delta > 0:
        ws.insert_rows(last_sample_row + 1, row_delta)
        # sao chep style dong mau cuoi cung sang cac dong moi chen
        n_cols_after_delete = TEMPLATE_LAST_COL - len(deleted_cols)
        for i in range(row_delta):
            new_r = last_sample_row + 1 + i
            for c in range(1, n_cols_after_delete + 1):
                src = ws.cell(row=last_sample_row, column=c)
                dst = ws.cell(row=new_r, column=c)
                dst.font = copy.copy(src.font)
                dst.border = copy.copy(src.border)
                dst.fill = copy.copy(src.fill)
                dst.alignment = copy.copy(src.alignment)
                dst.number_format = src.number_format
            ws.row_dimensions[new_r].height = ws.row_dimensions[last_sample_row].height
    elif row_delta < 0:
        ws.delete_rows(last_sample_row + row_delta + 1, -row_delta)

    def remap_row(r):
        if r > last_sample_row:
            return r + row_delta
        return r

    # ---- remerge (bo qua merge nam trong pham vi cot da xoa hoan toan) ----
    def nearest_start(c):
        while c in deleted_set:
            c += 1
        return c

    def nearest_end(c):
        while c in deleted_set:
            c -= 1
        return c

    for (r1, c1, r2, c2) in merges_before:
        # merge trong vung du lieu mau (row 9..18) khong can remerge (moi o rieng le)
        if TEMPLATE_DATA_ROWS[0] <= r1 <= TEMPLATE_DATA_ROWS[-1]:
            continue
        nr1, nr2 = remap_row(r1), remap_row(r2)
        sc1, sc2 = nearest_start(c1), nearest_end(c2)
        if sc1 > sc2:
            continue
        nc1, nc2 = remap_col(sc1), remap_col(sc2)
        if nc1 > nc2 or nr1 > nr2:
            continue
        ws.merge_cells(start_row=nr1, start_column=nc1, end_row=nr2, end_column=nc2)

    # ---- vi tri cac dong/cot sau khi xoa/chen ----
    DATA_START = 9
    last_row = DATA_START + n_people - 1
    tong_row = remap_row(TEMPLATE_TOTAL_ROW)
    stat_start = remap_row(TEMPLATE_STAT_START)
    note_row = remap_row(TEMPLATE_NOTE_ROW)
    date_row = remap_row(TEMPLATE_DATE_ROW)
    sign_row = remap_row(TEMPLATE_SIGN_ROW)
    name_row = remap_row(TEMPLATE_NAME_ROW)

    col_letter = {}  # col_id -> cot MOI (sau xoa) — chi cho cac cot con giu
    for cid in enabled_ids:
        orig_idx = column_index_from_string(TEMPLATE_COL_LETTER[cid])
        col_letter[cid] = get_column_letter(remap_col(orig_idx))

    # ---- gan lai do rong cot dung theo VI TRI MOI (khac phuc loi openpyxl
    # khong tu doi cho column_dimensions khi delete_cols - xem ghi chu o tren) ----
    for cid, new_letter in col_letter.items():
        if cid in orig_col_widths:
            ws.column_dimensions[new_letter].width = orig_col_widths[cid]

    # ---- tieu de ----
    ws["A4"] = f"BẢNG TỔNG HỢP PHÂN LOẠI SỨC KHỎE {meta.get('doi_tuong', '')}"
    ws["A5"] = f"KHÁM SỨC KHỎE ĐỊNH KỲ NĂM {meta.get('nam', '')}"
    if meta.get("don_vi_chu_quan"):
        ws["A1"] = meta["don_vi_chu_quan"]
    if meta.get("tram_y_te"):
        ws["A2"] = meta["tram_y_te"]

    # ---- du lieu ----
    for i, rec in enumerate(records):
        r = DATA_START + i
        for cid, letter in col_letter.items():
            if cid == "stt":
                val = i + 1
            elif cid == "bmi":
                val = f"={col_letter['cannang']}{r}/({col_letter['chieucao']}{r}*{col_letter['chieucao']}{r})*10000"
            else:
                val = _record_value(rec, cid)
            cell = ws[f"{letter}{r}"]
            cell.value = val
            bold, italic = _record_font_flags(rec, cid)
            f = cell.font
            # QUY TAC (30/09/2026): moi cho in dam (cao hon tham chieu) doi mau do;
            # cac o khac (binh thuong / in nghieng cho thap hon) giu nguyen mau chu.
            font_color = "FFFF0000" if bold else f.color
            cell.font = Font(name=f.name, size=f.size, bold=bold, italic=italic, color=font_color)

    # ---- TONG CONG: COUNTA tu F den Xep loai (khong tinh Ghi chu/Canh bao) ----
    ws[f"A{tong_row}"] = "TỔNG CỘNG"
    skip_ids = {"stt", "hoten", "ten", "cccd", "ngaysinh", "danhgia", "ghichu", "canhbao"}
    for cid, letter in sorted(col_letter.items(), key=lambda kv: column_index_from_string(kv[1])):
        if cid in skip_ids:
            continue
        ws[f"{letter}{tong_row}"] = f"=COUNTA({letter}{DATA_START}:{letter}{last_row})"

    # ---- thong ke xep loai ----
    ws[f"C{stat_start}"] = f"=SUM(C{stat_start + 1}:C{stat_start + 5})"
    xl_letter = col_letter.get("xeploai")
    for k in range(1, 6):
        rr = stat_start + k
        if xl_letter:
            ws[f"C{rr}"] = f'=COUNTIF(${xl_letter}${DATA_START}:${xl_letter}${last_row},"{k}")'

    ws[f"B{note_row}"] = ("Ghi chú: chỉ số cận lâm sàng in đậm màu đỏ = cao hơn giá trị tham chiếu; "
                          "in nghiêng = thấp hơn giá trị tham chiếu.")
    # ngay ky luon giu dang cham cham, KHONG dien so cu the (QUY TAC 4)
    date_col_letter = get_column_letter(remap_col(column_index_from_string("V")))
    ws[f"{date_col_letter}{date_row}"] = "Ngày ......... tháng ......... năm ........."
    ws[f"B{sign_row}"] = "Người Lập Bảng"
    ws[f"{date_col_letter}{sign_row}"] = "GIÁM ĐỐC"
    ws[f"B{name_row}"] = meta.get("nguoi_lap_bang", "Nguyễn Thị Ngọc Sương")
    if meta.get("giam_doc"):
        ws[f"{date_col_letter}{name_row}"] = meta["giam_doc"]

    n_cols_final = TEMPLATE_LAST_COL - len(deleted_cols)

    # ---- wrap text cho HỌ & TÊN, ĐÁNH GIÁ va GHI CHÚ (yeu cau Jo 30/09/2026) ----
    for cid in ("hoten", "danhgia", "ghichu"):
        letter = col_letter.get(cid)
        if not letter:
            continue
        for r in range(7, last_row + 1):
            cell = ws[f"{letter}{r}"]
            al = cell.alignment
            cell.alignment = Alignment(
                horizontal=al.horizontal, vertical=al.vertical, wrap_text=True,
                text_rotation=al.text_rotation, indent=al.indent,
            )

    # ---- font size (yeu cau Jo 30/09/2026, dinh chinh lai cung ngay: pham vi
    #   la THEO DONG chu khong phai theo cot) ----
    # - Dong 1-6 (khoi tieu de bao cao): toan bo cot, size 13.
    # - Dong 7 (tieu de bang) den dong benh nhan cuoi cung + 1 dong nua (chinh
    #   la dong TONG CONG): toan bo cot, size 10.
    # - Cac dong SAU dong TONG CONG (thong ke xep loai, ghi chu, ky ten...):
    #   toan bo cot, size 13.
    def _resize(cell, size):
        f = cell.font
        cell.font = Font(name=f.name, size=size, bold=f.bold, italic=f.italic, color=f.color)

    max_row_final = max(ws.max_row, name_row)

    for r in range(1, 7):
        for c in range(1, n_cols_final + 1):
            _resize(ws.cell(row=r, column=c), 13)

    for r in range(7, tong_row + 1):
        for c in range(1, n_cols_final + 1):
            _resize(ws.cell(row=r, column=c), 10)

    for r in range(tong_row + 1, max_row_final + 1):
        for c in range(1, n_cols_final + 1):
            _resize(ws.cell(row=r, column=c), 13)

    # ---- in vua kho ngang A4: fit-to-width 1 trang, so dong tu chay xuong nhieu trang ----
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "7:8"
    ws.print_area = f"A1:{get_column_letter(n_cols_final)}{name_row}"

    wb.save(out_path)
    return out_path
