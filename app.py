import streamlit as st
import pandas as pd
import os
import json
import base64
import re
from datetime import datetime

# 嘗試引入 PDF 讀取工具
try:
    import pypdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

st.set_page_config(page_title="智能工程 Quotation 檔案管理系統", page_icon="📁", layout="centered")

# --- 自訂 CSS 樣式：Aptos 12pt ---
st.markdown(
    """
    <style>
    .stCodeBlock code, .stCodeBlock pre {
        font-family: 'Aptos', sans-serif !important;
        font-size: 12pt !important;
    }
    .stTextArea textarea {
        font-family: 'Aptos', sans-serif !important;
        font-size: 12pt !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

PDF_DIR = "quotations_pdf_storage"
os.makedirs(PDF_DIR, exist_ok=True)
DB_FILE = "quotations_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 智能分析 PDF 內文與檔名的函數 ---
def smart_analyze_pdf(filename, text):
    client_keywords = ["Regent Hotel", "K11 Musea", "K11", "Regent", "MTR", "Link", "Airport", "Sands", "W Hotel"]
    detected_client = "其他 / 未分類"
    
    combined_str = filename + " " + text
    for kw in client_keywords:
        if kw.lower() in combined_str.lower():
            detected_client = kw
            break
            
    if any(k in combined_str.lower() for k in ["fs", "fire", "消防", "sprinkler", "alarm", "afa"]):
        category = "Fire Services (FS)"
    elif any(k in combined_str.lower() for k in ["elv", "cctv", "security", "data", "network"]):
        category = "Extra Low Voltage (ELV)"
    elif any(k in combined_str.lower() for k in ["el", "electrical", "power", "mcb", "fuse", "電力"]):
        category = "Electrical (EL)"
    elif any(k in combined_str.lower() for k in ["hvac", "chiller", "fcu", "ventilation", "冷氣", "通風", "vac"]):
        category = "HVAC / Mechanical"
    else:
        category = "General E&M Works"
        
    amount_found = "未偵測"
    amount_patterns = [r"HK\$\s*[\d,]+\.?\d*", r"\$\s*[\d,]+\.?\d*", r"Total\s*:\s*[\d,]+\.?\d*"]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_found = match.group(0)
            break
            
    return detected_client, category, amount_found

# --- 顯示 PDF 預覽的輔助函數 ---
def render_pdf_preview(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error("找不到對應的 PDF 檔案。")

# --- App 標題與分頁 ---
st.title("📁 智能工程 Quotation 檔案管理系統")
st.write("批量上傳 PDF：自動分析分類、取代重複檔案，並提供即時網頁預覽 (Preview)！")

tab1, tab2 = st.tabs(["📤 批量上載與智能分析", "📂 智能分類預覽與搜尋"])

# ==========================================
# Tab 1: 批量上載與智能分析
# ==========================================
with tab1:
    st.subheader("📤 批量上載 Quotation PDF 檔案")
    st.write("一次過選取多個 PDF，系統會自動辨識新檔或取代現有同名檔案。")

    uploaded_pdfs = st.file_uploader("選擇多個 Quotation PDF 檔案", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_pdfs:
        st.info(f"已選取 {len(uploaded_pdfs)} 個檔案準備上載。")
        
        if st.button("🚀 開始智能批量分析與歸檔", type="primary"):
            db_data = load_db()
            existing_map = {item.get("original_filename"): item for item in db_data}
            
            success_count = 0
            replaced_count = 0
            replaced_files = []
            
            for uploaded_pdf in uploaded_pdfs:
                original_name = uploaded_pdf.name
                
                if original_name in existing_map:
                    record = existing_map[original_name]
                    filename = record["filename"]
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_pdf.getbuffer())
                        
                    extracted_text = ""
                    if PDF_SUPPORT:
                        try:
                            reader = pypdf.PdfReader(file_path)
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    extracted_text += text + "\n"
                        except Exception as e:
                            extracted_text = f"無法讀取文字: {str(e)}"
                    else:
                        extracted_text = "未啟用 PDF 文字萃取套件"
                    
                    client_name, category, detected_amount = smart_analyze_pdf(original_name, extracted_text)
                    clean_project_name = os.path.splitext(original_name)[0]
                    
                    record["date"] = str(datetime.today().date())
                    record["project_name"] = clean_project_name
                    record["client_name"] = client_name
                    record["category"] = category
                    record["amount"] = detected_amount
                    record["extracted_text"] = extracted_text
                    
                    replaced_count += 1
                    replaced_files.append(original_name)
                    
                else:
                    new_id = (db_data[-1]["id"] + 1) if db_data else 1
                    filename = f"q_{new_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_pdf.getbuffer())
                        
                    extracted_text = ""
                    if PDF_SUPPORT:
                        try:
                            reader = pypdf.PdfReader(file_path)
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    extracted_text += text + "\n"
                        except Exception as e:
                            extracted_text = f"無法讀取文字: {str(e)}"
                    else:
                        extracted_text = "未啟用 PDF 文字萃取套件"
                    
                    client_name, category, detected_amount = smart_analyze_pdf(original_name, extracted_text)
                    clean_project_name = os.path.splitext(original_name)[0]
                    
                    new_record = {
                        "id": new_id,
                        "date": str(datetime.today().date()),
                        "project_name": clean_project_name,
                        "client_name": client_name,
                        "category": category,
                        "amount": detected_amount,
                        "filename": filename,
                        "original_filename": original_name,
                        "extracted_text": extracted_text
                    }
                    
                    db_data.append(new_record)
                    existing_map[original_name] = new_record
                    success_count += 1
                
            save_db(db_data)
            
            if success_count > 0:
                st.success(f"🎉 成功新增 {success_count} 個全新 Quotation PDF 檔案！")
            if replaced_count > 0:
                st.info(f"🔄 偵測到 {replaced_count} 個重複檔案，已自動完成**取代與更新**：\n- " + "\n- ".join(replaced_files))

# ==========================================
# Tab 2: 智能分類預覽與搜尋
# ==========================================
with tab2:
    st.subheader("📂 智能分類預覽與多維度搜尋")
    st.write("過濾項目後，直接選擇 ID 即可在下方即時預覽 PDF 內容！")

    db_data = load_db()

    if not db_data:
        st.info("暫無 Quotation 紀錄，請先上載 PDF。")
    else:
        df_pdf = pd.DataFrame(db_data)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            all_clients = ["全部"] + list(df_pdf['client_name'].unique())
            selected_client_filter = st.selectbox("🏢 按客戶/公司篩選：", options=all_clients)
        with col_f2:
            all_cats = ["全部"] + list(df_pdf['category'].unique())
            selected_cat_filter = st.selectbox("⚙️ 按工程系統篩選：", options=all_cats)
            
        filtered_df = df_pdf.copy()
        if selected_client_filter != "全部":
            filtered_df = filtered_df[filtered_df['client_name'] == selected_client_filter]
        if selected_cat_filter != "全部":
            filtered_df = filtered_df[filtered_df['category'] == selected_cat_filter]

        search_kw = st.text_input("🔍 自由關鍵字搜尋（檔名、金額、內文細節）：", value="")
        if search_kw:
            filtered_df = filtered_df[
                filtered_df['project_name'].str.contains(search_kw, case=False, na=False) |
                filtered_df['original_filename'].str.contains(search_kw, case=False, na=False) |
                filtered_df['extracted_text'].str.contains(search_kw, case=False, na=False) |
                filtered_df['amount'].str.contains(search_kw, case=False, na=False)
            ]

        st.write(f"共找到 {len(filtered_df)} 個符合條件的 Quotation 紀錄：")
        display_df = filtered_df[['id', 'date', 'client_name', 'category', 'project_name', 'amount', 'original_filename']]
        st.dataframe(display_df, use_container_width=True)
        
        # 選擇 ID 進行直接網頁預覽
        valid_ids = list(filtered_df['id'])
        if valid_ids:
            selected_id = st.selectbox("🎯 選擇要即時預覽 (Preview) 的 Quotation ID：", options=[None] + valid_ids)
            if selected_id:
                record = next((item for item in db_data if item["id"] == selected_id), None)
                if record:
                    st.markdown(f"### 📄 預覽中：{record['original_filename']}")
                    st.markdown(f"**項目：** {record['project_name']} | **客戶：** {record['client_name']} | **分類：** {record['category']} | **金額：** {record['amount']}")
                    
                    file_path = os.path.join(PDF_DIR, record['filename'])
                    # 直接呼叫網頁內嵌預覽
                    render_pdf_preview(file_path)

# --- 專屬水印 Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "🛠️ <b>Design by nikki 💅</b>"
    "</div>", 
    unsafe_allow_html=True
)
