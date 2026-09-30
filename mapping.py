# -*- coding: utf-8 -*-
"""
mapping.py
Nap va thao tac cau hinh cot dich (mapping.json). Tach khoi giao dien de
de sua (muc 5 cua khung nguyen tac).
"""
import json
import copy

DEFAULT_MAPPING_PATH = "mapping.json"


def load_mapping(path=DEFAULT_MAPPING_PATH):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def save_mapping(cfg, path=DEFAULT_MAPPING_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_column(cfg, col_id):
    for col in cfg["columns"]:
        if col["id"] == col_id:
            return col
    return None


def apply_manual_override(cfg, col_id, keywords):
    """Ghi de source_keywords cho mot cot (dung khi nguoi dung tu chon keyword
    thu cong cho cac cot con 'Trống' nhu Cholesterol/Triglycerid/HDL/LDL -
    xem muc 2 va muc 4.2 khung nguyen tac: khong tu ghep theo ten gan giong)."""
    cfg = copy.deepcopy(cfg)
    col = get_column(cfg, col_id)
    if col is not None:
        col["source_keywords"] = list(keywords)
        col["_manual_override"] = True
    return cfg


def ordered_enabled_columns(cfg, availability=None):
    """availability: dict {col_id: bool} - co du lieu that hay khong, dung cho
    enabled_default == 'auto'. Tra ve danh sach cot theo dung 'order', da loc
    theo trang thai bat/tat."""
    availability = availability or {}
    cols = []
    for col in sorted(cfg["columns"], key=lambda c: c["order"]):
        default = col.get("enabled_default", True)
        if default == "auto":
            on = availability.get(col["id"], False)
        else:
            on = bool(default)
        if col.get("required"):
            on = True
        if on:
            cols.append(col)
    return cols
