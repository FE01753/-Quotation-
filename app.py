import streamlit as st
import pandas as pd
import os
import json
import re
from datetime import datetime
import urllib.parse

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
st.write("批量上傳 PDF，透過互動表格輕鬆勾選刪除或展開檢視！")

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
# Tab 2: 智能檢視、預覽與管理 (採用 DataFrame 批量勾選)
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

        if filtered_data:
            st.write("💡 **勾選下方表格嘅「刪除」欄位，然後按下方按鈕即可實現批量刪除！**")
            
            # 建立 DataFrame 專畀互動表格
            df_display = []
            for item in filtered_data:
                df_display.append({
                    "刪除": False,
                    "ID": item['id'],
                    "檔名": item['original_filename'],
                    "公司": item.get('client_company', '未分類'),
                    "金額": item.get('amount', '未偵測')
                })
            
            df_editable = pd.DataFrame(df_display)
            
            # 呈現互動編輯表格
            edited_df = st.data_editor(
                df_editable,
                column_config={
                    "刪除": st.column_config.CheckboxColumn("刪除？", default=False),
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "檔名": st.column_config.TextColumn("檔案名稱", disabled=True),
                    "公司": st.column_config.TextColumn("公司名稱", disabled=True),
                    "金額": st.column_config.TextColumn("金額", disabled=True),
                },
                hide_index=True,
                key="quotation_table_editor"
            )
            
            # 取得被勾選刪除的 ID
            selected_to_delete = edited_df[edited_df["刪除"] == True]["ID"].tolist()
            
            if selected_to_delete:
                if st.button(f"🗑️ 確認刪除已勾選嘅 {len(selected_to_delete)} 個檔案", type="primary"):
                    db_data_updated = []
                    for item in db_data:
                        if item['id'] in selected_to_delete:
                            target_path = os.path.join(PDF_DIR, item['filename'])
                            if os.path.exists(target_path):
                                os.remove(target_path)
                        else:
                            db_data_updated.append(item)
                    
                    save_db(db_data_updated)
                    st.success(f"🎉 成功刪除 {len(selected_to_delete)} 個檔案！")
                    st.rerun()

            st.markdown("---")
            st.subheader("📄 檔案快速預覽、下載與 WhatsApp 傳送")
            
            # 獨立檔案展開檢視區
            for item in filtered_data:
                file_path = os.path.join(PDF_DIR, item['filename'])
                
                with st.expander(f"📄 [ID: {item['id']}] {item['original_filename']}"):
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            pdf_bytes = f.read()
                            
                        st.info("💡 貼士：點擊下方按鈕即可在瀏覽器新分頁完美開啟 PDF 閱讀（避開 Chrome 內嵌黑屏限制）。")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.download_button(
                                label="📥 立即開啟 / 下載 PDF 檔案",
                                data=pdf_bytes,
                                file_name=item['original_filename'],
                                mime="application/pdf",
                                key=f"dl_{item['id']}"
                            )
                        with col_btn2:
                            share_text = f"🛠️ E&M Quotation 參考分享 (Design by nikki 💅)：\n- 檔名: {item['original_filename']}"
                            encoded_share_text = urllib.parse.quote(share_text)
                            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_share_text}"
                            st.markdown(
                                f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:8px 14px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">💬 WhatsApp 傳送</button></a>',
                                unsafe_allow_html=True
                            )
                            
                        if item.get('extracted_text'):
                            with st.expander("🔍 檢視 PDF 智能萃取文字內容"):
                                st.text(item['extracted_text'][:1000] + ("..." if len(item.get('extracted_text', '')) > 1000 else ""))
                    else:
                        st.error("找不到對應的 PDF 檔案。")

# --- 專屬水印 Footer ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "🛠️ <b>Design by nikki 💅</b>"
    "</div>", 
    unsafe_allow_html=True
)
