# -*- coding: utf-8 -*-
"""
transforms.py
Cac ham chuan hoa / suy luan tu du lieu tho M03 sang gia tri hien thi trong
Bang Tong Hop (BTH). Moi ham deu duoc chu thich ro quy tac ap dung, tham
chieu toi muc tuong ung trong Khung_nguyen_tac_BTH_KSK_Streamlit_v2.md va
trong khung-mau-bang-tong-hop-suc-khoe.md (project memory) khi hai tai lieu
trung khop.

NGUYEN TAC CHUNG (rat quan trong, xem muc 4.7 cua khung nguyen tac):
  Khong tu suy luan "binh thuong", "bt", "x", benh hay chi dinh chuyen khoa
  tu MOT chi so don le ngoai pham vi da duoc dinh nghia ro trong file cau
  hinh (lab_reference.json / cbc_reference.json). Moi gia tri khong the xac
  dinh chac chan phai tra ve None (o trong) kem canh bao, khong duoc doan.
"""
import re
import unicodedata
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Chuoi / ten
# ---------------------------------------------------------------------------

def normalize_name(raw, **kw):
    if raw is None:
        return None, None
    s = " ".join(str(raw).strip().split())
    return (s if s else None), None


def last_given_name(raw, **kw):
    """Cot TEN = tu cuoi cung cua ho ten, sau khi chuan hoa khoang trang.
    Vi du 'NGUYEN THI ANH' -> 'ANH'. Xem muc 2, hang 'ten' trong khung nguyen tac."""
    name, _ = normalize_name(raw)
    if not name:
        return None, None
    return name.split()[-1], None


def as_text_id(raw, **kw):
    """CCCD phai doc nhu chuoi, giu so 0 dau. Neu nguon da la so (mat so 0),
    gan co canh bao de doi soat - khong tu them so 0 (muc 1)."""
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, (int, float)):
        s = str(int(raw))
        return s, f"CCCD doc duoc dang so ({s}) - co the da mat so 0 dau, can doi soat thu cong."
    return str(raw).strip(), None


def parse_dob(raw, **kw):
    """Nhan Excel date hoac chuoi dd/MM/yyyy. Khong phan tich duoc -> None + canh bao."""
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, (datetime, date)):
        return raw.strftime("%d/%m/%Y"), None
    s = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y"), None
        except ValueError:
            continue
    return None, f"Khong nhan dang duoc ngay sinh '{s}' - de trong, can nhap tay."


GENDER_MAP = {"1": "Nam", "2": "Nữ", "3": "Chưa xác định"}


def gender_label(raw, **kw):
    if raw is None or raw == "":
        return None, None
    key = str(raw).strip().split(".")[0]
    label = GENDER_MAP.get(key)
    if label is None:
        return None, f"Ma gioi tinh khong xac dinh: '{raw}'."
    return label, None


def to_number(raw, **kw):
    if raw is None or raw == "":
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    s = str(raw).strip().replace(",", ".")
    try:
        return float(s), None
    except ValueError:
        return None, f"Gia tri so khong hop le: '{raw}'."


def to_int(raw, **kw):
    v, warn = to_number(raw)
    if v is None:
        return None, warn
    if v != int(v):
        return None, f"Gia tri phan loai khong phai so nguyen 1-5: '{raw}'."
    iv = int(v)
    if iv not in (1, 2, 3, 4, 5):
        return None, f"Gia tri phan loai ngoai 1-5: '{raw}'."
    return iv, None


def compute_bmi(chieucao_cm, cannang_kg, decimals=2, **kw):
    """BMI = can nang(kg) / (chieu cao(m))^2. Chi tinh khi ca hai la so hop le va G>0."""
    h, hw = to_number(chieucao_cm)
    w, ww = to_number(cannang_kg)
    if h is None or w is None or h <= 0:
        return None, "Thieu du lieu chieu cao/can nang hop le de tinh BMI."
    bmi = w / ((h / 100.0) ** 2)
    return round(bmi, decimals), None


def compose_huyetap(tt, ttr, **kw):
    a, wa = to_number(tt)
    b, wb = to_number(ttr)
    if a is None or b is None:
        return None, "Thieu huyet ap tam thu hoac tam truong - de trong."
    return f"{int(a)}/{int(b)}", None


# ---------------------------------------------------------------------------
# Thi luc (muc 6 - "chon cap co tong lon nhat")
# ---------------------------------------------------------------------------

def vision_pair(pairs_mp_mt, **kw):
    """pairs_mp_mt: list [(mp_raw, mt_raw), ...] cho 3 kieu (khong kinh/kinh lo/co kinh).
    Chon cap co TONG (mp+mt) LON NHAT trong cac cap co it nhat 1 gia tri.
    Tra ve (mp, mt) cua cap duoc chon, ap dung dong nhat cho ca cot P va T."""
    best = None
    best_sum = -1
    for mp_raw, mt_raw in pairs_mp_mt:
        mp, _ = to_number(mp_raw)
        mt, _ = to_number(mt_raw)
        if mp is None and mt is None:
            continue
        s = (mp or 0) + (mt or 0)
        if s > best_sum:
            best_sum = s
            best = (mp, mt)
    if best is None:
        return (None, None), None
    mp, mt = best
    mp = int(mp) if mp is not None and mp == int(mp) else mp
    mt = int(mt) if mt is not None and mt == int(mt) else mt
    return (mp, mt), None


# ---------------------------------------------------------------------------
# Phan loai lam sang (muc 6: "Noi khoa" = cum con lai ngoai 7 chuyen khoa rieng;
# "Xep loai" = max toan bo cac *_phanloai, tru theluc_phanloai)
# ---------------------------------------------------------------------------

NAMED_SPECIALTY_PREFIXES = {
    "ngoaikhoa", "dalieu", "sankhoa", "phukhoa", "mat", "tmh", "rhm",
}
EXCLUDED_PHANLOAI_PREFIXES = {"theluc"}


def noikhoa_max(all_phanloai, **kw):
    """all_phanloai: dict {prefix: value_or_None} cho MOI cot *_phanloai doc duoc.
    Noi = max cua cac nhom KHONG thuoc 7 chuyen khoa rieng (Ngoai/Da lieu/San/
    Phu/Mat/TMH/RHM) va khong nam trong EXCLUDED_PHANLOAI_PREFIXES."""
    vals = [
        v for prefix, v in all_phanloai.items()
        if prefix not in NAMED_SPECIALTY_PREFIXES
        and prefix not in EXCLUDED_PHANLOAI_PREFIXES
        and v is not None
    ]
    if not vals:
        return None, None
    return max(vals), None


def sanphukhoa_max(sankhoa_phanloai, phukhoa_phanloai, sankhoa_tuchoi, phukhoa_tuchoi,
                    gioitinh=None, **kw):
    """Sanphukhoa = max(san khoa, phu khoa). 'Tu choi kham' la trang thai rieng,
    KHONG duoc gop nhu mot muc phan loai (khong ghi 'X' nhu phan loai)."""
    if gioitinh == "Nam":
        return None, None
    vals = [v for v in (sankhoa_phanloai, phukhoa_phanloai) if v is not None]
    tuchoi = bool(sankhoa_tuchoi) or bool(phukhoa_tuchoi)
    if not vals:
        if tuchoi:
            return "Từ chối khám", None
        return None, None
    return max(vals), None


def xeploai_max(all_phanloai, **kw):
    """Xep loai tong = max cua TAT CA cac cot *_phanloai doc duoc (tru
    theluc_phanloai neu co) - dung truc tiep tren du lieu tho, khong phu
    thuoc viec cac cot bao cao M-S co duoc bat hay khong."""
    vals = [
        v for prefix, v in all_phanloai.items()
        if prefix not in EXCLUDED_PHANLOAI_PREFIXES and v is not None
    ]
    if not vals:
        return None, None
    return max(vals), None


# ---------------------------------------------------------------------------
# Ghi chu (da duoc Jo chot trong phien lam viec: uu tien Ghi ro > Ket luan > ICD)
# ---------------------------------------------------------------------------

def ghichu_priority(ghiro, ketluan, icd_fallback_text=None, **kw):
    """Thu tu uu tien: 1) 'Ghi ro' (keyword de_nghi - FW trong file mau) neu
    co noi dung -> dung nguyen van. 2) Neu trong: 'Ket luan' (danh_muc_de_nghi).
    3) Neu ca hai trong: ghep ICD tu cac chuyen khoa (phuong an du phong cuoi).
    Day la quy tac Jo da chot rieng cho du an nay, uu tien hon phan 'Trong'
    trong khung nguyen tac chung."""
    g = (str(ghiro).strip() if ghiro not in (None, "") else "")
    k = (str(ketluan).strip() if ketluan not in (None, "") else "")
    if g:
        return g, None
    if k:
        return k, None
    if icd_fallback_text:
        return icd_fallback_text, "Ghi chu lay tu ICD (khong co Ghi ro/Ket luan trong du lieu goc)."
    return "", None


# ---------------------------------------------------------------------------
# Nuoc tieu (tuy chon, mac dinh BAT theo thuc te du an da lam - co the tat
# trong cau hinh neu tram muon de trong hoan toan nhu khung nguyen tac goc)
# ---------------------------------------------------------------------------

def urine_flag(titrong_raw, ph_raw, ref_nuoc_tieu, **kw):
    issues = []
    tt, _ = to_number(titrong_raw)
    ph, _ = to_number(ph_raw)
    if tt is not None:
        lo, hi = ref_nuoc_tieu["titrong"]["duoi"], ref_nuoc_tieu["titrong"]["tren"]
        if tt < lo or tt > hi:
            issues.append(f"Tỉ trọng={tt} (tk {lo}-{hi})")
    if ph is not None:
        lo, hi = ref_nuoc_tieu["ph"]["duoi"], ref_nuoc_tieu["ph"]["tren"]
        if ph < lo or ph > hi:
            issues.append(f"pH={ph} (tk {lo}-{hi})")
    if tt is None and ph is None:
        return None, None, "Khong co du lieu ti trong/pH de danh gia nuoc tieu."
    flag = "x" if issues else "bt"
    return flag, issues, None


def verbatim(raw, **kw):
    if raw is None or raw == "":
        return None, None
    return str(raw).strip(), None


# ---------------------------------------------------------------------------
# Sap xep tieng Viet (QUY TAC QUAN TRONG 6 trong khung-mau-bang-tong-hop-suc-khoe.md)
# ---------------------------------------------------------------------------

_VOWEL_BASE_ORDER = "aăâbcdđeêghiklmnoôơpqrstuưvxy"
_TONE_ORDER = {"": 0, "̀": 1, "̉": 2, "̃": 3, "́": 4, "̣": 5}


def _char_sort_key(ch):
    nfd = unicodedata.normalize("NFD", ch)
    base = nfd[0]
    tone = "".join(c for c in nfd[1:] if unicodedata.category(c) == "Mn" and c in _TONE_ORDER)
    # dinh danh chu (breve/circumflex/horn) can duoc giu lai trong base khi so sanh
    base_full = unicodedata.normalize("NFC", nfd[0] + "".join(
        c for c in nfd[1:] if c not in _TONE_ORDER
    ))
    try:
        base_rank = _VOWEL_BASE_ORDER.index(base_full.lower())
    except ValueError:
        base_rank = len(_VOWEL_BASE_ORDER) + ord(base_full.lower())
    tone_rank = _TONE_ORDER.get(tone, 0)
    return (base_rank, tone_rank)


def vi_sort_key(s):
    if not s:
        return ()
    return tuple(_char_sort_key(ch) for ch in s.lower())
