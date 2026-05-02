#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 18:03:46 2026

@author: trieukimlanh
"""
# streamlit run "/Users/trieukimlanh/Library/CloudStorage/GoogleDrive-lanhtk@hub.edu.vn/My Drive/Spyder/app/Báo điểm GK/QL_điểm.py"
#pip install gspread oauth2client
import streamlit as st
import pandas as pd
import sqlite3
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Quản lý Điểm QT SV", page_icon="📝", layout="wide")

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
        df.columns = [str(c).strip() for c in df.columns]

        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        return df
    except Exception as e:
        st.error(f"Không thể tải dữ liệu: {e}")
        return None

def normalize_mssv(x):
    if pd.isna(x):
        return ""
    
    x = str(x).strip()
    
    # bỏ .0 nếu có
    if x.endswith(".0"):
        x = x[:-2]
    
    return x


def find_student_row(df, mssv):
    if df is None or df.empty:
        return None
    
    id_col = None
    for col in df.columns:
        col_norm = str(col).upper().replace(" ", "")
        
        if any(x in col_norm for x in ["MSSV", "MASV", "SV"]):
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
    df["MSSV"] = df["MSSV"].apply(normalize_mssv)

    row = df[df["MSSV"] == normalize_mssv(mssv)]

    if row.empty:
        return False, None
    
    real_pass = row.iloc[0].get("password", "")
    must_change = row.iloc[0].get("must_change", "0")

    if str(password) == str(real_pass):
        return True, must_change
    
    return False, None

import gspread
from oauth2client.service_account import ServiceAccountCredentials
def update_password(mssv, new_pass):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url(LINK_USER).sheet1
    
    # Lấy toàn bộ giá trị (bao gồm cả tiêu đề) để tính số hàng chính xác
    all_data = sheet.get_all_values() 
    
    # Giả định cột MSSV là cột 1 (index 0). Nếu là cột khác, hãy sửa số 0 ở [0]
    found = False
    for i, row_values in enumerate(all_data):
        # i + 1 vì Google Sheet bắt đầu từ dòng 1
        if i == 0: continue # Bỏ qua dòng tiêu đề
        
        if normalize_mssv(row_values[0]) == normalize_mssv(mssv):
            sheet.update_cell(i + 1, 4, str(new_pass))  # Cột 4: Password
            sheet.update_cell(i + 1, 5, "0")           # Cột 5: must_change
            found = True
            break
    
    if not found:
        st.error(f"Không tìm thấy MSSV {mssv} trên hệ thống để đổi mật khẩu.")
        st.stop()

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
        
    st.markdown("### 🔁 Reset mật khẩu SV")
    mssv_reset = st.text_input("Nhập MSSV cần reset")
    
    if st.button("Reset"):
        if mssv_reset:
            update_password(mssv_reset, normalize_mssv(mssv_reset))
            st.success("Đã reset về mặc định (MSSV)")
        else:
            st.warning("Nhập MSSV trước")
# PHẦN 3: GIAO DIỆN CHÍNH
# Tải dữ liệu từ DB lên để sử dụng
# PHẦN 3: GIAO DIỆN CHÍNH
# --- CẤU HÌNH LINK CỐ ĐỊNH TẠI ĐÂY ---
LINK_TT = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=955190676#gid=955190676"
LINK_DD = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=246423748#gid=246423748"
LINK_QT = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=347549665#gid=347549665"
LINK_4 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1724010901#gid=1724010901"
LINK_5 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1112987460#gid=1112987460"
LINK_6 = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=250285587#gid=250285587"
LINK_USER = "https://docs.google.com/spreadsheets/d/19VCWKBdA9WwOv8LzZCe2RQJTeO-5YJGixMZc1OeiWFY/edit?gid=1406726171#gid=1406726171"

user_db = load_data(LINK_USER)

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

if role == "👨‍🏫 Giảng viên":
    st.header("👨‍🏫 Quản lý Điểm quá trình (Giảng viên)")
    st.markdown("##### === Triệu Kim Lanh ===")

    # Hiển thị các Tab
    t1, t2, t3, t4, t5, t6 = st.tabs(["💬 Điểm tương tác", "📅 Điểm danh", "🎯 Điểm bài nhóm", "🎯 Điểm bài cá nhân","📊 Điểm quá trình", "📈 Thông tin khác"])
    
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
            update_password(st.session_state.user, new_pass)
            
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
            
        else:
            st.error(f"❌ Không tìm thấy dữ liệu cho mã số: {mssv_clean}")
            st.info("Hãy kiểm tra xem bạn đã nhập đúng mã số chưa, hoặc liên hệ GV để cập nhật danh sách mới nhất.")
                
st.sidebar.markdown("---")
st.sidebar.caption("Dữ liệu được bảo mật trong Database cục bộ.")
