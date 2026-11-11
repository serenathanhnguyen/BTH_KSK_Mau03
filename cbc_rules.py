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

ORDER = ["hb", "rbc", "mcv", "wbc", "plt"]
LABELS = {
    "hb": ("Hb giảm", "Hb tăng"),
    "rbc": ("Hồng cầu giảm", "Hồng cầu tăng"),
    "mcv": ("MCV thấp", "MCV cao"),
    "wbc": ("Bạch cầu giảm", "Bạch cầu tăng"),
    "plt": ("Tiểu cầu giảm", "Tiểu cầu tăng"),
}

# He so quy doi ve g/dL (chuan noi bo cua bang tham chieu Hb trong cbc_reference.json)
_HB_UNIT_TO_GDL = {"g/dL": 1.0, "g/L": 0.1}

# Nguong RIENG (g/L, theo gioi tinh) de xac dinh co ghi "Theo dõi thiếu máu"
# vao cot DANH GIA hay khong - KHAC voi nguong.hb (dung cho Canh bao CTM
# "Hb giảm/tăng"). Doc tu cbc_reference.json["thieu_mau_hb"] - yeu cau Jo
# 01/10/2026: "Nam: Hb <130 g/L; Nữ: Hb <120 g/L -> Theo dõi thiếu máu".
def _anemia_flag(hb_gdl, gioitinh, ref_cfg):
    if hb_gdl is None:
        return False
    cfg = ref_cfg.get("thieu_mau_hb")
    if not cfg:
        return False
    nhom = "nam" if gioitinh == "Nam" else ("nu" if gioitinh == "Nữ" else None)
    if nhom is None:
        return False
    nguong_gl = cfg["nhom"].get(nhom)
    if nguong_gl is None:
        return False
    return (hb_gdl * 10.0) < nguong_gl


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

    Rut gon theo yeu cau Jo 30/09/2026: cot T chi con 3 trang thai hien thi -
    "bt" (tat ca chi so DOC DUOC deu trong nguong), "x" (co it nhat 1 chi so
    doc duoc nam ngoai nguong), hoac de TRONG (khong chi so nao doc/danh gia
    duoc). Chi tiet tung chi so bat thuong/thieu du lieu van duoc tra ve
    (chi_tiet) de pipeline dua vao Canh bao cho nguoi phu trach ra soat.

    Tra ve: (text, status, chi_tiet, abnormal_map, thieu_mau)
      text in {"", "bt", "x"}
      status in {'trong', 'bt', 'bat_thuong'}
      chi_tiet: list mo ta (chi so bat thuong + chi so thieu du lieu/nguong)
      abnormal_map: dict {chiso: 'thap'/'cao'} CHI gom cac chi so DOC DUOC
        va NGOAI nguong (them 30/09/2026 dot 3, de pipeline.py dua vao cot
        DANH GIA voi ten/cach ghi rieng, khac voi chi_tiet dung cho Canh bao)
      thieu_mau: bool - True neu Hb (quy doi g/L) thap hon nguong rieng
        theo gioi tinh trong cbc_reference.json["thieu_mau_hb"] (them
        01/10/2026, xem _anemia_flag) - DOC LAP voi abnormal_map["hb"]
        (nguong khac nhau, hai muc dich khac nhau - xem ghi chu trong
        cbc_reference.json).
    """
    if hb_source_unit is None:
        hb_source_unit = ref_cfg.get("don_vi_nguon_m03_mac_dinh", {}).get("hb", "g/dL")

    resolved = {}   # chiso -> (gia_tri_da_quy_doi, ket_qua 'thap'/'binh_thuong'/'cao', ly_do_loi_neu_co)
    for chiso in ORDER:
        raw = raw_values.get(chiso)
        val, warn = to_number(raw)
        if val is None:
            resolved[chiso] = (None, None, warn or "Không có dữ liệu")
            continue

        if chiso == "hb":
            factor = _HB_UNIT_TO_GDL.get(hb_source_unit)
            if factor is None:
                resolved[chiso] = (None, None, f"Đơn vị Hb không nhận dạng: {hb_source_unit}")
                continue
            val = val * factor

        th, _unit = _resolve_threshold(chiso, gioitinh, ref_cfg)
        if th is None:
            resolved[chiso] = (val, None, f"Chưa có ngưỡng tham chiếu đã duyệt cho {chiso} (nhóm {gioitinh}).")
            continue

        if val < th["duoi"]:
            resolved[chiso] = (val, "thap", None)
        elif val > th["tren"]:
            resolved[chiso] = (val, "cao", None)
        else:
            resolved[chiso] = (val, "binh_thuong", None)

    # Hb (da quy doi ve g/dL trong resolved, neu doc/quy doi duoc) -> tinh co
    # thieu mau theo nguong rieng g/L khong, DOC LAP voi nguong.hb o tren
    hb_gdl = resolved["hb"][0]
    thieu_mau = _anemia_flag(hb_gdl, gioitinh, ref_cfg)

    missing = [c for c in ORDER if resolved[c][1] is None]
    chi_tiet = [f"{c}: {resolved[c][2]}" for c in missing]

    available = [c for c in ORDER if resolved[c][1] is not None]

    # Khong chi so nao doc/danh gia duoc -> de trong (giu nguyen o trong)
    if not available:
        return "", "trong", chi_tiet, {}, thieu_mau

    # Co it nhat 1 chi so (trong so cac chi so doc duoc) ngoai nguong -> "x"
    abnormal = [c for c in available if resolved[c][1] in ("thap", "cao")]
    if abnormal:
        abnormal_map = {c: resolved[c][1] for c in abnormal}
        chi_tiet = [
            (LABELS[c][0] if resolved[c][1] == "thap" else LABELS[c][1]) for c in abnormal
        ] + chi_tiet
        return "x", "bat_thuong", chi_tiet, abnormal_map, thieu_mau

    # Tat ca chi so doc duoc deu trong nguong -> "bt"
    return "bt", "bt", chi_tiet, {}, thieu_mau


def assess_anemia_qd1613(raw_hb, raw_rbc, ref_cfg, hb_source_unit=None):
    """
    Danh gia thieu mau NANG theo QD 1613/BYT-QD, chi tieu 50.5 (huong dan
    muc 14): hong cau < 3 trieu (3.0 T/L) VA huyet sac to < 10 g/100ml
    (10 g/dL). Bang phan loai danh dau loai III-IV.

    Tra ve:
      "nang"           - dat CA HAI tieu chi -> thieu mau nang (50.5)
      "thieu_rbc"      - Hb < 10 g/dL nhung KHONG co so lieu hong cau ->
                         chua du can cu ket luan theo 50.5
      None             - khong dat tieu chi (hoac thieu Hb / thieu cau hinh)
    QD 1613 khong co nguong cho thieu mau nhe/vua - truong hop do van di theo
    nhanh 'Theo doi thieu mau' (thieu_mau_hb) co san.
    """
    cfg = (ref_cfg or {}).get("thieu_mau_qd1613")
    if not cfg:
        return None
    if hb_source_unit is None:
        hb_source_unit = ref_cfg.get("don_vi_nguon_m03_mac_dinh", {}).get("hb", "g/dL")
    factor = _HB_UNIT_TO_GDL.get(hb_source_unit)
    hb, _ = to_number(raw_hb)
    if hb is None or factor is None:
        return None
    if hb * factor >= cfg["hb_duoi_gdl"]:
        return None
    rbc, _ = to_number(raw_rbc)
    if rbc is None:
        return "thieu_rbc"
    return "nang" if rbc < cfg["rbc_duoi_tl"] else None


ANEMIA_1832_LABELS = {
    "nhe": "Thiếu máu nhẹ",
    "vua": "Thiếu máu vừa",
    "nang": "Thiếu máu nặng",
    "rat_nang": "Thiếu máu rất nặng",
}

def assess_anemia_qd1832(raw_hb, gioitinh, ref_cfg, hb_source_unit=None):
    """
    Danh gia thieu mau (cap nhat 11/11/2026 theo yeu cau Jo): Hb (g/L) < nguong
    tham chieu duoi tren phieu xet nghiem (nguong.hb trong cbc_reference.json,
    hien 11.0 g/dL = 110 g/L) -> THIEU MAU, muc do theo QD 1832/QD-BYT (2022):
    nhe >= 90, vua 60-<90, nang 30-<60, rat nang < 30 g/L.
    Hb >= nguong phieu -> None (KHONG ghi "Theo doi thieu mau").

    Tra ve "nhe" / "vua" / "nang" / "rat_nang" hoac None (khong thieu mau,
    thieu Hb, gioi tinh khong xac dinh, hoac thieu cau hinh).
    """
    cfg = (ref_cfg or {}).get("thieu_mau_qd1832")
    hb_ref = ((ref_cfg or {}).get("nguong") or {}).get("hb")
    if not cfg or not hb_ref:
        return None
    if gioitinh not in ("Nam", "Nữ"):
        return None
    th_phieu = hb_ref["nhom"].get(_hb_group(gioitinh))
    if th_phieu is None:
        return None
    phieu_gl = th_phieu["duoi"] * (10.0 if hb_ref.get("don_vi") == "g/dL" else 1.0)
    if hb_source_unit is None:
        hb_source_unit = ref_cfg.get("don_vi_nguon_m03_mac_dinh", {}).get("hb", "g/dL")
    factor = _HB_UNIT_TO_GDL.get(hb_source_unit)
    hb, _ = to_number(raw_hb)
    if hb is None or factor is None:
        return None
    hb_gl = hb * factor * 10.0
    if hb_gl >= phieu_gl:
        return None
    md = cfg["muc_do_hb_gl"]
    if hb_gl >= md["nhe_tu"]:
        return "nhe"
    if hb_gl >= md["vua_tu"]:
        return "vua"
    if hb_gl >= md["nang_tu"]:
        return "nang"
    return "rat_nang"
