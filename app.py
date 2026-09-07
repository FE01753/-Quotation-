import streamlit as st
import pandas as pd
import os
import json
import base64
import re
from datetime import datetime
import urllib.parse

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
                data = json.load(f)
                # 自動兼容舊資料格式，避免 KeyError
                for item in data:
                    if "client_company" not in item:
                        item["client_company"] = item.get("client_name", "未分類公司")
                    if "attention_name" not in item:
                        item["attention_name"] = "未偵測"
                    if "project_name" not in item:
                        item["project_name"] = os.path.splitext(item.get("original_filename", "unknown"))[0]
                    if "amount" not in item:
                        item["amount"] = "未偵測"
                return data
        except:
            return []
    return []

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 智能分析 PDF 內文：提取第一行作公司，Attention 作聯絡人 ---
def smart_analyze_pdf(filename, text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    detected_client_company = lines[0] if len(lines) > 0 else os.path.splitext(filename)[0]
    
    detected_attention = "未偵測"
    for line in lines:
        if "attention" in line.lower() or "attn" in line.lower():
            detected_attention = line
            break
            
    amount_found = "未偵測"
    amount_patterns = [r"HK\$\s*[\d,]+\.?\d*", r"\$\s*[\d,]+\.?\d*", r"Total\s*:\s*[\d,]+\.?\d*"]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_found = match.group(0)
            break
            
    return detected_client_company, detected_attention, amount_found

# --- 顯示 PDF 預覽的輔助函數 ---
def render_pdf_preview(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error("找不到對應的 PDF 檔案。")

# --- App 標題與分頁 (加入 nikki 水印標記) ---
st.title("📁 智能工程 Quotation 檔案管理系統")
st.caption("✨ System curated & Design by nikki 💅")
st.write("批量上傳 PDF：自動識別公司與 Attention，點擊表格即時預覽、刪除及 WhatsApp 分享！")

tab1, tab2 = st.tabs(["📤 批量上載與智能分析", "📂 智能檢視、預覽與管理"])

# ==========================================
# Tab 1: 批量上載與智能分析
# ==========================================
with tab1:
    st.subheader("📤 批量上載 Quotation PDF 檔案")
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
                    
                    client_company, attention_name, detected_amount = smart_analyze_pdf(original_name, extracted_text)
                    clean_project_name = os.path.splitext(original_name)[0]
                    
                    record["date"] = str(datetime.today().date())
                    record["project_name"] = clean_project_name
                    record["client_company"] = client_company
                    record["attention_name"] = attention_name
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
                    
                    client_company, attention_name, detected_amount = smart_analyze_pdf(original_name, extracted_text)
                    clean_project_name = os.path.splitext(original_name)[0]
                    
                    new_record = {
                        "id": new_id,
                        "date": str(datetime.today().date()),
                        "project_name": clean_project_name,
                        "client_company": client_company,
                        "attention_name": attention_name,
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
# Tab 2: 智能檢視、預覽與管理
# ==========================================
with tab2:
    st.subheader("📂 智能檢視、預覽與管理")
    st.write("點選下方表格中的項目即可即時預覽。如需刪除或分享，請利用下方的工具列。")

    db_data = load_db()

    if not db_data:
        st.info("暫無 Quotation 紀錄，請先上載 PDF。")
    else:
        df_pdf = pd.DataFrame(db_data)
        
        search_kw = st.text_input("🔍 自由關鍵字搜尋（公司名稱、Attention、檔名、金額）：", value="")
        if search_kw:
            df_pdf = df_pdf[
                df_pdf['client_company'].str.contains(search_kw, case=False, na=False) |
                df_pdf['attention_name'].str.contains(search_kw, case=False, na=False) |
                df_pdf['original_filename'].str.contains(search_kw, case=False, na=False) |
                df_pdf['amount'].str.contains(search_kw, case=False, na=False)
            ]

        display_df = df_pdf[['id', 'date', 'client_company', 'attention_name', 'project_name', 'amount', 'original_filename']]
        
        st.write("👇 **請點選你想預覽的記錄行：**")
        event = st.dataframe(
            display_df,
            use_container_width=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        selected_rows = event.selection.get("rows", [])
        
        if selected_rows:
            selected_index = selected_rows[0]
            selected_record = df_pdf.iloc[selected_index]
            
            st.markdown("---")
            st.markdown(f"### 📄 預覽中：{selected_record['original_filename']}")
            st.markdown(f"**公司：** {selected_record['client_company']} | **Attention：** {selected_record['attention_name']} | **金額：** {selected_record['amount']}")
            
            # --- WhatsApp 快速分享按鈕 ---
            share_text = f"🛠️ E&M Quotation 參考分享 (Design by nikki 💅)：\n- 檔名: {selected_record['original_filename']}\n- 公司: {selected_record['client_company']}\n- Attention: {selected_record['attention_name']}\n- 金額: {selected_record['amount']}"
            encoded_share_text = urllib.parse.quote(share_text)
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_share_text}"
            
            st.markdown(
                f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:8px 16px; border:none; border-radius:4px; font-weight:bold; cursor:pointer;">💬 WhatsApp 傳送摘要比同事</button></a>',
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
            
            file_path = os.path.join(PDF_DIR, selected_record['filename'])
            render_pdf_preview(file_path)

        st.divider()
        
        # --- 刪除檔案專區 ---
        with st.expander("🗑️ 管理與刪除不需要的 Quotation 記錄"):
            del_ids = [item['id'] for item in db_data]
            target_del_id = st.selectbox("選擇要刪除的 Quotation ID：", options=[None] + del_ids)
            
            if target_del_id:
                target_rec = next((item for item in db_data if item["id"] == target_del_id), None)
                if target_rec:
                    st.warning(f"準備刪除：`{target_rec['original_filename']}` (公司: {target_rec['client_company']})")
                    if st.button("⚠️ 確認永久刪除此記錄及實體 PDF", type="primary"):
                        f_path = os.path.join(PDF_DIR, target_rec['filename'])
                        if os.path.exists(f_path):
                            os.remove(f_path)
                        
                        db_data = [item for item in db_data if item["id"] != target_del_id]
                        save_db(db_data)
                        st.success("成功刪除記錄！請重新整理頁面。")
                        st.rerun()

# --- 專屬水印 Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "🛠️ <b>Design by nikki 💅</b>"
    "</div>", 
    unsafe_allow_html=True
)
