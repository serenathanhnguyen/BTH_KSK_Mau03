# -*- coding: utf-8 -*-
"""
pipeline.py
Ghep reader.py + transforms.py + cbc_rules.py + mapping.json/lab_reference.json
/cbc_reference.json thanh danh sach "ban ghi da xu ly" san sang dua vao
report.py. Day la lop nghiep vu trung tam - moi quy tac trong
Khung_nguyen_tac_BTH_KSK_Streamlit_v2.md nen duoc ap dung o day, KHONG
duoc rai rac trong app.py hay report.py.
"""
import json
import os

import transforms as T
import cbc_rules

PHANLOAI_SUFFIX = "_phanloai"
NAMED_LAB_KEYS = ["alt", "ast", "ure", "creatinin", "acid_uric", "glucose",
                  "cholesterol", "triglycerid", "hdl", "ldl"]

# Bang tra ma ICD-10 -> ten benh (Thong tu 06/2026/TT-BYT, Jo cung cap
# 30/09/2026) - nap 1 lan luc import module, dung cho build_icd_fallback().
_ICD_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icd_reminders.json")


def _load_icd_disease_map():
    try:
        with open(_ICD_MAP_PATH, encoding="utf-8") as f:
            return json.load(f).get("benh", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


ICD_DISEASE_MAP = _load_icd_disease_map()

_SOBO_SUFFIXES = ("_chandoansobo_icd", "_chuandoansobo_icd")
_XACDINH_SUFFIXES = ("_chandoanxacdinh_icd", "_chuandoanxacdinh_icd")


def _strip_suffix(kw, suffixes):
    for suf in suffixes:
        if kw.endswith(suf):
            return kw[: -len(suf)]
    return None


def _get_kw(row, keyword):
    if keyword is None:
        return None
    v = row.get(keyword)
    if isinstance(v, list):  # keyword trung (vd mat_docau_mt) - lay gia tri dau, da canh bao rieng o reader
        return v[0] if v else None
    return v


def _collect_phanloai(row):
    """Tra ve dict {prefix: gia_tri_int_hoac_None} cho MOI keyword ket thuc
    bang '_phanloai' co trong dong du lieu nay."""
    out = {}
    for kw, val in row.items():
        if isinstance(kw, str) and kw.endswith(PHANLOAI_SUFFIX):
            prefix = kw[: -len(PHANLOAI_SUFFIX)]
            v, _warn = T.to_int(val)
            out[prefix] = v
    return out


def build_icd_fallback(row, icd_map=None):
    """Phuong an du phong cuoi cho Ghi chu (CHI dung khi ca Ghi ro va Ket
    luan deu trong - da chot theo yeu cau Jo 30/09/2026, giu dung thu tu
    uu tien cu: Ghi ro > Ket luan > loi nhac ICD nay):
      - Cot *_chandoanxacdinh_icd (chan doan XAC DINH) co ma ICD khop duoc
        ten benh trong bang tra -> "đang bị bệnh <ten benh>".
      - Cot *_chandoansobo_icd (chan doan SO BO) co ma ICD khop duoc ten
        benh -> "theo dõi bệnh <ten benh>" (bo qua neu benh do da nam trong
        nhom "đang bị" o tren, tranh lap lai).
      - Ma ICD (o cot xac dinh) KHONG khop duoc benh nao trong bang tra van
        giu nguyen dinh dang cu "<chuyen khoa>: <ma>" de khong mat thong tin
        (phong truong hop bang tra ICD chua co ma do).
    Mot o co the co nhieu ma ICD cach nhau boi dau phay - xu ly tung ma."""
    if icd_map is None:
        icd_map = ICD_DISEASE_MAP

    dang_bi = {}   # ten_benh (khong dau hoa) -> True, theo thu tu gap
    theo_doi = {}
    raw_fallback_parts = []

    for kw, val in row.items():
        if not isinstance(kw, str) or val in (None, ""):
            continue

        specialty = _strip_suffix(kw, _XACDINH_SUFFIXES)
        if specialty is not None:
            unmatched_codes = []
            for code in str(val).split(","):
                code = code.strip()
                if not code:
                    continue
                name = T.icd_disease_name(code, icd_map)
                if name:
                    dang_bi.setdefault(name, True)
                else:
                    unmatched_codes.append(code)
            if unmatched_codes:
                raw_fallback_parts.append(f"{specialty}: {', '.join(unmatched_codes)}")
            continue

        specialty = _strip_suffix(kw, _SOBO_SUFFIXES)
        if specialty is not None:
            for code in str(val).split(","):
                code = code.strip()
                if not code:
                    continue
                name = T.icd_disease_name(code, icd_map)
                if name:
                    theo_doi.setdefault(name, True)

    parts = [f"đang bị bệnh {name}" for name in dang_bi]
    parts += [f"theo dõi bệnh {name}" for name in theo_doi if name not in dang_bi]
    parts += raw_fallback_parts
    return "; ".join(parts) if parts else None


def build_danhgia(row, icd_map=None):
    """Cot DANH GIA (them 30/09/2026) - PHIEN BAN NGAN GON cua Ghi chu, LUON
    tao truc tiep tu cac cot ma ICD cua TUNG chuyen khoa (khong phai chi
    dung khi Ghi ro/Ket luan trong nhu build_icd_fallback), vi chu bac si
    ghi tay o Ghi ro/Ket luan thuong qua chung chung (vd chi ghi "Răng hàm
    mặt." khong ro la sau rang hay mat rang) trong khi ma ICD phan biet
    duoc ro rang. Quy tac (chot voi Jo 30/09/2026):
      - Dung dung co che dang_bi/theo_doi nhu build_icd_fallback (chan doan
        XAC DINH -> "đang bị bệnh <ten>"; SO BO -> "theo dõi bệnh <ten>").
      - Bo hau to ", không xác định" trong ten benh cho ngan gon.
      - BO QUA hoan toan moi ma ICD thuoc CHUONG Z (Z00-Z99: "yeu to anh
        huong den tinh trang suc khoe va tiep xuc voi co so y te" trong
        ICD-10) - day la nhom ma HANH CHINH/TIEN SU/TINH TRANG SAU CAN
        THIEP, KHONG PHAI benh ly dang anh huong suc khoe, vi du: Z96.5
        (co mat implant/cau rang), Z98.x (tinh trang sau can thiep - vd
        sinh mo cu o San phu khoa)... Ap dung CHUNG cho MOI chuyen khoa
        (chot voi Jo 30/09/2026: "mat rang", "sinh mo" v.v. deu khong phai
        benh ly nen khong ghi vao Danh gia), khong rieng Rang Ham Mat.
      - Giu them rieng cum "mat rang" theo ten benh (phong truong hop ma
        khong thuoc chuong Z nhung van la mat rang).
        Ma ICD KHONG khop duoc ten benh trong bang tra thi bo qua (khac
        voi build_icd_fallback - o day khong giu ma tho, chi ghi ten benh
        ngan gon)."""
    if icd_map is None:
        icd_map = ICD_DISEASE_MAP

    dang_bi = {}
    theo_doi = {}

    def _resolve(code):
        if code.strip().upper().startswith("Z"):
            return None  # chuong Z: hanh chinh/tien su/tinh trang sau can thiep, khong phai benh ly
        name = T.icd_disease_name(code, icd_map)
        if not name:
            return None
        name = T.strip_khong_xac_dinh(name)
        if "mất răng" in name.lower():
            return None
        return name or None

    for kw, val in row.items():
        if not isinstance(kw, str) or val in (None, ""):
            continue

        specialty = _strip_suffix(kw, _XACDINH_SUFFIXES)
        if specialty is not None:
            for code in str(val).split(","):
                code = code.strip()
                if not code:
                    continue
                name = _resolve(code)
                if name:
                    dang_bi.setdefault(name, True)
            continue

        specialty = _strip_suffix(kw, _SOBO_SUFFIXES)
        if specialty is not None:
            for code in str(val).split(","):
                code = code.strip()
                if not code:
                    continue
                name = _resolve(code)
                if name:
                    theo_doi.setdefault(name, True)

    # (dinh chinh 30/09/2026: bo chu "bệnh" cho gon - "đang bị <ten>" / "theo dõi <ten>",
    # KHONG con "đang bị bệnh <ten>" / "theo dõi bệnh <ten>" nhu truoc)
    parts = [f"đang bị {name}" for name in dang_bi]
    parts += [f"theo dõi {name}" for name in theo_doi if name not in dang_bi]
    return "; ".join(parts) if parts else None


def process_row(row, index, manual_keyword_map, lab_ref, cbc_ref,
                 hb_source_unit, urine_enabled=True, icd_fallback_enabled=True):
    """Xu ly MOT dong du lieu tho -> 1 dict ban ghi day du, kem 'canhbao'
    (danh sach ly do dua vao cot Canh bao) va 'warnings' (loi/thieu du lieu
    de dua vao bang kiem tra tren giao dien)."""
    rec = {"stt": index}
    warnings = []
    canhbao_parts = []

    hoten, w = T.normalize_name(row.get("ho_ten"))
    hoten, _ = T.proper_case(hoten)  # Proper Case cho HỌ & TÊN (yeu cau Jo 30/09/2026)
    rec["hoten"] = hoten
    rec["ten"], w = T.last_given_name(row.get("ho_ten"))
    rec["cccd"], w = T.as_text_id(row.get("dinh_danh_ca_nhan"))
    if w: warnings.append(w)
    rec["ngaysinh"], w = T.parse_dob(row.get("ngay_sinh"))
    if w: warnings.append(w)
    rec["gioitinh"], w = T.gender_label(row.get("gioi_tinh"))
    rec["gioitinh"], _ = T.proper_case(rec["gioitinh"])  # Proper Case cho GIỚI TÍNH
    if w: warnings.append(w)
    rec["chieucao"], w = T.to_number(row.get("chieucao"))
    rec["cannang"], w = T.to_number(row.get("cannang"))
    rec["bmi"], w = T.compute_bmi(row.get("chieucao"), row.get("cannang"))
    rec["huyetap"], w = T.compose_huyetap(row.get("huyetaptamthu"), row.get("huyetaptamtruong"))

    # --- thi luc: 3 cap (khong kinh / kinh lo / co kinh), chon tong lon nhat ---
    pairs = [
        (row.get("mat_khongkinh_mp"), row.get("mat_khongkinh_mt")),
        (row.get("mat_kinhlo_mp"), row.get("mat_kinhlo_mt")),
        (row.get("mat_cokinh_mp"), row.get("mat_cokinh_mt")),
    ]
    (mp, mt), w = T.vision_pair(pairs)
    rec["matphai"], rec["mattrai"] = mp, mt

    # --- phan loai lam sang ---
    phanloai = _collect_phanloai(row)
    rec["noi"], w = T.noikhoa_max(phanloai)
    rec["ngoai"] = phanloai.get("ngoaikhoa")
    rec["dalieu"] = phanloai.get("dalieu")
    rec["sanphukhoa"], w = T.sanphukhoa_max(
        phanloai.get("sankhoa"), phanloai.get("phukhoa"),
        row.get("sankhoa_tuchoikham"), row.get("phukhoa_tuchoikham"),
        gioitinh=rec["gioitinh"],
    )
    rec["mat"] = phanloai.get("mat")
    rec["tmh"] = phanloai.get("tmh")
    rec["rhm"] = phanloai.get("rhm")
    rec["xeploai"], w = T.xeploai_max(phanloai)
    if rec["xeploai"] is not None:
        canhbao_parts.append(
            f"Xếp loại tự tính = max(tất cả *_phanloai) = {rec['xeploai']} — kiểm tra lại."
        )

    # --- danh gia (ten benh ngan gon tu ma ICD - luon tao, doc lap voi Ghi chu) ---
    rec["danhgia"] = build_danhgia(row)
    rec["danhgia"], _ = T.sentence_case(rec["danhgia"])  # chi hoa chu dau dong (yeu cau Jo 30/09/2026)

    # --- ghi chu (uu tien Ghi ro > Ket luan > ICD) ---
    icd_fallback = build_icd_fallback(row) if icd_fallback_enabled else None
    rec["ghichu"], w = T.ghichu_priority(row.get("de_nghi"), row.get("danh_muc_de_nghi"), icd_fallback)
    rec["ghichu"], _ = T.sentence_case(rec["ghichu"])  # chi hoa chu dau dong, khong con Proper Case (dinh chinh 30/09/2026)
    if w:
        canhbao_parts.append(w)

    # --- CTM (Hb/MCV/WBC/PLT) ---
    ctm_text, ctm_status, ctm_detail = cbc_rules.evaluate_ctm(
        {
            "hb": row.get("kskdk_xnm_huyetsacto"),
            "mcv": row.get("kskdk_xnm_mcv"),
            "wbc": row.get("kskdk_xnm_slbc"),
            "plt": row.get("kskdk_xnm_sltc"),
        },
        rec["gioitinh"], cbc_ref, hb_source_unit=hb_source_unit,
    )
    rec["ctm"] = ctm_text  # da rut gon con "bt" / "x" / "" (30/09/2026) - chi tiet nam trong Canh bao
    rec["ctm_status"] = ctm_status
    if ctm_status == "bat_thuong":
        canhbao_parts.append("CTM ngoài tham chiếu: " + "; ".join(ctm_detail))
    elif ctm_status == "bt" and ctm_detail:
        canhbao_parts.append(
            "CTM ghi 'bt' nhưng một số chỉ số chưa đủ dữ liệu/ngưỡng để đánh giá — "
            + "; ".join(ctm_detail)
        )

    # --- cac chi so sinh hoa mau (bold = cao hon tren, italic = thap hon duoi) ---
    lab_values = {}
    for key in NAMED_LAB_KEYS:
        keyword = manual_keyword_map.get(key)
        raw = row.get(keyword) if keyword else None
        v, _w = T.to_number(raw)
        ref = lab_ref["mau"].get(key)
        bold = italic = False
        if v is not None and ref is not None:
            bold = v > ref["tren"]
            italic = v < ref["duoi"]
            if (bold or italic) and ref.get("can_xac_nhan"):
                canhbao_parts.append(
                    f"{key}={v}: ngưỡng tham chiếu CHƯA được Jo xác nhận lại — kiểm tra kỹ trước khi dùng."
                )
        lab_values[key] = {"value": v, "bold": bold, "italic": italic}
    rec["lab"] = lab_values

    # --- nuoc tieu (tuy chon) ---
    if urine_enabled:
        flag, issues, w = T.urine_flag(
            row.get("kskdk_xnnt_titrong"), row.get("kskdk_xnnt_ph"), lab_ref["nuoc_tieu"]
        )
        rec["nt"] = flag
        if issues:
            canhbao_parts.append("Nước tiểu ngoài tham chiếu: " + "; ".join(issues))
        if w:
            warnings.append(w)
    else:
        rec["nt"] = None

    # --- sieu am / x-quang: giu nguyen van (co the anh xa thu cong o Muc 3 -
    # neu khong chon gi thi dung lai keyword goc cua Mau 03 chuan, khong doi
    # hanh vi cu - yeu cau Jo 30/09/2026) ---
    rec["satq"], _ = T.verbatim(row.get(manual_keyword_map.get("satq")) if manual_keyword_map.get("satq") else None)
    satv_kw = manual_keyword_map.get("satv") or "sieu_am_2_tuyen_vu"
    rec["satv"], _ = T.verbatim(row.get(satv_kw))
    xq_kw = manual_keyword_map.get("xq") or "xq"
    rec["xq"], _ = T.xquang_flag(row.get(xq_kw))

    rec["canhbao"] = " | ".join(canhbao_parts)
    rec["warnings"] = warnings
    rec["_excel_row"] = row.get("_excel_row")
    return rec


def process_all(reader_result, manual_keyword_map, lab_ref, cbc_ref,
                 hb_source_unit, urine_enabled=True, icd_fallback_enabled=True,
                 sort_by_ten=False):
    records = []
    for i, row in enumerate(reader_result.rows, start=1):
        records.append(process_row(
            row, i, manual_keyword_map, lab_ref, cbc_ref,
            hb_source_unit, urine_enabled, icd_fallback_enabled,
        ))
    if sort_by_ten:
        records.sort(key=lambda r: T.vi_sort_key(r.get("ten") or ""))
        for i, r in enumerate(records, start=1):
            r["stt"] = i
    return records


def column_availability(records):
    """Cho biet cot cau lam sang nao THUC SU co du lieu trong toan bo tap
    du lieu dang xu ly - dung cho enabled_default == 'auto' (muc 1: bo cot
    khong co du lieu, tru khi nguoi dung yeu cau giu)."""
    avail = {}
    for key in NAMED_LAB_KEYS:
        col_id = {"alt": "alt", "ast": "ast", "ure": "ure", "creatinin": "cre",
                  "acid_uric": "aciduric", "glucose": "glu", "cholesterol": "cho",
                  "triglycerid": "tri", "hdl": "hdl", "ldl": "ldl"}[key]
        avail[col_id] = any(r["lab"][key]["value"] is not None for r in records)
    avail["nt"] = any(r.get("nt") is not None for r in records)
    avail["satq"] = any(r.get("satq") for r in records)
    avail["satv"] = any(r.get("satv") for r in records)
    avail["xq"] = any(r.get("xq") for r in records)
    avail["ctm"] = any(r.get("ctm") not in (None, "") for r in records)
    return avail
