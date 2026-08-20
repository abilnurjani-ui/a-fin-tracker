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
    page_title="UANGABIL TRACKER 💳✨", 
    layout="wide", 
    page_icon="💳"
)

# --- 2. FITUR SWITCH TEMA (MASKULIN GAHAR VS UNYU IMUT) ---
st.sidebar.markdown("### 🎨 **PILIH TEMA TAMPILAN** 🎭")
tema_pilihan = st.sidebar.radio(
    "Gaya Tampilan Aplikasi:",
    ["🔥 Maskulin Gahar (Cyberpunk Dark)", "🎀 Unyu Imut (Soft Pastel)"]
)
st.sidebar.markdown("---")

# Mengatur Variabel Styling & Emoji berdasarkan Pilihan Tema
if "Maskulin" in tema_pilihan:
    bg_main = "#09090B"
    bg_card = "#121215"
    border_card = "2px solid #27272A"
    color_title = "#00F2FE"
    color_sub = "#A1A1AA"
    color_label = "#71717A"
    color_val = "#FFFFFF"
    gradient_target = "linear-gradient(135deg, #09090B 0%, #18181B 100%)"
    border_target = "2px solid #00F2FE"
    color_bar = ['#27272A', '#00F2FE']
    
    title_app = "UANGABIL TRACKER 🏎️⚡"
    sub_title = "FINANCIAL COMMAND CENTER | TARGET MISSION: NIKAH 2028 💍🔥"
    label_inflow = "TOTAL INFLOW (CUAN) 💰"
    label_burn = "BURN RATE (PENGELUARAN) 💸"
    label_sisa = "NET LIQUIDITY (SALDO) 💳"
    text_btn_simpan = "🚀 EXECUTE TRANSAKSI 🔥"
    text_btn_ai = "🧠 MINTA STRATEGI TAKTIS AI ⚡"
    text_btn_update = "💾 UPDATE DATA 👊"
    text_btn_hapus = "DESTROY TRANSAKSI 💣"
    msg_sidebar_footer = "⚡ **NO MERCY UNTUK BOROS! KUASAI FINANCIAL FREEDOM!** 🏁"
    
    lbl_tgl = "TANGGAL TRANSAKSI 📅"
    lbl_pos = "POS TRANSAKSI UTAMA 📑"
    lbl_kantong = "NAMA POS / KANTONG 🎯"
    lbl_nominal = "NOMINAL (RP) 💵"
    lbl_ket = "KETERANGAN / LOG 📝"
    status_aman = "🟢 SAFE ZONE 🔥"
    status_pas = "🟡 ON POINT 🎯"
    status_over = "🔴 DANGER OVERBUDGET 🚨"

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

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_main}; }}
    .main-title {{ font-size: 2.3rem; font-weight: 900; color: {color_title}; margin-bottom: 2px; }}
    .sub-title {{ font-size: 1rem; color: {color_sub}; margin-bottom: 22px; font-weight: 700; }}
    .metric-card {{ background: {bg_card}; padding: 18px 22px; border-radius: 14px; border: {border_card}; }}
    .metric-label {{ font-size: 0.85rem; font-weight: 900; color: {color_label}; margin-bottom: 6px; }}
    .metric-val {{ font-size: 1.6rem; font-weight: 900; color: {color_val}; }}
    .target-card {{ background: {gradient_target}; padding: 22px 26px; border-radius: 16px; border: {border_target}; margin-bottom: 18px; }}
    .stButton>button {{ border-radius: 10px !important; font-weight: 900 !important; padding: 10px 20px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. INISIALISASI FIREBASE ---
if not firebase_admin._apps:
    key_dict = dict(st.secrets["firebase"])
    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 4. KONFIGURASI ANGGARAN & KANTONG KEUANGAN ---
PEMASUKAN_DEFAULT = 8183550  
TARGET_NIKAH = 100000000
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

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

# --- 5. INTERAKSI DATABASE FIREBASE ---
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
        if 'jenis_pengeluaran' not in df_temp.columns and 'kategori' in df_temp.columns:
            df_temp['jenis_pengeluaran'] = df_temp['kategori'].map(KATEGORI_KE_JENIS).fillna("3. Pengeluaran Dinamis / Variabel")
        return df_temp
    return pd.DataFrame()

# --- 6. CHECK & TAMPILKAN NOTIFIKASI POP-UP ---
if "notif_sukses" in st.session_state:
    st.toast(st.session_state["notif_sukses"], icon="✅")
    st.success(st.session_state["notif_sukses"])
    del st.session_state["notif_sukses"]

# --- 7. BILAH SISI (SIDEBAR): INPUT TRANSAKSI ---
st.sidebar.subheader("➕ Catat Transaksi Baru ✏️")

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
    st.sidebar.info(f"Nominal: **{format_rupiah(nominal)}** ✨")

ket = st.sidebar.text_input(lbl_ket, placeholder="Contoh: Gaji, bonus, belanja, kopi")

if st.sidebar.button(text_btn_simpan, use_container_width=True, type="primary"):
    if nominal > 0:
        simpan_transaksi(tgl, jenis_selected, kategori_selected, nominal, ket)
        st.session_state["notif_sukses"] = f"Berhasil! Transaksi {format_rupiah(nominal)} pada {kategori_selected} telah dicatat ke cloud database! 🚀"
        st.rerun()
    else:
        st.sidebar.warning("Nominal transaksi kudu lebih dari Rp0! ⚠️")

st.sidebar.markdown("---")
st.sidebar.info(msg_sidebar_footer)

# --- 8. DASHBOARD UTAMA & PERHITUNGAN NERACA SALDO ---
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
        
        total_pemasukan_bln = df_pemasukan['nominal'].sum() if not df_pemasukan.empty else PEMASUKAN_DEFAULT
        total_pengeluaran_bln = df_pengeluaran['nominal'].sum() if not df_pengeluaran.empty else 0
    else:
        total_pemasukan_bln = PEMASUKAN_DEFAULT
else:
    total_pemasukan_bln = PEMASUKAN_DEFAULT

sisa_uang = total_pemasukan_bln - total_pengeluaran_bln

# Kartu Ringkasan Neraca Kas
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
        <div class="metric-card" style="background:#064E3B; border-color:#059669;">
            <div class="metric-label" style="color:#6EE7B7;">STATUS CASHFLOW 🔥</div>
            <div class="metric-val" style="color:#34D399;">SURPLUS 🏁</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="metric-card" style="background:#4C0519; border-color:#9F1239;">
            <div class="metric-label" style="color:#FECDD3;">STATUS CASHFLOW ⚠️</div>
            <div class="metric-val" style="color:#F43F5E;">DEFISIT 🚨</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Target Tabungan Pernikahan
total_nikah = 0
if not df.empty and 'kategori' in df.columns:
    total_nikah = df[df['kategori'].isin(['Kantong Tabungan Nikah', 'Tabungan Nikah'])]['nominal'].sum()

progress = min(float(total_nikah / TARGET_NIKAH), 1.0)
persen = progress * 100

st.markdown(f"""
<div class="target-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 1.15rem; font-weight: 900; color: {color_title};">🎯 MISSION: NIKAH 2028 💍🔥</span>
        <span style="font-size: 0.95rem; font-weight: 900; color: #0284C7; background: #F8FAFC; padding: 6px 14px; border-radius: 10px;">{persen:.1f}% UNLOCKED ⚡</span>
    </div>
    <div style="font-size: 1.65rem; font-weight: 900; color: {color_val};">
        {format_rupiah(total_nikah)} <span style="font-size: 0.9rem; color: {color_label}; font-weight: 700;">/ Goal {format_rupiah(TARGET_NIKAH)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.progress(progress)

st.markdown("---")

# TABEL TAB: VISUALISASI DAN KELOLA
tab1, tab2 = st.tabs(["📊 ANALYTICS & AI ADVISOR 🧠", "✏️ EDIT & ADJUST TRANSAKSI 🛠️"])

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
        st.subheader("📊 PERBANDINGAN ANGGARAN VS REALISASI PENGELUARAN 🎨")
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
            
            st.markdown("##### 📌 RINCIAN SISA LIMIT ANGGARAN PENGELUARAN ⚡")
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
        st.subheader("🤖 AI FINANCIAL COMMANDER 🧠")
        st.caption("Analisis taktis otomatis berbasis kondisi finansial lo.")
        
        if st.button(text_btn_ai, use_container_width=True, type="primary"):
            if not GEMINI_KEY:
                st.error("🔑 GEMINI_API_KEY belum terpasang Bro! ⚠️")
            else:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    data_text = merged[['jenis_pengeluaran', 'kategori', 'Anggaran', 'Realisasi', 'Sisa_Anggaran', 'Status_Otomatis']].to_string(index=False) if not merged.empty else "Belum ada pengeluaran."
                    
                    prompt = f"""
                    Analisis Keuangan Bulanan UANGABIL TRACKER:
                    - Total Pemasukan Terinput Bulan Ini: {format_rupiah(total_pemasukan_bln)}
                    - Total Pengeluaran Bulan Ini: {format_rupiah(total_pengeluaran_bln)}
                    - Sisa Saldo Kas: {format_rupiah(sisa_uang)}

                    Data Per Pos Pengeluaran, Sisa Alokasi & Status Otomatisnya:
                    {data_text}

                    Berikan evaluasi yang lugas, tegas, maskulin, gahar, dan obyektif mengenai kondisi finansial ini. Berikan rekomendasi hemat taktis.
                    """
                    
                    with st.spinner("AI FINANCIAL COMMANDER SEDANG MENGAKSES STRATEGI... 🧠⚡"):
                        response = client.models.generate_content(
                            model='gemini-2.0-flash',
                            contents=prompt,
                        )
                        if response and response.text:
                            st.markdown("---")
                            st.markdown(response.text)
                except APIError as e:
                    if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ BATAS API GRATIS TERCAPAI. TUNGGU 30 DETIK BRO! ⚠️")
                    else:
                        st.error(f"Kesalahan API: {e.message}")
                except Exception as e:
                    st.error(f"Kesalahan Sistem: {e}")

# TAB 2: REVISI TRANSAKSI
with tab2:
    st.subheader("✏️ EDIT & ADJUST TRANSAKSI 🛠️")
    st.caption("Fasilitas koreksi data transaksi keuangan (Pemasukan maupun Pengeluaran).")
    
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
            st.info(f"Nominal: **{format_rupiah(e_nom)}** 🔥")
            
            e_ket = st.text_input(lbl_ket, value=str(selected_row['keterangan']) if pd.notna(selected_row['keterangan']) else "")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button(text_btn_update, use_container_width=True, type="primary"):
                    update_transaksi(selected_row['doc_id'], e_tgl, e_jenis, e_kat, e_nom, e_ket)
                    st.session_state["notif_sukses"] = f"Perubahan data transaksi {selected_row['kategori']} berhasil diperbarui! 🔥"
                    st.rerun()
            
            with col_btn2:
                if st.button(text_btn_hapus, use_container_width=True):
                    hapus_transaksi(selected_row['doc_id'])
                    st.session_state["notif_sukses"] = "Data transaksi berhasil dihapus dari cloud database! 🗑️"
                    st.rerun()

# --- 9. JURNAL TRANSAKSI HARIAN ---
st.markdown("---")
st.subheader("📑 DATABASE JURNAL TRANSAKSI (FIRESTORE CLOUD) 📊⚡")

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
    st.caption(f"Menampilkan **{len(df_filtered)}** transaksi | Total Akumulasi: **{format_rupiah(total_nominal_kelompok)}** 🔥")
    
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
    st.caption("Belum ada riwayat transaksi tersimpan Bro! 🏁")
