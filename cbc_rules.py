# -*- coding: utf-8 -*-
"""
cbc_rules.py
Sinh nhan xet mo ta cho cot T (Tong phan tich te bao mau) tu 4 chi so
Hb, MCV, WBC, PLT - dung QUY TAC muc 3 cua
Khung_nguyen_tac_BTH_KSK_Streamlit_v2.md.

QUAN TRONG - pham vi cho phep (da chot 29/09/2026):
  - Chi mo ta trang thai chi so (thap/binh thuong/cao), KHONG tu ket luan
    thieu mau, viem, nhiem trung hay bat ky benh ly huyet hoc nao.
  - Nguoi phu trach chuyen mon PHAI kiem tra nhan xet truoc khi dung chinh
    thuc (giao dien Streamlit cho xem truoc va sua tay - xem app.py).
"""
from transforms import to_number

ORDER = ["hb", "mcv", "wbc", "plt"]
LABELS = {
    "hb": ("Hb giảm", "Hb tăng"),
    "mcv": ("MCV thấp", "MCV cao"),
    "wbc": ("Bạch cầu giảm", "Bạch cầu tăng"),
    "plt": ("Tiểu cầu giảm", "Tiểu cầu tăng"),
}

# He so quy doi ve g/dL (chuan noi bo cua bang tham chieu Hb trong cbc_reference.json)
_HB_UNIT_TO_GDL = {"g/dL": 1.0, "g/L": 0.1}


def _hb_group(gioitinh):
    if gioitinh == "Nam":
        return "nam"
    if gioitinh == "Nữ":
        return "nu_khong_thai"
    return "khac"


def _resolve_threshold(chiso, gioitinh, ref_cfg):
    if chiso == "hb":
        nhom = _hb_group(gioitinh)
        th = ref_cfg["nguong"]["hb"]["nhom"].get(nhom)
        return th, ref_cfg["nguong"]["hb"]["don_vi"]
    th = ref_cfg["nguong"][chiso]["nhom"]["mac_dinh"]
    return th, ref_cfg["nguong"][chiso]["don_vi"]


def evaluate_ctm(raw_values, gioitinh, ref_cfg, hb_source_unit=None):
    """
    raw_values: dict {'hb':.., 'mcv':.., 'wbc':.., 'plt':..} - gia tri THO
                (chuoi/so) doc truc tiep tu file M03, chua chuyen doi.
    gioitinh:   'Nam' / 'Nữ' / None - de chon nhom nguong Hb.
    ref_cfg:    noi dung cbc_reference.json (da load).
    hb_source_unit: don vi THUC TE cua cot Hb trong file dang xu ly
                ('g/dL' hoac 'g/L'), do nguoi dung khai bao tren giao dien -
                KHONG tu doan theo do lon con so (muc 3.1).

    Tra ve: (text, status, chi_tiet)
      status in {'bt', 'bat_thuong', 'thieu_du_lieu', 'trong'}
      chi_tiet: list cac ly do thieu du lieu (de dua vao bang kiem tra)
    """
    if hb_source_unit is None:
        hb_source_unit = ref_cfg.get("don_vi_nguon_m03_mac_dinh", {}).get("hb", "g/dL")

    resolved = {}   # chiso -> (gia_tri_da_quy_doi, ket_qua 'thap'/'binh_thuong'/'cao', ly_do_loi_neu_co)
    for chiso in ORDER:
        raw = raw_values.get(chiso)
        val, warn = to_number(raw)
        if val is None:
            resolved[chiso] = (None, None, warn or "Khong co du lieu")
            continue

        if chiso == "hb":
            factor = _HB_UNIT_TO_GDL.get(hb_source_unit)
            if factor is None:
                resolved[chiso] = (None, None, f"Don vi Hb khong nhan dang: {hb_source_unit}")
                continue
            val = val * factor

        th, _unit = _resolve_threshold(chiso, gioitinh, ref_cfg)
        if th is None:
            resolved[chiso] = (val, None, f"Chua co nguong tham chieu da duyet cho {chiso} (nhom {gioitinh}).")
            continue

        if val < th["duoi"]:
            resolved[chiso] = (val, "thap", None)
        elif val > th["tren"]:
            resolved[chiso] = (val, "cao", None)
        else:
            resolved[chiso] = (val, "binh_thuong", None)

    missing = [c for c in ORDER if resolved[c][1] is None]
    chi_tiet = [f"{c}: {resolved[c][2]}" for c in missing]

    # Rule 4: ca bon chi so deu khong danh gia duoc -> de trong
    if len(missing) == len(ORDER):
        return "", "trong", chi_tiet

    # Rule 3: thieu du lieu/nguong/don vi o BAT KY chi so nao -> khong ghep
    # ket qua mot phan, tra ve thong bao chung (an toan hon la bao cao thieu)
    if missing:
        return "Chưa đủ dữ liệu đánh giá", "thieu_du_lieu", chi_tiet

    # Rule 2: du ca bon va tat ca binh thuong -> bt
    if all(resolved[c][1] == "binh_thuong" for c in ORDER):
        return "bt", "bt", []

    # Rule 1: ghep cac chi so bat thuong theo dung thu tu Hb -> MCV -> WBC -> PLT
    parts = []
    for c in ORDER:
        _, ket_qua, _ = resolved[c]
        if ket_qua == "thap":
            parts.append(LABELS[c][0])
        elif ket_qua == "cao":
            parts.append(LABELS[c][1])
    return "; ".join(parts), "bat_thuong", []
