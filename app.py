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

# --- App 標題與分頁 ---
st.title("📁 智能工程 Quotation 檔案管理系統")
st.caption("✨ System curated & Design by nikki 💅")
st.write("批量上傳 PDF，點擊按鈕即時彈出選單，一鍵放大預覽、下載或傳送！")

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
    
    db_data = load_db()

    if not db_data:
        st.info("暫無 Quotation 紀錄，請先上載 PDF。")
    else:
        search_kw = st.text_input("🔍 自由關鍵字搜尋（檔名）：", value="")
        filtered_data = db_data
        if search_kw:
            filtered_data = [item for item in db_data if search_kw.lower() in item['original_filename'].lower()]

        st.markdown("---")
        
        # 表頭
        col_h1, col_h2, col_h3, col_h4 = st.columns([1, 2, 7, 2])
        col_h1.markdown("**ID**")
        col_h2.markdown("**日期**")
        col_h3.markdown("**Original Filename (點擊彈出操作選單)**")
        col_h4.markdown("**操作**")
        st.markdown("---")
        
        for item in filtered_data:
            c1, c2, c3, c4 = st.columns([1, 2, 7, 2])
            c1.write(str(item['id']))
            c2.write(item['date'])
            
            # 使用 st.popover 彈出選單，提供「開新分頁檢視」、「下載」、「WhatsApp」
            with c3:
                with st.popover(f"📄 {item['original_filename']}"):
                    st.markdown(f"### 📄 檔案管理選項")
                    st.write(f"**檔名：** {item['original_filename']}")
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                    
                    file_path = os.path.join(PDF_DIR, item['filename'])
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            pdf_bytes = f.read()
                            
                        # 轉 Base64 以供在新分頁中完美開啟
                        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        pdf_data_url = f"data:application/pdf;base64,{base64_pdf}"
                        
                        # 1. 在新分頁檢視按鈕
                        st.markdown(
                            f'<a href="{pdf_data_url}" target="_blank"><button style="background-color:#1f77b4; color:white; padding:8px 14px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%; margin-bottom:8px;">🔍 喺新分頁放大檢視 PDF</button></a>',
                            unsafe_allow_html=True
                        )
                        
                        # 2. 下載按鈕
                        st.download_button(
                            label="📥 下載此 PDF 檔案",
                            data=pdf_bytes,
                            file_name=item['original_filename'],
                            mime="application/pdf",
                            key=f"popover_dl_{item['id']}"
                        )
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # 3. WhatsApp 傳送按鈕
                        share_text = f"🛠️ E&M Quotation 參考分享 (Design by nikki 💅)：\n- 檔名: {item['original_filename']}"
                        encoded_share_text = urllib.parse.quote(share_text)
                        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_share_text}"
                        st.markdown(
                            f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:8px 14px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">💬 WhatsApp 傳送給同事</button></a>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.error("找不到對應的 PDF 檔案。")
                
            # 直接在檔名後面設刪除按鈕
            if c4.button("🗑️ Del", key=f"del_{item['id']}"):
                f_path = os.path.join(PDF_DIR, item['filename'])
                if os.path.exists(f_path):
                    os.remove(f_path)
                
                db_data = [d for d in db_data if d["id"] != item["id"]]
                save_db(db_data)
                
                st.success(f"已成功刪除：{item['original_filename']}")
                st.rerun()

# --- 專屬水印 Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "🛠️ <b>Design by nikki 💅</b>"
    "</div>", 
    unsafe_allow_html=True
)
