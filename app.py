import streamlit as st
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime
import base64

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
                if not isinstance(data, list):
                    return []
                return data
        except Exception:
            return []
    return []

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"儲存資料庫失敗: {e}")

# --- App 標題與分頁 ---
st.title("📁 智能工程 Quotation 檔案管理系統")
st.caption("✨ System curated & Design by nikki 💅")
st.write("批量上傳 PDF，享受極速秒速歸檔與網頁內嵌預覽體驗！")

tab1, tab2 = st.tabs(["📤 批量上載與智能分析", "📂 智能檢視、預覽與管理"])

# ==========================================
# Tab 1: 批量上載與極速分析
# ==========================================
with tab1:
    st.subheader("📤 批量上載 Quotation / Drawing PDF 檔案")
    uploaded_pdfs = st.file_uploader("選擇多個 PDF 檔案", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_pdfs:
        st.info(f"已選取 {len(uploaded_pdfs)} 個檔案準備上載。")
    
    if st.button("🚀 開始極速批量歸檔", type="primary"):
        if not uploaded_pdfs:
            st.warning("請先選擇至少一個 PDF 檔案！")
        else:
            db_data = load_db()
            existing_map = {item.get("original_filename"): item for item in db_data}
            
            success_count = 0
            replaced_count = 0
            
            progress_bar = st.progress(0)
            total_files = len(uploaded_pdfs)
            
            for idx, uploaded_pdf in enumerate(uploaded_pdfs):
                original_name = uploaded_pdf.name
                clean_project_name = os.path.splitext(original_name)[0]
                is_drawing = any(k in original_name.upper() for k in ["PLAN", "DWG", "CSD", "LAYOUT", "E&M"])
                detected_client = "圖則/未分類" if is_drawing else clean_project_name
                
                if original_name in existing_map:
                    record = existing_map[original_name]
                    filename = record["filename"]
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_pdf.getbuffer())
                        
                    record["date"] = str(datetime.today().date())
                    record["project_name"] = clean_project_name
                    record["client_company"] = detected_client
                    replaced_count += 1
                else:
                    new_id = (db_data[-1]["id"] + 1) if db_data else 1
                    filename = f"q_{new_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_pdf.getbuffer())
                        
                    new_record = {
                        "id": new_id,
                        "date": str(datetime.today().date()),
                        "project_name": clean_project_name,
                        "client_company": detected_client,
                        "attention_name": "未偵測",
                        "amount": "未偵測",
                        "filename": filename,
                        "original_filename": original_name,
                        "extracted_text": "【系統提示】此檔案為圖則/PDF，已略過文字萃取以保持極速載入。"
                    }
                    db_data.append(new_record)
                    existing_map[original_name] = new_record
                    success_count += 1
                
                progress_bar.progress((idx + 1) / total_files)
                
            save_db(db_data)
            progress_bar.empty()
            
            if success_count > 0:
                st.success(f"🎉 成功極速歸檔 {success_count} 個全新檔案！")
            if replaced_count > 0:
                st.info(f"🔄 已自動完成取代與更新 {replaced_count} 個重複檔案。")

# ==========================================
# Tab 2: 統一整合列表（內嵌即時預覽、下載、批量管理）
# ==========================================
with tab2:
    st.subheader("📂 智能檢視、預覽與管理")
    
    db_data = load_db()

    if not db_data:
        st.info("暫無紀錄，請先上載 PDF。")
    else:
        search_kw = st.text_input("🔍 自由關鍵字搜尋（檔名）：", value="")
        filtered_data = db_data
        if search_kw:
            filtered_data = [item for item in db_data if search_kw.lower() in item['original_filename'].lower()]

        st.markdown("---")

        if filtered_data:
            def toggle_all_checkboxes():
                val = st.session_state.select_all_master
                for item in filtered_data:
                    st.session_state[f"chk_{item['id']}"] = val

            col_top1, col_top2 = st.columns([3, 2])
            with col_top1:
                st.checkbox("☑️ 全選目前顯示的檔案", key="select_all_master", on_change=toggle_all_checkboxes)
            
            selected_ids = []
            for item in filtered_data:
                chk_key = f"chk_{item['id']}"
                if chk_key not in st.session_state:
                    st.session_state[chk_key] = False
                if st.session_state[chk_key]:
                    selected_ids.append(item['id'])

            with col_top2:
                if selected_ids:
                    if st.button(f"🗑️ 刪除已選取嘅 {len(selected_ids)} 個檔案", type="primary", use_container_width=True):
                        db_data_updated = []
                        for item in db_data:
                            if item['id'] in selected_ids:
                                target_path = os.path.join(PDF_DIR, item['filename'])
                                if os.path.exists(target_path):
                                    os.remove(target_path)
                            else:
                                db_data_updated.append(item)
                        
                        save_db(db_data_updated)
                        for item in filtered_data:
                            st.session_state[f"chk_{item['id']}"] = False
                        st.success(f"🎉 成功刪除 {len(selected_ids)} 個檔案！")
                        st.rerun()

            st.markdown("---")

            for item in filtered_data:
                file_path = os.path.join(PDF_DIR, item['filename'])
                
                col_chk, col_exp = st.columns([0.6, 9.4])
                
                with col_chk:
                    st.write("") 
                    st.checkbox("", key=f"chk_{item['id']}", label_visibility="collapsed")
                    
                with col_exp:
                    with st.expander(f"📄 [ID: {item['id']}] {item['original_filename']} | 類別: {item.get('client_company', '未分類')}"):
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                pdf_bytes = f.read()
                                
                            # 轉換為 Base64 嵌入 HTML 進行網頁內嵌預覽
                            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="550px" type="application/pdf"></iframe>'
                            
                            st.markdown("🔍 **PDF 即時預覽：**")
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                            st.markdown("---")
                            
                            col_btn1, col_btn2, col_btn3 = st.columns([3, 3, 1.5])
                            with col_btn1:
                                st.download_button(
                                    label="📥 下載 PDF",
                                    data=pdf_bytes,
                                    file_name=item['original_filename'],
                                    mime="application/pdf",
                                    key=f"dl_{item['id']}"
                                )
                            with col_btn2:
                                share_text = f"🛠️ E&M Drawing/Quotation 參考分享 (Design by nikki 💅)：\n- 檔名: {item['original_filename']}"
                                encoded_share_text = urllib.parse.quote(share_text)
                                whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_share_text}"
                                st.markdown(
                                    f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:6px 12px; border:none; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">💬 WhatsApp 傳送</button></a>',
                                    unsafe_allow_html=True
                                )
                            with col_btn3:
                                if st.button("🗑️ 刪除", key=f"single_del_{item['id']}"):
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                    db_data = [d for d in db_data if d["id"] != item["id"]]
                                    save_db(db_data)
                                    st.success(f"已刪除：{item['original_filename']}")
                                    st.rerun()
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
