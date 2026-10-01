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


def huyetap_cao(tt, ttr, **kw):
    """Nguong tang huyet ap o NGUOI TRUONG THANH khi do tai co so y te (yeu
    cau Jo 30/09/2026): tam thu >= 140 mmHg HOAC tam truong >= 90 mmHg.
    Tra ve True/False de report.py to do o mmc Huyet ap; None neu thieu du
    lieu (khong danh gia duoc, KHONG mac dinh la False)."""
    a, _ = to_number(tt)
    b, _ = to_number(ttr)
    if a is None or b is None:
        return None, None
    return (a >= 140 or b >= 90), None


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


# Cac chi so ĐỊNH TÍNH khac cua Tong phan tich nuoc tieu (ngoai Ti trong/pH da
# co o urine_flag) - trong M03 thuc te (kskdk_xnnt_*) la CAC O SO (thang do
# dai/ban dinh luong cua que thu nuoc tieu, vd Protein 15/30/100/300,
# Glucose 100/1000, Bach cau 500...): quy uoc chung cua que thu la 0/rong =
# Am tinh (binh thuong), BAT KY gia tri KHAC 0 nao = Duong tinh (bat thuong)
# - dung de dua vao cot DANH GIA khi co gia tri duong tinh (yeu cau Jo
# 30/09/2026 dot 3: "Nitrit dương tính,..."). "kskdk_xnnt_khac" la o ghi chu
# tu do, KHONG phai chi so dinh tinh nen khong dua vao day.
URINE_QUALITATIVE_LABELS = {
    "bachcau": "Bạch cầu",
    "bilirubin": "Bilirubin",
    "cetonic": "Cetonic",
    "glucose": "Glucose",
    "hongcau": "Hồng cầu",
    "nitrit": "Nitrit",
    "protein": "Protein",
    "urobilinogen": "Urobilinogen",
}

_AM_TINH_TEXTS = {"ÂM TÍNH", "AM TINH", "NEGATIVE", "NEG", "-", "0", "KHÔNG"}


def urine_positive_findings(row, **kw):
    """Quet cac chi so DINH TINH cua Tong phan tich nuoc tieu (xem
    URINE_QUALITATIVE_LABELS) trong 1 dong du lieu tho, tra ve danh sach cac
    chuoi "{Ten chi so} [niệu] dương tính" cho nhung chi so co gia tri DUONG
    TINH (so khac 0, hoac van ban khong phai mot trong cac cach ghi "am
    tinh" da biet). Dung de dua vao cot DANH GIA - yeu cau Jo 30/09/2026 dot
    3, them "[niệu]" theo yeu cau Jo 01/10/2026 dot 3 de phan biet voi cac
    chi so cung ten trong mau (vd "Bạch cầu tăng"/"Hồng cầu tăng" cua CTM)."""
    findings = []
    for suffix, label in URINE_QUALITATIVE_LABELS.items():
        raw = row.get(f"kskdk_xnnt_{suffix}")
        if raw is None or str(raw).strip() == "":
            continue
        val, _ = to_number(raw)
        if val is not None:
            if val != 0:
                findings.append(f"{label} [niệu] dương tính")
            continue
        text = _normalize_ws_upper(raw)
        if text not in _AM_TINH_TEXTS:
            findings.append(f"{label} [niệu] dương tính")
    return findings


_ICD_STRIP_RE = re.compile(r"[^A-Z0-9.]")


def _normalize_icd_code(raw):
    if raw is None:
        return None
    s = _ICD_STRIP_RE.sub("", str(raw).strip().upper())
    return s or None


def icd_disease_name(raw_code, icd_map):
    """Tra ten benh (tieng Viet, da bo tien to 'Bệnh ' va viet thuong chu
    dau) tu 1 ma ICD, dung bang tra icd_reminders.json (Thong tu 06/2026).
    Khop CHINH XAC truoc; neu khong thay, thu khop theo 3 ky tu dau (nhom
    benh). Tra ve None neu khong khop duoc ma nao trong bang."""
    code = _normalize_icd_code(raw_code)
    if not code or not icd_map:
        return None
    name = icd_map.get(code)
    if name is None and len(code) > 3:
        name = icd_map.get(code[:3])
    if name is None:
        return None
    name = name.strip()
    if name.lower().startswith("bệnh "):
        name = name[len("bệnh "):]
    if name:
        name = name[0].lower() + name[1:]
    return name or None


def proper_case(raw, **kw):
    """Chuyen text ve dang 'Proper Case' (moi tu viet hoa chu cai dau, cac
    chu con lai giu nguyen dang thuong cua tu do) - ap dung cho Ho & Ten,
    Gioi tinh theo yeu cau Jo 30/09/2026. Giu nguyen None/chuoi rong."""
    if raw is None:
        return None, None
    s = str(raw)
    if s.strip() == "":
        return s, None
    words = s.split()
    return " ".join(w.capitalize() for w in words), None


def sentence_case(raw, **kw):
    """Chi viet hoa CHU CAI DAU TIEN cua dong, giu nguyen phan con lai -
    ap dung cho GHI CHU va DANH GIA (dinh chinh lai 30/09/2026, thay the
    Proper Case truoc do cho rieng 2 cot nay - Proper Case van giu cho
    Ho & Ten / Gioi tinh)."""
    if raw is None:
        return None, None
    s = str(raw)
    if s.strip() == "":
        return s, None
    return s[0].upper() + s[1:], None


_KHONG_XAC_DINH_RE = re.compile(r",\s*không xác định", re.IGNORECASE)


def strip_khong_xac_dinh(name, **kw):
    """Bo cum tu ', không xác định' (hau to rat hay gap trong ten benh tra
    tu bang ICD-10 khi khong ro the/dang cu the cua benh) de ten benh ngan
    gon hon - dung cho cot DANH GIA theo yeu cau Jo 30/09/2026."""
    if not name:
        return name
    return _KHONG_XAC_DINH_RE.sub("", name).strip()


def verbatim(raw, **kw):
    if raw is None or raw == "":
        return None, None
    return str(raw).strip(), None


_XQUANG_BINH_THUONG = "PHỔI SÁNG BÌNH THƯỜNG"

# Cac cum tu "BINH THUONG" thuong gap trong ket qua X-quang/Sieu am dang van
# ban tu do cua M03 (so khop CHINH XAC sau khi chuan hoa hoa/thuong + khoang
# trang - AN TOAN hon so khop chua/mot phan, tranh bo sot noi dung bat
# thuong that su). Dung chung cho ca xquang_flag va finding_flag (sieu am).
_BINH_THUONG_PATTERNS = {
    _XQUANG_BINH_THUONG,
    "BÌNH THƯỜNG",
    "CHƯA GHI NHẬN BẤT THƯỜNG",
    "KHÔNG GHI NHẬN BẤT THƯỜNG",
    "CHƯA PHÁT HIỆN BẤT THƯỜNG",
    "KHÔNG PHÁT HIỆN BẤT THƯỜNG",
}


def _normalize_ws_upper(raw):
    return " ".join(str(raw).strip().upper().split())


def xquang_flag(raw, **kw):
    """X-quang (cot xq): rut gon theo yeu cau Jo 30/09/2026 -
    'PHỔI SÁNG BÌNH THƯỜNG' hoac cac cum 'binh thuong' thong dung khac
    (khong phan biet hoa/thuong, khoang trang thua) -> 'bt'; co gia tri
    khac -> 'x'; o trong -> giu trong (None)."""
    if raw is None or str(raw).strip() == "":
        return None, None
    text = _normalize_ws_upper(raw)
    if text in _BINH_THUONG_PATTERNS:
        return "bt", None
    return "x", None


# Alias dung chung cho Sieu am tong quat / Sieu am vu (cot satq/satv) - cung
# logic nhu xquang_flag nhung ten trung tinh hon, dung de phan loai bt/x KHI
# CAN (vd de biet co dua vao Danh gia hay khong), KHONG lam doi cach hien thi
# hien tai cua cot satq/satv (van la verbatim nguyen van - yeu cau rieng
# truoc do cua Jo, khong doi) - yeu cau Jo 30/09/2026 dot 3.
finding_flag = xquang_flag


_THEO_DOI_PREFIX_RE = re.compile(r"^theo\s*dõi\s*:?\s*", re.IGNORECASE)
_SIDE_PAREN_RE = re.compile(r"\(([a-zđ])\)", re.IGNORECASE)


def format_finding_for_danhgia(raw, prefix, **kw):
    """Chuan hoa 1 ket qua CAN LAM SANG dang van ban tu do (Sieu am, X-quang)
    BAT THUONG de dua vao cot DANH GIA - GIU NGUYEN noi dung nhu trong o goc
    (yeu cau Jo 30/09/2026 dot 3: "giữ nguyên giá trị trong ô X-quang để ghi
    qua ô Đánh giá"), chi:
      - bo tien to "Theo dõi"/"Theo dõi:" o dau (neu co) - vi ban than cot
        Danh gia da ham y day la dieu can theo doi, khong can lap lai;
      - dua ve chu thuong (du lieu tho thuong la CHU HOA toan bo), rieng cac
        ky hieu ben trong ngoac don 1 chu cai nhu (P)/(T) (quy uoc ben
        phai/trai trong ghi chu y khoa) duoc GIU HOA;
      - viet hoa chu cai dau tien cua noi dung;
      - them tien to viet tat chuyen muc (vd "XQ", "SATQ", "SATV") o dau.
    Tra ve None neu raw rong."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    s = _THEO_DOI_PREFIX_RE.sub("", s).strip()
    if s == "":
        return None
    low = s.lower()
    low = _SIDE_PAREN_RE.sub(lambda m: "(" + m.group(1).upper() + ")", low)
    body = low[0].upper() + low[1:] if low else low
    return f"{prefix} {body}"


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
