#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 18:03:46 2026

@author: trieukimlanh
"""
# streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-lanhtk@hub.edu.vn/My Drive/Spyder/app/Báo điểm GK/QL_điểm (link).py"
#pip install gspread oauth2client
import streamlit as st
import pandas as pd
import sqlite3
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Quản lý Điểm QT SV", page_icon="📝", layout="wide")

# --- CẤU HÌNH LINK CỐ ĐỊNH TẠI ĐÂY ---
LINK_TT = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=955190676#gid=955190676"
LINK_DD = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=246423748#gid=246423748"
LINK_QT = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=347549665#gid=347549665"
LINK_4 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1724010901#gid=1724010901"
LINK_5 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1112987460#gid=1112987460"
LINK_6 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=250285587#gid=250285587"
LINK_USER = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1406726171#gid=1406726171"


def get_creds():
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception:
        import os, json

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "service_account.json")

        with open(json_path, "r") as f:
            return json.load(f)

def get_mssv_col(df):
    for col in df.columns:
        if "SV" in str(col).upper() and "LỚP" not in str(col).upper():
            return col
    return None

# --- HÀM HỖ TRỢ GOOGLE SHEETS (GIỮ NGUYÊN) ---
def get_csv_url(gsheet_url):
    try:
        if "docs.google.com" not in gsheet_url: return gsheet_url
        sheet_id = gsheet_url.split("/d/")[1].split("/")[0]
        gid = "0"
        if "gid=" in gsheet_url:
            gid = gsheet_url.split("gid=")[-1].split("&")[0]
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    except: return gsheet_url

@st.cache_data(ttl=300)  # cache 5 phút
def load_data(url):
    csv_url = get_csv_url(url)
    try:
        df = pd.read_csv(csv_url, dtype=str, engine='python', on_bad_lines='skip')

        # chuẩn hóa header
        df.columns = (
            df.columns
            .str.strip()
            .str.replace("\xa0", "", regex=True)
            .str.replace(r"\s+", " ", regex=True)
        )

        # chuẩn hóa dữ liệu
        for col in df.columns:
            df[col] = (
                df[col]
                .replace(["nan", "None", "NaT"], pd.NA)
                .astype("string")
                .str.strip()
                .fillna("")
            )

        return df

    except Exception as e:
        st.error(f"Không thể tải dữ liệu: {e}")
        return None

import re

def extract_group_number(x):
    if x is None:
        return ""
    x = str(x)
    match = re.search(r'\d+', x)
    return match.group(0) if match else ""

def normalize_mssv(x):
    if pd.isna(x):
        return ""
    
    x = str(x).strip()
    
    # bỏ .0 nếu có
    if x.endswith(".0"):
        x = x[:-2]
    
    return x


def get_group_role(data_6, mssv):
    if data_6 is None:
        return None

    df = data_6.copy()

    # chuẩn hóa cột
    df.columns = df.columns.str.strip()

    # tìm cột MSSV linh hoạt
    mssv_col = None
    for col in df.columns:
        if "SV" in str(col).upper() and "LỚP" not in str(col).upper():
            mssv_col = col
            break

    if mssv_col is None:
        return None

    # chuẩn hóa MSSV
    df[mssv_col] = df[mssv_col].astype(str).str.strip().apply(normalize_mssv)
    target = normalize_mssv(mssv)

    # 1. tìm dòng chứa MSSV
    rows = df[df[mssv_col] == target]

    if rows.empty:
        return None

    roles = []

    for _, r in rows.iterrows():

        nam_hoc = str(r["Năm học"]).strip()
        lop_hp = str(r["Lớp HP"]).strip()
        nhom = str(r["Nhóm trưởng"]).strip()

        # chỉ lấy dòng nào có MSSV thật (tránh rác)
        if pd.isna(r[mssv_col]) or r[mssv_col] == "":
            continue

        roles.append({
            "nam_hoc": nam_hoc,
            "lop_hp": lop_hp,
            "nhom": extract_group_number(nhom),
            "nhom_raw": nhom,
            "mssv": normalize_mssv(r[mssv_col])
        })

    return roles if roles else None

def filter_group(df, role):
    if df is None or role is None:
        return None

    df = df.copy()
    
    # Chuẩn hóa cột để so sánh
    df["Năm học"] = df["Năm học"].astype(str).str.strip()
    df["Lớp HP"] = df["Lớp HP"].astype(str).str.strip()
    
    # Chuẩn hóa cột Nhóm bên data_tt (Ví dụ: từ "1" hoặc "Nhóm 1" về "1")
    def clean_nhom(x):
        m = re.search(r'\d+', str(x))
        return m.group(0) if m else ""
    
    df["Nhóm_Clean"] = df["Nhóm"].apply(clean_nhom)

    # Lọc đúng Năm học, Lớp HP và số Nhóm
    filtered = df[
        (df["Năm học"] == role["nam_hoc"]) & 
        (df["Lớp HP"] == role["lop_hp"]) & 
        (df["Nhóm_Clean"] == role["nhom"])
    ]
    
    return filtered

def is_group_locked(data_6, role):
    if data_6 is None or role is None:
        return False

    df = data_6.copy()

    df["Năm học"] = df["Năm học"].astype(str).str.strip()
    df["Lớp HP"] = df["Lớp HP"].astype(str).str.strip()

    target = df[
        (df["Năm học"] == role["nam_hoc"]) &
        (df["Lớp HP"] == role["lop_hp"])
    ]

    if target.empty:
        return False

    status = target["Tình trạng"].astype(str).str.lower()

    return any(status.str.contains("hoàn thành"))

def is_buoi_locked_df(group_df, buoi):
    if group_df is None or group_df.empty:
        return False

    def normalize(x):
        return (
            str(x)
            .strip()
            .upper()
            .replace("\xa0", "")
            .replace(" ", "")
        )

    target = normalize(buoi)

    # tìm cột buổi
    buoi_col = None
    for col in group_df.columns:
        if target in normalize(col):
            buoi_col = col
            break

    if buoi_col is None:
        return False

    # 🔥 xử lý sạch dữ liệu
    col_data = (
        group_df[buoi_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # loại bỏ các giá trị "rỗng giả"
    col_data = col_data.replace(["", "nan", "none"], pd.NA)

    # nếu còn giá trị thật → đã có dữ liệu
    return col_data.dropna().shape[0] > 0

def find_student_row(df, mssv):
    if df is None or df.empty:
        return None
    
    id_col = None
    for col in df.columns:
        col_norm = str(col).upper().replace(" ", "")
        
        if any(x in col_norm for x in ["MSSV", "Mã SV", "SV"]):
            id_col = col
            break

    # 🔥 thêm xử lý cho "Mã SV"
    if id_col is None:
        for col in df.columns:
            col_norm = str(col).upper()
            if "SV" in col_norm and "LỚP" not in col_norm:
                id_col = col
                break

    if id_col is None:
        st.error("❌ Không tìm thấy cột MSSV")
        return None

    col_series = df[id_col].apply(normalize_mssv)
    target = normalize_mssv(mssv)
    
    res = df[col_series == target]

    return res if not res.empty else None

def check_login(user_db, mssv, password):
    if user_db is None:
        return False, None
    
    df = user_db.copy()
    df["Mã SV"] = df["Mã SV"].apply(normalize_mssv)

    row = df[df["Mã SV"] == normalize_mssv(mssv)]

    if row.empty:
        return False, None
    
    real_pass = row.iloc[0].get("password", "")
    must_change = row.iloc[0].get("must_change", "0")

    if str(password) == str(real_pass):
        return True, must_change
    
    return False, None

def update_password(mssv, new_pass, sheet_url, must_change_value="0"):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
   
    creds_dict = get_creds()
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1 # Dùng tham số truyền vào
    # Lấy toàn bộ giá trị (bao gồm cả tiêu đề) để tính số hàng chính xác
    all_data = sheet.get_all_values() 
    
    # Giả định cột MSSV là cột 1 (index 0). Nếu là cột khác, hãy sửa số 0 ở [0]
    found = False
    for i, row_values in enumerate(all_data):
        # i + 1 vì Google Sheet bắt đầu từ dòng 1
        if i == 0: continue # Bỏ qua dòng tiêu đề
        
        if normalize_mssv(row_values[0]) == normalize_mssv(mssv):
            sheet.update_cell(i + 1, 5, str(new_pass))  # Cột 5: Password
            sheet.update_cell(i + 1, 6, must_change_value)           # Cột 6: must_change
            found = True
            break
    
    if not found:
        st.error(f"Không tìm thấy MSSV {mssv} trên hệ thống để đổi mật khẩu.")
        st.stop()

def reset_password_by_class(lop_sv, sheet_url):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = get_creds()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url(sheet_url).sheet1
    all_data = sheet.get_all_values()

    header = all_data[0]

    def norm(x):
        return str(x).strip().upper().replace(" ", "").replace("\xa0", "")

    header_norm = [norm(h) for h in header]

    # tìm cột
    lop_idx = next((i for i, h in enumerate(header_norm) if "LOP" in h), None)
    mssv_idx = next((i for i, h in enumerate(header_norm) if "SV" in h), None)

    if lop_idx is None or mssv_idx is None:
        st.error("Không tìm thấy cột Lớp SV hoặc MSSV")
        return 0

    updates = []
    count = 0

    for i, row in enumerate(all_data[1:], start=2):
        if norm(row[lop_idx]) == norm(lop_sv):
            mssv = normalize_mssv(row[mssv_idx])

            # cột 5 = password, cột 6 = must_change
            updates.append({
                "range": f"E{i}",
                "values": [[mssv]]
            })
            updates.append({
                "range": f"F{i}",
                "values": [["1"]]
            })

            count += 1

    if updates:
        sheet.batch_update(updates)

    return count

        
def update_interaction_sheet(sheet_url, mssv, buoi_col, value):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = get_creds()
        
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url(sheet_url).worksheet("Tương tác")  # hoặc tên tab đúng
    data = sheet.get_all_values()

    header = [str(h).strip() for h in data[0]]

    def normalize(x):
        return (
            str(x)
            .strip()
            .upper()
            .replace("\xa0", "")
            .replace(" ", "")
        )
    
    header_norm = [normalize(h) for h in header]
    target = normalize(buoi_col)
    
    # tìm gần đúng thay vì index cứng
    col_idx = None
    for i, h in enumerate(header_norm):
        if target in h:   # <-- quan trọng: dùng "contains"
            col_idx = i + 1
            break
    
    if col_idx is None:
        st.error(f"Không tìm thấy cột: {buoi_col}")
        st.write("Header thực tế:", header)
        st.stop()

    # tìm cột MSSV đúng
    mssv_col_idx = 4  # cột 4 là MSSV

    for i, row in enumerate(data[1:], start=2):
        if normalize_mssv(row[mssv_col_idx - 1]) == normalize_mssv(mssv):
            sheet.update_cell(i, col_idx, value)
            break

# --- GIAO DIỆN CHÍNH ---

# PHẦN 1: XỬ LÝ PHÂN QUYỀN & URL PARAMS (GIỮ NGUYÊN)
query_params = st.query_params
is_student_link = query_params.get("role") == "student"

if is_student_link:
    role = "🧑‍🎓 Sinh viên"
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;} section[data-testid="stSidebar"] {width: 0px;}</style>""", unsafe_allow_html=True)
else:
    st.sidebar.title("🔐 Hệ thống Quản trị")
    role = st.sidebar.radio("Chọn vai trò:", ["👨‍🏫 Giảng viên", "🧑‍🎓 Sinh viên"])

# PHẦN 2: LOGIC KIỂM TRA MẬT KHẨU (GIỮ NGUYÊN)
if role == "👨‍🏫 Giảng viên":
    st.sidebar.markdown("---")
    pwd = st.sidebar.text_input("Nhập mật khẩu quản lý:", type="password")
    if pwd != "admin123":
        if pwd != "": st.sidebar.error("❌ Sai mật khẩu")
        else: st.info("🔑 Vui lòng nhập mật khẩu ở menu bên trái để truy cập quản trị.")
        st.stop()

    st.sidebar.success("✅ Đã xác thực")
    if st.sidebar.button("🔄 Làm mới dữ liệu"):
        load_data.clear()
        st.success("Đã làm mới dữ liệu từ Google Sheets")
        st.rerun()
        
# PHẦN 3: GIAO DIỆN CHÍNH
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.must_change = "0"
    
# Tải dữ liệu từ DB lên để sử dụng
data_tt = load_data(LINK_TT)
data_dd = load_data(LINK_DD)
data_qt = load_data(LINK_QT)
data_4  = load_data(LINK_4)
data_5  = load_data(LINK_5)
data_6  = load_data(LINK_6)
user_db = load_data(LINK_USER)

if role == "👨‍🏫 Giảng viên":
    st.header("👨‍🏫 Quản lý Điểm quá trình (Giảng viên)")
    st.markdown("##### === Triệu Kim Lanh ===")

    # Hiển thị các Tab
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["💬 Điểm tương tác", "📅 Điểm danh", "🎯 Điểm bài nhóm", "🎯 Điểm bài cá nhân","📊 Điểm quá trình", "📈 Thông tin khác","👨‍🏫 Admin_Password"])
    
    with t1:
        if data_tt is not None:
            
            st.dataframe(data_tt, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")
            
    with t2:
        if data_dd is not None:
            st.dataframe(data_dd, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")
            
    with t3:
        if data_4 is not None:
            st.dataframe(data_4, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")
    with t4:
        if data_5 is not None:
            st.dataframe(data_5, use_container_width=True)
    with t5:
        if data_qt is not None:
            st.dataframe(data_qt, use_container_width=True)
    with t6:
        if data_6 is not None:
            st.dataframe(data_6, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu.")
    with t7:
        if user_db is not None:
            st.markdown("### 🔁 Reset mật khẩu SV")
    
            tab1, tab2 = st.tabs(["Reset từng SV", "Reset theo lớp"])
    
            # ===== RESET 1 SV =====
            with tab1:
                mssv_reset = st.text_input("Nhập MSSV cần reset")
    
                if st.button("Reset MSSV"):
                    if mssv_reset:
                        update_password(
                            mssv_reset,
                            normalize_mssv(mssv_reset),
                            LINK_USER,
                            "1"
                        )
                        st.success("Đã reset về mặc định (MSSV)")
                    else:
                        st.warning("Nhập MSSV trước")
    
            # ===== RESET THEO LỚP =====
            with tab2:
                # lấy danh sách lớp HP
                if "Lớp HP" in user_db.columns:
                    lop_list = sorted(user_db["Lớp HP"].dropna().unique())
                else:
                    lop_list = []
    
                selected_lop = st.selectbox("Chọn lớp HP", lop_list)
    
                if st.button("Reset toàn bộ lớp"):
                    if selected_lop:
                        count = reset_password_by_class(selected_lop, LINK_USER)
                        st.success(f"Đã reset {count} sinh viên của lớp {selected_lop}")
                    else:
                        st.warning("Chọn lớp trước")
    
            st.dataframe(user_db, use_container_width=True)
    
        else:
            st.info("Chưa có dữ liệu.")

# Sửa lại phần hiển thị để tránh lỗi 'With' object has no attribute 'value'
if role == "🧑‍🎓 Sinh viên":
    if not st.session_state.logged_in:

        st.header("🧑‍🎓 Tra cứu kết quả học tập (quá trình)")

        mssv_input = st.text_input("Nhập Mã số sinh viên của bạn:", placeholder="Ví dụ: 030140240xxx")
        password_input = st.text_input("Mật khẩu", type="password")

        if st.button("Đăng nhập"):
            ok, must_change = check_login(user_db, mssv_input, password_input)

            if ok:
                st.session_state.logged_in = True
                st.session_state.user = normalize_mssv(mssv_input)
                st.session_state.must_change = must_change
                st.rerun()
            else:
                st.error("Sai MSSV hoặc mật khẩu")

        st.stop()
        
    if str(st.session_state.must_change) == "1":
        st.warning("⚠️ Bạn phải đổi mật khẩu trước khi tiếp tục")

        new_pass = st.text_input("Mật khẩu mới", type="password")
    
        if st.button("Đổi mật khẩu"):
            update_password(st.session_state.user, new_pass, LINK_USER, "0")
            
            # Cập nhật trạng thái session để thoát khỏi vòng lặp đổi pass
            st.session_state.must_change = "0" 
            
            # Xóa cache để lần sau load_data lấy dữ liệu mới từ Sheet
            st.cache_data.clear() 
            
            st.success("✅ Đã đổi mật khẩu thành công! Đang đăng nhập...")
            
            import time
            time.sleep(1.5)
            st.rerun()
    
        st.stop()
    
    mssv_clean = normalize_mssv(st.session_state.user)
    
    # Tải dữ liệu từ DB
    data_tt = load_data(LINK_TT)
    data_dd = load_data(LINK_DD)
    data_qt = load_data(LINK_QT)
    data_4  = load_data(LINK_4)
    data_5  = load_data(LINK_5)
    data_6  = load_data(LINK_6)
    
    role_input = get_group_role(data_6, st.session_state.user)
    
    if data_tt is None and data_dd is None and data_qt is None:
        st.warning("⚠️ Dữ liệu chưa có sẵn. Giảng viên cần vào mục 'Giảng viên' -> Nhập link -> Nhấn 'Cập nhật'.")
    else:
        row_tt = find_student_row(data_tt, mssv_clean)
        row_dd = find_student_row(data_dd, mssv_clean)
        row_qt = find_student_row(data_qt, mssv_clean)
        row_4 = find_student_row(data_4, mssv_clean)
        row_5 = find_student_row(data_5, mssv_clean)
        row_6 = find_student_row(data_6, mssv_clean)
        
        if any(x is not None for x in [row_tt, row_dd, row_qt, row_4, row_5, row_6]):
            # Tìm tên SV để chào hỏi
            ref = row_dd if row_dd is not None else (
                  row_tt if row_tt is not None else (
                  row_qt if row_qt is not None else (
                  row_4 if row_4 is not None else (
                  row_5 if row_5 is not None else row_6))))
            # Tìm cột Tên linh hoạt
            row = ref.iloc[0]

            ho_lot = row.get('Họ lót', row.get('Họ lót', ''))
            ten = row.get('Tên', '')
            
            st.success(f"✅ Sinh viên: **{ho_lot} {ten}** | MSSV: **{mssv_clean}**")

            col1, col2 = st.columns([8, 2])

            with col2:
                if st.button("🚪 Đăng xuất"):
                    st.session_state.logged_in = False
                    st.session_state.user = None
                    st.session_state.must_change = "0"
                    st.rerun()
        
            mode_sv = st.radio(
                "Chọn chức năng",
                ["📊 Xem điểm quá trình", "🧑‍🎓 Nhập tương tác"]
            )
            
            if mode_sv == "📊 Xem điểm quá trình":
                
                # HIỂN THỊ CÁC TAB ĐIỂM (ĐÃ XUỐNG DÒNG ĐỂ TRÁNH LỖI)
                if row_tt is not None:
                    with st.expander("💬 Điểm tương tác", expanded=True):
                        st.dataframe(row_tt, use_container_width=True, hide_index=True)
                
                if row_dd is not None:
                    with st.expander("📅 Điểm danh & Chuyên cần", expanded=True):
                        st.dataframe(row_dd, use_container_width=True, hide_index=True)
                
                if row_4 is not None:
                    with st.expander("🎯 Điểm bài nhóm", expanded=True):
                        st.dataframe(row_4, use_container_width=True, hide_index=True)
                if row_5 is not None:
                    with st.expander("🎯 Điểm bài cá nhân", expanded=True):
                        st.dataframe(row_5, use_container_width=True, hide_index=True)
                if row_qt is not None:
                    with st.expander("🎯 Điểm quá trình", expanded=True):
                        st.dataframe(row_qt, use_container_width=True, hide_index=True)
                
                if row_6 is not None:
                    with st.expander("🎯 Thông tin khác", expanded=True):
                        st.dataframe(row_6, use_container_width=True, hide_index=True)
            
            
            if mode_sv == "🧑‍🎓 Nhập tương tác":
                # Chỉ cần role_input không phải None (tức là đã tìm thấy MSSV trong data_6)
                if role_input is None:
                    st.warning("Bạn không có quyền nhập tương tác (không có tên trong danh sách nhóm trưởng)")
                    st.stop()
                
                selected_role = st.selectbox(
                    "Chọn nhóm",
                    role_input,
                    format_func=lambda x: f"{x['lop_hp']} - Nhóm {x['nhom']}"
                )
                
                st.info(f"Đang nhập cho: {selected_role['lop_hp']} - Nhóm {selected_role['nhom']}")
                
                is_locked = is_group_locked(data_6, selected_role)

                if role == "🧑‍🎓 Sinh viên" and is_locked:
                    st.error("🚫 Lớp đã hoàn thành, không thể nhập tương tác.")
                    st.stop()
                
                data_tt = load_data(LINK_TT)
                group_df = filter_group(data_tt, selected_role)
            
                if group_df is None or group_df.empty:
                    st.warning("Không có dữ liệu nhóm")
                else:
                    buoi = st.selectbox("Chọn buổi", [
                        "BUỔI 1","BUỔI 2","BUỔI 3","BUỔI 4",
                        "BUỔI 5","BUỔI 6","BUỔI 7","BUỔI 8","BUỔI 9"
                    ])
                    
                    
                    if is_buoi_locked_df(group_df, buoi):
                        if role == "🧑‍🎓 Sinh viên":
                            st.error(f"🚫 {buoi} đã có dữ liệu, không thể nhập lại.")
                            st.stop()
                        else:
                            st.warning(f"⚠️ {buoi} đã có dữ liệu (GV vẫn có thể sửa).")
                    
                    input_values = {}
            
                    st.write("#### Nhập tương tác cho Nhóm")
            
                    mssv_col = get_mssv_col(group_df)

                    for i, row in group_df.iterrows():
                        mssv = row[mssv_col]
                    
                        val = st.number_input(
                            f"{row.get('Lớp HP','')} - {mssv} - {row.get('Họ lót','')} {row.get('Tên','')}",
                            min_value=0,
                            step=1,
                            key=f"{mssv}_{buoi}"
                        )
                    
                        input_values[mssv] = val
            
                    if st.button("📌 Cập nhật tương tác"):
                        for mssv, val in input_values.items():
                            update_interaction_sheet(
                                LINK_TT,
                                mssv,
                                buoi,
                                val
                            )
            
                        st.success("Đã cập nhật thành công")
              
                    # ===== PREVIEW SAU KHI CẬP NHẬT =====
                    st.markdown("#### 📊 Tổng hợp tương tác nhóm (sau khi cập nhật)")
                    
                    data_tt_new = load_data(LINK_TT)
                    
                    group_preview = filter_group(data_tt_new, selected_role)
                    
                    if group_preview is not None and not group_preview.empty:
                        # chỉ hiển thị các cột BUỔI + thông tin chính
                        buoi_cols = ["Lớp HP","STT",
                            "Mã SV", "Lớp SV", "Họ lót", "Tên",
                            "BUỔI 1","BUỔI 2","BUỔI 3","BUỔI 4",
                            "BUỔI 5","BUỔI 6","BUỔI 7","BUỔI 8","BUỔI 9"
                        ]
                    
                        buoi_cols = [c for c in buoi_cols if c in group_preview.columns]
                    
                        st.dataframe(group_preview[buoi_cols], use_container_width=True, hide_index=True)
                    else:
                        st.warning("Không có dữ liệu nhóm để hiển thị")

        else:
            st.error(f"❌ Không tìm thấy dữ liệu cho mã số: {mssv_clean}")
            st.info("Hãy kiểm tra xem bạn đã nhập đúng mã số chưa, hoặc liên hệ GV để cập nhật danh sách mới nhất.")
         
st.sidebar.markdown("---")
st.sidebar.caption("Dữ liệu được bảo mật trong Database cục bộ.")
