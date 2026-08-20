import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from google.genai.errors import APIError
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="UANGABIL TRACKER | Smart Money Management", 
    layout="wide", 
    page_icon="⚡"
)

# --- 2. SWITCH TEMA DESIGN (GEN Z CLEAN VS SOFT PASTEL) ---
st.sidebar.markdown("### 🎨 **UI THEME SELECTOR**")
tema_pilihan = st.sidebar.radio(
    "Pilih Mode Tampilan Dashboard:",
    ["⚡ Gen Z Pro FinTech (Clean Dark)", "🌸 Soft Pastel Aesthetic"]
)
st.sidebar.markdown("---")

# Pengaturan Variabel Visual & Warna Sesuai Theme
if "Gen Z Pro" in tema_pilihan:
    bg_main = "#0D1117"
    bg_card = "#161B22"
    border_card = "1px solid #30363D"
    color_title = "#58A6FF"
    color_sub = "#8B949E"
    color_label = "#8B949E"
    color_val = "#F0F6FC"
    gradient_target = "linear-gradient(135deg, #161B22 0%, #1F2937 100%)"
    border_target = "1px solid #38BDF8"
    color_bar = ['#30363D', '#38BDF8']
    
    title_app = "UANGABIL TRACKER ⚡"
    sub_title = "Smart Financial Command Center & Marriage Savings Milestone 2028 💍"
    label_inflow = "Total Income (Pemasukan) 💰"
    label_burn = "Total Expenses (Pengeluaran) 💸"
    label_sisa = "Net Cash Balance (Saldo) 💳"
    text_btn_simpan = "🚀 Record Transaction"
    text_btn_ai = "🧠 Run AI Financial Coach ⚡"
    text_btn_update = "💾 Save Changes"
    text_btn_hapus = "🗑️ Delete Record"
    msg_sidebar_footer = "⚡ **SMART MONEY MANAGEMENT FOR FUTURE FREEDOM**"
    
    lbl_tgl = "Tanggal Transaksi 📅"
    lbl_pos = "Pos Transaksi Utama 📑"
    lbl_kantong = "Nama Kantong / Kategori 🎯"
    lbl_nominal = "Nominal (Rp) 💵"
    lbl_ket = "Keterangan / Catatan 📝"
    status_aman = "🟢 Safe Budget"
    status_pas = "🟡 On Point"
    status_over = "🔴 Overbudget"

else:
    bg_main = "#FFFFFF"
    bg_card = "#FFF1F2"
    border_card = "2px solid #FFE4E6"
    color_title = "#881337"
    color_sub = "#9F1239"
    color_label = "#9F1239"
    color_val = "#4C0519"
    gradient_target = "linear-gradient(135deg, #FFF1F2 0%, #F0F9FF 100%)"
    border_target = "2px dashed #FDA4AF"
    color_bar = ['#FBCFE8', '#F43F5E']
    
    title_app = "UANGABIL TRACKER 🧸✨"
    sub_title = "Pemantauan Arus Kas Harian & Tabungan Pernikahan Tahun 2028 💒🌸"
    label_inflow = "Pemasukan Bulan Ini 🌸"
    label_burn = "Pengeluaran Bulan Ini 🛍️"
    label_sisa = "Sisa Saldo Kas 👛"
    text_btn_simpan = "💖 Simpan Transaksi ✨"
    text_btn_ai = "🔍 Minta Analisis Keuangan AI ✨"
    text_btn_update = "💾 Simpan Perubahan 🌸"
    text_btn_hapus = "🗑️ Hapus Transaksi 🥺"
    msg_sidebar_footer = "✨ **CATAT SEMUA PENGELUARANMU SECARA REAL TIME YAA!!** 🌸"
    
    lbl_tgl = "Tanggal Transaksi 📅"
    lbl_pos = "Pos Transaksi Utama 📑"
    lbl_kantong = "Nama Kantong / Kategori 👛"
    lbl_nominal = "Nominal Transaksi (Rp) 💸"
    lbl_ket = "Keterangan 📝"
    status_aman = "🟢 Aman ✨"
    status_pas = "🟡 Pas 🎯"
    status_over = "🔴 Overbudget 🥺"

# --- CSS RESPONSIVE & HIGH-END UI STYLING ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_main}; }}
    
    .main-title {{ 
        font-size: 2.2rem; 
        font-weight: 800; 
        color: {color_title}; 
        margin-bottom: 2px; 
        letter-spacing: -0.5px;
    }}
    .sub-title {{ 
        font-size: 0.95rem; 
        color: {color_sub}; 
        margin-bottom: 22px; 
        font-weight: 500;
    }}
    
    .metric-card {{ 
        background: {bg_card}; 
        padding: 18px 22px; 
        border-radius: 16px; 
        border: {border_card}; 
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}
    .metric-label {{ 
        font-size: 0.8rem; 
        font-weight: 700; 
        color: {color_label}; 
        margin-bottom: 6px; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .metric-val {{ 
        font-size: 1.55rem; 
        font-weight: 800; 
        color: {color_val}; 
        word-break: break-word; 
    }}
    
    .target-card {{ 
        background: {gradient_target}; 
        padding: 20px 24px; 
        border-radius: 16px; 
        border: {border_target}; 
        margin-bottom: 18px; 
    }}
    .target-header {{ 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 8px; 
    }}
    
    .stButton>button {{ 
        border-radius: 12px !important; 
        font-weight: 700 !important; 
        padding: 10px 18px !important; 
    }}

    @media (max-width: 768px) {{
        .main-title {{ font-size: 1.5rem !important; text-align: center; }}
        .sub-title {{ font-size: 0.8rem !important; text-align: center; margin-bottom: 16px; }}
        .metric-card {{ padding: 14px 16px !important; border-radius: 12px !important; }}
        .metric-label {{ font-size: 0.72rem !important; }}
        .metric-val {{ font-size: 1.25rem !important; }}
        .target-card {{ padding: 16px 18px !important; }}
        .target-header {{ flex-direction: column !important; align-items: flex-start !important; gap: 8px !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# --- 3. INISIALISASI FIREBASE ---
if not firebase_admin._apps:
    key_dict = dict(st.secrets["firebase"])
    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 4. KONFIGURASI ANGGARAN & MULTI-MILESTONE ---
PEMASUKAN_DEFAULT = 8183550  
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

PILIHAN_MISI = {
    "🎯 Milestone 1: DP Venue & Lamaran / Akad (Rp30.000.000)": 30000000,
    "💍 Milestone 2: Total Resepsi Pernikahan (Rp100.000.000)": 100000000
}

STRUKTUR_TRANSAKSI = {
    "0. Pemasukan Kas / Gaji": {
        "Gaji Pokok BMKG": 2938400,
        "Tunjangan Kinerja (Tukin)": 4595150,
        "Uang Makan / Tunjangan Lain": 650000,
        "Pemasukan Sampingan / Bonus": 0,
        "Sumber Pemasukan Lainnya": 0
    },
    "1. Pengeluaran Tetap & Masa Depan": {
        "Kantong Tabungan Nikah": 2500000,
        "Kantong Orang Tua (Cilacap)": 1000000,
        "Kantong Dana Darurat & Investasi": 300000
    },
    "2. Pengeluaran Berkala": {
        "Kantong Dana Tak Terduga": 383550
    },
    "3. Pengeluaran Dinamis / Variabel": {
        "Kantong Kebutuhan Pokok": 2000000,
        "Kantong Pacaran": 1000000,
        "Kantong Olahraga": 300000,
        "Kantong Keinginan Pribadi": 500000
    }
}

KATEGORI_KE_JENIS = {}
for jenis, kat_dict in STRUKTUR_TRANSAKSI.items():
    for kat in kat_dict.keys():
        KATEGORI_KE_JENIS[kat] = jenis

def format_rupiah(nominal):
    if pd.isna(nominal) or nominal is None:
        return "Rp0"
    return f"Rp{int(nominal):,}".replace(",", ".")

# --- 5. OPERASI DATABASE FIREBASE ---
def simpan_transaksi(tgl, jenis_pengeluaran, kategori, nominal, ket):
    doc_ref = db.collection("transaksi").document()
    doc_ref.set({
        "tanggal": tgl.strftime("%Y-%m-%d"),
        "jenis_pengeluaran": jenis_pengeluaran,
        "kategori": kategori,
        "nominal": float(nominal),
        "keterangan": ket,
        "created_at": firestore.SERVER_TIMESTAMP
    })

def update_transaksi(doc_id, tgl, jenis_pengeluaran, kategori, nominal, ket):
    doc_ref = db.collection("transaksi").document(doc_id)
    doc_ref.update({
        "tanggal": tgl.strftime("%Y-%m-%d"),
        "jenis_pengeluaran": jenis_pengeluaran,
        "kategori": kategori,
        "nominal": float(nominal),
        "keterangan": ket
    })

def hapus_transaksi(doc_id):
    db.collection("transaksi").document(doc_id).delete()

def ambil_semua_transaksi():
    docs = db.collection("transaksi").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d['doc_id'] = doc.id
        data.append(d)
    if data:
        df_temp = pd.DataFrame(data)
        if 'jenis_pengeluaran' not in df_temp.columns:
            df_temp['jenis_pengeluaran'] = df_temp['kategori'].map(KATEGORI_KE_JENIS).fillna("3. Pengeluaran Dinamis / Variabel")
        else:
            df_temp['jenis_pengeluaran'] = df_temp['jenis_pengeluaran'].fillna(
                df_temp['kategori'].map(KATEGORI_KE_JENIS)
            ).fillna("3. Pengeluaran Dinamis / Variabel")
            
        return df_temp
    return pd.DataFrame()

# --- 6. CHECK & NOTIFIKASI SUKSES ---
if "notif_sukses" in st.session_state:
    st.toast(st.session_state["notif_sukses"], icon="✅")
    st.success(st.session_state["notif_sukses"])
    del st.session_state["notif_sukses"]

# --- 7. SIDEBAR INPUT TRANSAKSI ---
st.sidebar.subheader("➕ Quick Transaction Entry ✏️")

tgl = st.sidebar.date_input(lbl_tgl, datetime.now())
jenis_selected = st.sidebar.selectbox(lbl_pos, list(STRUKTUR_TRANSAKSI.keys()))
kategori_options = list(STRUKTUR_TRANSAKSI[jenis_selected].keys())
kategori_selected = st.sidebar.selectbox(lbl_kantong, kategori_options)

nominal = st.sidebar.number_input(
    lbl_nominal, 
    min_value=0, 
    step=10000, 
    value=0
)

if nominal > 0:
    st.sidebar.info(f"Amount: **{format_rupiah(nominal)}** ✨")

ket = st.sidebar.text_input(lbl_ket, placeholder="Contoh: Gaji, bonus, bensin, coffee")

if st.sidebar.button(text_btn_simpan, use_container_width=True, type="primary"):
    if nominal > 0:
        simpan_transaksi(tgl, jenis_selected, kategori_selected, nominal, ket)
        st.session_state["notif_sukses"] = f"Transaksi {format_rupiah(nominal)} ke pos {kategori_selected} telah berhasil tersimpan! 🚀"
        st.rerun()
    else:
        st.sidebar.warning("Nominal transaksi harus lebih dari Rp0! ⚠️")

st.sidebar.markdown("---")
st.sidebar.info(msg_sidebar_footer)

# --- 8. DASHBOARD UTAMA & NERACA KAS ---
st.markdown(f'<p class="main-title">{title_app}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-title">{sub_title}</p>', unsafe_allow_html=True)

df = ambil_semua_transaksi()

df_bln = pd.DataFrame()
total_pemasukan_bln = 0
total_pengeluaran_bln = 0

if not df.empty and 'tanggal' in df.columns:
    df['tanggal_dt'] = pd.to_datetime(df['tanggal'])
    bln_ini = datetime.now().month
    thn_ini = datetime.now().year
    df_bln = df[(df['tanggal_dt'].dt.month == bln_ini) & (df['tanggal_dt'].dt.year == thn_ini)]
    
    if not df_bln.empty:
        df_pemasukan = df_bln[df_bln['jenis_pengeluaran'] == '0. Pemasukan Kas / Gaji']
        df_pengeluaran = df_bln[df_bln['jenis_pengeluaran'] != '0. Pemasukan Kas / Gaji']
        
        pemasukan_terinput = df_pemasukan['nominal'].sum() if not df_pemasukan.empty else 0
        total_pemasukan_bln = PEMASUKAN_DEFAULT + pemasukan_terinput
        total_pengeluaran_bln = df_pengeluaran['nominal'].sum() if not df_pengeluaran.empty else 0
    else:
        total_pemasukan_bln = PEMASUKAN_DEFAULT
else:
    total_pemasukan_bln = PEMASUKAN_DEFAULT

sisa_uang = total_pemasukan_bln - total_pengeluaran_bln

# Kartu Ikhtisar Neraca Kas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label_inflow}</div>
        <div class="metric-val" style="color:#10B981;">{format_rupiah(total_pemasukan_bln)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label_burn}</div>
        <div class="metric-val" style="color:#EF4444;">{format_rupiah(total_pengeluaran_bln)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label_sisa}</div>
        <div class="metric-val" style="color:#3B82F6;">{format_rupiah(sisa_uang)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    if sisa_uang > 0:
        st.markdown("""
        <div class="metric-card" style="background:#065F46; border-color:#059669;">
            <div class="metric-label" style="color:#A7F3D0;">Cashflow Status</div>
            <div class="metric-val" style="color:#34D399;">SURPLUS ⚡</div>
        </div>
        """, unsafe_allow_html=True)
    elif sisa_uang == 0:
        st.markdown("""
        <div class="metric-card" style="background:#1F2937; border-color:#4B5563;">
            <div class="metric-label" style="color:#9CA3AF;">Cashflow Status</div>
            <div class="metric-val" style="color:#F9FAFB;">BALANCED ⚖️</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="metric-card" style="background:#881337; border-color:#E11D48;">
            <div class="metric-label" style="color:#FECDD3;">Cashflow Status</div>
            <div class="metric-val" style="color:#FDA4AF;">DEFICIT 🚨</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- FITUR MULTI-MILESTONE NIKAH 2028 ---
total_nikah = 0
if not df.empty and 'kategori' in df.columns:
    total_nikah = df[df['kategori'].isin(['Kantong Tabungan Nikah', 'Tabungan Nikah'])]['nominal'].sum()

misi_terpilih_nama = st.selectbox(
    "🎯 **SELECT MARRIAGE SAVINGS MILESTONE:**",
    list(PILIHAN_MISI.keys())
)
target_nominal = PILIHAN_MISI[misi_terpilih_nama]

progress = min(float(total_nikah / target_nominal), 1.0)
persen = progress * 100

st.markdown(f"""
<div class="target-card">
    <div class="target-header">
        <span class="target-title" style="font-weight: 800; color: {color_title};">{misi_terpilih_nama.upper()}</span>
        <span style="font-size: 0.9rem; font-weight: 800; color: #38BDF8; background: #0D1117; padding: 5px 12px; border-radius: 8px;">{persen:.1f}% COMPLETED ✨</span>
    </div>
    <div class="target-val" style="font-weight: 800; color: {color_val};">
        {format_rupiah(total_nikah)} <span style="font-size: 0.85rem; color: {color_label}; font-weight: 600;">/ Goal {format_rupiah(target_nominal)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.progress(progress)

if total_nikah >= 30000000 and target_nominal == 30000000:
    st.balloons()
    st.success("🎉 **MILESTONE 1 ACHIEVED! (DP VENUE & LAMARAN Rp30.000.000 TUNTAS). READY FOR MILESTONE 2!** 💍✨")

st.markdown("---")

# TABEL TAB: VISUALISASI DAN KELOLA
tab1, tab2 = st.tabs(["📊 Analytics & AI Coach 🧠", "✏️ Manage & Edit Records 🛠️"])

merged = pd.DataFrame()
if not df_bln.empty:
    df_pengeluaran_bln = df_bln[df_bln['jenis_pengeluaran'] != '0. Pemasukan Kas / Gaji']
    summary = df_pengeluaran_bln.groupby(['jenis_pengeluaran', 'kategori'])['nominal'].sum().reset_index() if not df_pengeluaran_bln.empty else pd.DataFrame(columns=['jenis_pengeluaran', 'kategori', 'nominal'])
    
    budget_df = pd.DataFrame([
        {"jenis_pengeluaran": j, "kategori": k, "Anggaran": b}
        for j, k_dict in STRUKTUR_TRANSAKSI.items() if j != "0. Pemasukan Kas / Gaji"
        for k, b in k_dict.items()
    ])
    
    merged = pd.merge(budget_df, summary, on=['jenis_pengeluaran', 'kategori'], how='left').fillna(0)
    merged.rename(columns={'nominal': 'Realisasi'}, inplace=True)
    merged['Sisa_Anggaran'] = merged['Anggaran'] - merged['Realisasi']
    
    def hitung_status_otomatis(row):
        sisa = row['Sisa_Anggaran']
        if sisa > 0:
            return status_aman
        elif sisa == 0:
            return status_pas
        else:
            return status_over
            
    merged['Status_Otomatis'] = merged.apply(hitung_status_otomatis, axis=1)

with tab1:
    col1, col2 = st.columns([1.25, 0.75])

    with col1:
        st.subheader("📊 Expense Budget vs Actual Usage 🎨")
        if not merged.empty:
            fig = px.bar(
                merged, 
                x='kategori', 
                y=['Anggaran', 'Realisasi'], 
                color_discrete_sequence=color_bar,
                barmode='group',
                hover_data={
                    'jenis_pengeluaran': True,
                    'Sisa_Anggaran': True,
                    'Status_Otomatis': True
                },
                labels={'kategori': 'Nama Pos', 'value': 'Nominal (Rp)', 'variable': 'Kategori'}
            )
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Nominal (Rupiah)",
                legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=10, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickangle=-30)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("##### 📌 Budget Limit Remaining & Auto Status ⚡")
            df_tabel_sisa = merged.copy()
            df_tabel_sisa['Anggaran_Fmt'] = df_tabel_sisa['Anggaran'].apply(format_rupiah)
            df_tabel_sisa['Realisasi_Fmt'] = df_tabel_sisa['Realisasi'].apply(format_rupiah)
            df_tabel_sisa['Sisa_Fmt'] = df_tabel_sisa['Sisa_Anggaran'].apply(format_rupiah)
            
            st.dataframe(
                df_tabel_sisa[['kategori', 'Anggaran_Fmt', 'Realisasi_Fmt', 'Sisa_Fmt', 'Status_Otomatis']],
                use_container_width=True,
                column_config={
                    "kategori": st.column_config.TextColumn("Nama Pos / Kantong 🎯"),
                    "Anggaran_Fmt": st.column_config.TextColumn("Limit Anggaran 💰"),
                    "Realisasi_Fmt": st.column_config.TextColumn("Terpakai 💸"),
                    "Sisa_Fmt": st.column_config.TextColumn("Sisa Limit ⚡"),
                    "Status_Otomatis": st.column_config.TextColumn("Status 🚨")
                },
                hide_index=True
            )
        else:
            st.info("💡 Belum terdapat data pengeluaran pada bulan berjalan.")

    with col2:
        st.subheader("🤖 AI Financial Coach 🧠")
        st.caption("Analisis pintar otomatis berbasis posisi keuangan kamu.")
        
        if st.button(text_btn_ai, use_container_width=True, type="primary"):
            if not GEMINI_KEY:
                st.error("🔑 GEMINI_API_KEY belum terpasang di Secrets! ⚠️")
            else:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    data_text = merged[['jenis_pengeluaran', 'kategori', 'Anggaran', 'Realisasi', 'Sisa_Anggaran', 'Status_Otomatis']].to_string(index=False) if not merged.empty else "Belum ada pengeluaran."
                    
                    prompt = f"""
                    Analisis Keuangan Bulanan UANGABIL TRACKER:
                    - Total Pemasukan Terinput Bulan Ini: {format_rupiah(total_pemasukan_bln)}
                    - Total Pengeluaran Bulan Ini: {format_rupiah(total_pengeluaran_bln)}
                    - Sisa Saldo Kas: {format_rupiah(sisa_uang)}
                    - Progress Tabungan Nikah: {format_rupiah(total_nikah)} (Milestone Fokus: {misi_terpilih_nama})

                    Data Per Pos Pengeluaran, Sisa Alokasi & Status Otomatisnya:
                    {data_text}

                    Berikan evaluasi yang taktis, komunikatif, profesional, dan relevan dengan gaya Gen Z modern. Berikan rekomendasi alokasi yang cerdas.
                    """
                    
                    with st.spinner("AI FINANCIAL COACH IS ANALYZING YOUR DATA... 🧠⚡"):
                        # DAFTAR ID MODEL RESMI GOOGLE GEMINI DENGAN FALLBACK
                        available_models = [
                            'gemini-3.7-flash', 
                            'gemini-3.6-flash', 
                            'gemini-3.5-flash', 
                            'gemini-flash-latest'
                        ]
                        response = None
                        
                        for model_name in available_models:
                            try:
                                response = client.models.generate_content(
                                    model=model_name,
                                    contents=prompt,
                                )
                                if response and response.text:
                                    break
                            except Exception:
                                continue
                                
                        if response and response.text:
                            st.markdown("---")
                            st.markdown(response.text)
                        else:
                            st.error("Gagal mendapat respons dari AI Gemini API. Periksa kembali API Key kamu.")

                except APIError as e:
                    if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ BATAS API GRATIS TERCAPAI. HARAP TUNGGU 30 DETIK YA! ⚠️")
                    else:
                        st.error(f"Kesalahan API: {e.message}")
                except Exception as e:
                    st.error(f"Kesalahan Sistem: {e}")

# TAB 2: REVISI TRANSAKSI
with tab2:
    st.subheader("✏️ Manage & Edit Transaction 🛠️")
    st.caption("Koreksi atau perbarui data transaksi kas dengan mudah.")
    
    if not df.empty:
        df['label_pilihan'] = df['tanggal'] + " | " + df['kategori'] + " | " + df['nominal'].apply(format_rupiah) + " (" + df['keterangan'].fillna('') + ")"
        pilihan_transaksi = st.selectbox("📌 Pilih Transaksi yang Ingin Diperbarui:", df['label_pilihan'].tolist())
        
        selected_row = df[df['label_pilihan'] == pilihan_transaksi].iloc[0]
        
        st.markdown("---")
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            e_tgl = st.date_input(lbl_tgl, datetime.strptime(selected_row['tanggal'], "%Y-%m-%d"))
            e_jenis = st.selectbox(lbl_pos, list(STRUKTUR_TRANSAKSI.keys()), index=list(STRUKTUR_TRANSAKSI.keys()).index(selected_row['jenis_pengeluaran']) if selected_row['jenis_pengeluaran'] in STRUKTUR_TRANSAKSI else 0)
            e_kat_options = list(STRUKTUR_TRANSAKSI[e_jenis].keys())
            e_kat = st.selectbox(lbl_kantong, e_kat_options, index=e_kat_options.index(selected_row['kategori']) if selected_row['kategori'] in e_kat_options else 0)
        
        with col_edit2:
            e_nom = st.number_input(lbl_nominal, value=int(selected_row['nominal']), step=10000)
            st.info(f"Nominal: **{format_rupiah(e_nom)}** ✨")
            
            e_ket = st.text_input(lbl_ket, value=str(selected_row['keterangan']) if pd.notna(selected_row['keterangan']) else "")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button(text_btn_update, use_container_width=True, type="primary"):
                    update_transaksi(selected_row['doc_id'], e_tgl, e_jenis, e_kat, e_nom, e_ket)
                    st.session_state["notif_sukses"] = f"Data transaksi {selected_row['kategori']} berhasil diperbarui! ✨"
                    st.rerun()
            
            with col_btn2:
                if st.button(text_btn_hapus, use_container_width=True):
                    hapus_transaksi(selected_row['doc_id'])
                    st.session_state["notif_sukses"] = "Data transaksi berhasil dihapus! 🗑️"
                    st.rerun()

# --- 9. JURNAL TRANSAKSI HARIAN ---
st.markdown("---")
st.subheader("📑 TRANSACTION JOURNAL DATABASE (FIRESTORE CLOUD) 📊⚡")

if not df.empty:
    df_display = df.copy()
    if 'nominal' in df_display.columns:
        df_display['nominal_fmt'] = df_display['nominal'].apply(format_rupiah)
    
    daftar_pos = ["Semua Pos Transaksi"] + list(STRUKTUR_TRANSAKSI.keys())
    pos_filter = st.selectbox("🔍 Filter Berdasarkan Kelompok Pos Transaksi:", daftar_pos)
    
    if pos_filter != "Semua Pos Transaksi":
        df_filtered = df_display[df_display['jenis_pengeluaran'] == pos_filter]
    else:
        df_filtered = df_display

    total_nominal_kelompok = df_filtered['nominal'].sum() if not df_filtered.empty else 0
    st.caption(f"Menampilkan **{len(df_filtered)}** transaksi | Total Akumulasi: **{format_rupiah(total_nominal_kelompok)}** ✨")
    
    cols_order = [c for c in ['tanggal', 'jenis_pengeluaran', 'kategori', 'nominal_fmt', 'keterangan'] if c in df_filtered.columns]
    df_show = df_filtered[cols_order].sort_values(by='tanggal', ascending=False)
    
    st.dataframe(
        df_show, 
        use_container_width=True,
        column_config={
            "tanggal": st.column_config.TextColumn("Tanggal 📅"),
            "jenis_pengeluaran": st.column_config.TextColumn("Pos Transaksi Utama 📑"),
            "kategori": st.column_config.TextColumn("Nama Pos 🎯"),
            "nominal_fmt": st.column_config.TextColumn("Nominal Transaksi 💵"),
            "keterangan": st.column_config.TextColumn("Keterangan 📝")
        },
        hide_index=True
    )
else:
    st.caption("Belum ada riwayat transaksi tersimpan. ✨")
