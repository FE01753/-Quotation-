import streamlit as st
import pandas as pd
import os
import json
import urllib.parse
from datetime import datetime

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

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
THUMB_DIR = "quotations_thumbnail_storage"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)
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

# 生成縮圖函數
def generate_thumbnail(pdf_path, thumb_path):
    if not HAS_PYMUPDF:
        return False
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            page = doc[0]
            pix = page.get_pixmap(dpi=72)
            pix.save(thumb_path)
        doc.close()
        return True
    except Exception:
        return False

# 智能提取 PDF 內容與 Work Description (精準捕捉 Re: 標題)
def parse_pdf_content(file_path, original_name):
    is_drawing = any(k in original_name.upper() for k in ["PLAN", "DWG", "CSD", "LAYOUT"])
    if is_drawing or not HAS_PYMUPDF:
        return "圖則/未分類", clean_name_fallback(original_name), "【系統提示】此檔案為圖則/PDF。"

    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        extracted_desc = ""
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        
        # 1. 優先尋找 "Re:" 或 "SUBJECT:" 後面嘅字眼（工程 Quotation 最準確嘅 Work Description）
        for i, line in enumerate(lines):
            if line.lower().startswith("re:") or line.lower().startswith("subject:"):
                # 提取 Re: 後面嘅內容
                content = line.split(":", 1)[1].strip()
                # 如果同一行已經有好長嘅描述
                if len(content) > 5:
                    extracted_desc = content
                    # 順便把下面連埋一齊嘅行（如果有換行）接埋落去
                    for next_line in lines[i+1 : i+3]:
                        if next_line.lower().startswith("as per") or next_line.lower().startswith("dear") or ":" in next_line:
                            break
                        extracted_desc += " " + next_line
                    break

        # 2. 如果搵唔到 Re:，試尋找 "Dear Sir/Madam" 下面嘅字眼
        if not extracted_desc:
            for i, line in enumerate(lines):
                if "dear sir" in line.lower() or "madam" in line.lower():
                    desc_candidates = lines[i+1 : i+4]
                    if desc_candidates:
                        extracted_desc = " ".join(desc_candidates)
                        break
        
        # 3. 如果都搵唔用，試 "Description"
        if not extracted_desc:
            for i, line in enumerate(lines):
                if "description" in line.lower():
                    desc_candidates = lines[i+1 : i+3]
                    if desc_candidates:
                        extracted_desc = " ".join(desc_candidates)
                        break

        # 4. Fallback 用檔名
        if not extracted_desc or len(extracted_desc) < 3:
            extracted_desc = clean_name_fallback(original_name)

        # 限制長度避免太長
        if len(extracted_desc) > 90:
            extracted_desc = extracted_desc[:87] + "..."

        return extracted_desc, extracted_desc, full_text[:500]

    except Exception:
        return clean_name_fallback(original_name), clean_name_fallback(original_name), "解析失敗"

def clean_name_fallback(name):
    base = os.path.splitext(name)[0]
    return base

# --- App 標題與分頁 ---
st.title("📁 智能工程 Quotation 檔案管理系統")
st.caption("✨ System curated & Design by nikki 💅")
st.write("批量上傳 PDF，精準捕捉 Re: Work Description，享受極速預覽！")

tab1, tab2 = st.tabs(["📤 批量上載與智能分析", "📂 智能檢視、預覽與管理"])

# ==========================================
# Tab 1: 批量上載與智能分析
# ==========================================
with tab1:
    st.subheader("📤 批量上載 Quotation / Drawing PDF 檔案")
    uploaded_pdfs = st.file_uploader("選擇多個 PDF 檔案", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_pdfs:
        st.info(f"已選取 {len(uploaded_pdfs)} 個檔案準備上載。")
    
    if st.button("🚀 開始智能批量歸檔", type="primary"):
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
                
                temp_save_path = os.path.join(PDF_DIR, "temp_" + original_name)
                with open(temp_save_path, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())

                work_desc, project_name, extracted_text = parse_pdf_content(temp_save_path, original_name)

                if original_name in existing_map:
                    record = existing_map[original_name]
                    filename = record["filename"]
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    os.replace(temp_save_path, file_path)
                    
                    thumb_filename = f"thumb_{os.path.splitext(filename)[0]}.png"
                    thumb_path = os.path.join(THUMB_DIR, thumb_filename)
                    generate_thumbnail(file_path, thumb_path)
                    
                    record["date"] = str(datetime.today().date())
                    record["project_name"] = project_name
                    record["client_company"] = work_desc
                    record["thumb_filename"] = thumb_filename
                    replaced_count += 1
                else:
                    new_id = (db_data[-1]["id"] + 1) if db_data else 1
                    filename = f"q_{new_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
                    file_path = os.path.join(PDF_DIR, filename)
                    
                    os.replace(temp_save_path, file_path)
                    
                    thumb_filename = f"thumb_q_{new_id}.png"
                    thumb_path = os.path.join(THUMB_DIR, thumb_filename)
                    generate_thumbnail(file_path, thumb_path)
                    
                    new_record = {
                        "id": new_id,
                        "date": str(datetime.today().date()),
                        "project_name": project_name,
                        "client_company": work_desc,
                        "attention_name": "未偵測",
                        "amount": "未偵測",
                        "filename": filename,
                        "original_filename": original_name,
                        "thumb_filename": thumb_filename,
                        "extracted_text": extracted_text
                    }
                    db_data.append(new_record)
                    existing_map[original_name] = new_record
                    success_count += 1
                
                progress_bar.progress((idx + 1) / total_files)
                
            save_db(db_data)
            progress_bar.empty()
            
            if success_count > 0:
                st.success(f"🎉 成功智能歸檔 {success_count} 個檔案！")
            if replaced_count > 0:
                st.info(f"🔄 已自動完成取代與更新 {replaced_count} 個重複檔案。")

# ==========================================
# Tab 2: 統一整合列表（智能搜尋 Work Description）
# ==========================================
with tab2:
    st.subheader("📂 智能檢視、預覽與管理")
    
    db_data = load_db()

    if not db_data:
        st.info("暫無紀錄，請先上載 PDF。")
    else:
        search_kw = st.text_input("🔍 自由關鍵字搜尋（可搜檔名或 Work Description）：", value="")
        filtered_data = db_data
        if search_kw:
            filtered_data = [
                item for item in db_data 
                if search_kw.lower() in item['original_filename'].lower() or search_kw.lower() in item.get('client_company', '').lower()
            ]

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
                                if "thumb_filename" in item:
                                    thumb_path = os.path.join(THUMB_DIR, item['thumb_filename'])
                                    if os.path.exists(thumb_path):
                                        os.remove(thumb_path)
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
                    work_desc_display = item.get('client_company', '未分類')
                    with st.expander(f"📄 [ID: {item['id']}] {item['original_filename']} | 🛠️ {work_desc_display}"):
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                pdf_bytes = f.read()
                                
                            st.markdown("⚡ **網頁秒開預覽：**")
                            
                            thumb_file = item.get("thumb_filename")
                            thumb_path = os.path.join(THUMB_DIR, thumb_file) if thumb_file else ""
                            
                            if not thumb_file or not os.path.exists(thumb_path):
                                thumb_file = f"thumb_auto_{item['id']}.png"
                                thumb_path = os.path.join(THUMB_DIR, thumb_file)
                                generate_thumbnail(file_path, thumb_path)
                                item["thumb_filename"] = thumb_file
                                save_db(db_data)

                            if os.path.exists(thumb_path):
                                st.image(thumb_path, caption=f"Work Description: {work_desc_display}", use_container_width=True)
                            else:
                                st.warning("無法顯示預覽圖。")

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
                                share_text = f"🛠️ E&M Work Description (Design by nikki 💅)：\n- 項目: {work_desc_display}\n- 檔名: {item['original_filename']}"
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
                                    if thumb_file and os.path.exists(thumb_path):
                                        os.remove(thumb_path)
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
