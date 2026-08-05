import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from google.genai.errors import APIError
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- 1. SETTING HALAMAN & BRANDING ---
st.set_page_config(
    page_title="UANGABIL TRACKER", 
    layout="wide", 
    page_icon="💳"
)

# Custom Styling UI Modern
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #0F172A; margin-bottom: 2px; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 20px; }
    
    .metric-card {
        background: #FFFFFF;
        padding: 16px 20px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #E2E8F0;
    }
    .metric-label { font-size: 0.85rem; font-weight: 600; color: #64748B; margin-bottom: 4px; }
    .metric-val { font-size: 1.5rem; font-weight: 800; color: #0F172A; }
    
    .target-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        padding: 20px 24px;
        border-radius: 18px;
        border: 1px solid #BFDBFE;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. INISIALISASI FIREBASE ---
if not firebase_admin._apps:
    key_dict = dict(st.secrets["firebase"])
    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 3. CONFIG PEMASUKAN & STRUKTUR KANTONG / POS ---
PEMASUKAN_BULANAN = 8183550  
TARGET_NIKAH = 100000000
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Simulasi Kantong Otomatis Berdasarkan 3 Pos Pengeluaran
STRUKTUR_PENGELUARAN = {
    "1. Pengeluaran Tetap & Masa Depan": {
        "Tabungan Nikah": 2700000,
        "Orang Tua (Cilacap)": 1000000,
        "Dana Darurat / Investasi": 300000
    },
    "2. Pengeluaran Berkala": {
        "Dana Tak Terduga": 383550
    },
    "3. Pengeluaran Dinamis / Variabel": {
        "Kebutuhan Pokok": 2000000,
        "Pacaran": 1100000,
        "Olahraga / Minsoc": 300000,
        "Keinginan Sendiri": 400000
    }
}

# Pemetaan Kategori ke Jenis Pos Pengeluaran
KATEGORI_KE_JENIS = {}
for jenis, kat_dict in STRUKTUR_PENGELUARAN.items():
    for kat in kat_dict.keys():
        KATEGORI_KE_JENIS[kat] = jenis

# --- 4. FUNGSIONALITAS DATABASE FIREBASE (CRUD) ---
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

# --- 5. SIDEBAR: INPUT TRANSAKSI CEPAT ---
st.sidebar.markdown("## 💳 **UANGABIL TRACKER**")
st.sidebar.caption("✨ Pocket-Based Financial System")
st.sidebar.markdown("---")

st.sidebar.subheader("➕ Catat Transaksi Kantong")

tgl = st.sidebar.date_input("📅 Tanggal Transaksi", datetime.now())

# Pilihan Pos Utama
jenis_selected = st.sidebar.selectbox("📂 Pos Kantong Utama", list(STRUKTUR_PENGELUARAN.keys()))

# Pilihan Kategori Kantong (Otomatis menyesuaikan)
kategori_options = list(STRUKTUR_PENGELUARAN[jenis_selected].keys())
kategori_selected = st.sidebar.selectbox("🏷️ Pilih Nama Kantong", kategori_options)

nominal = st.sidebar.number_input("💵 Nominal (Rp)", min_value=0, step=10000)
ket = st.sidebar.text_input("📝 Catatan / Keterangan", placeholder="Cth: Belanja Dapur, Coffe Shop, Minsoc")

if st.sidebar.button("🚀 Masukkan ke Kantong", use_container_width=True, type="primary"):
    if nominal > 0:
        simpan_transaksi(tgl, jenis_selected, kategori_selected, nominal, ket)
        st.sidebar.success("✅ Transaksi tersimpan ke Kantong!")
        st.rerun()
    else:
        st.sidebar.warning("Nominal harus lebih dari 0!")

st.sidebar.markdown("---")
st.sidebar.info("📍 **Samarinda**\n🎯 Target Akad Nikah: **2028**")

# --- 6. DASHBOARD UTAMA ---
st.markdown('<p class="main-title">👋 Selamat Datang di UANGABIL TRACKER!</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Kelola Kantong Keuanganmu secara otomatis & fleksibel.</p>', unsafe_allow_html=True)

df = ambil_semua_transaksi()

# Filter Data Bulan Ini
df_bln = pd.DataFrame()
total_pengeluaran_bln = 0

if not df.empty and 'tanggal' in df.columns:
    df['tanggal_dt'] = pd.to_datetime(df['tanggal'])
    bln_ini = datetime.now().month
    thn_ini = datetime.now().year
    df_bln = df[(df['tanggal_dt'].dt.month == bln_ini) & (df['tanggal_dt'].dt.year == thn_ini)]
    if not df_bln.empty:
        total_pengeluaran_bln = df_bln['nominal'].sum()

sisa_uang = PEMASUKAN_BULANAN - total_pengeluaran_bln

# Metric Ringkasan Kas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💵 Total Pemasukan</div>
        <div class="metric-val">Rp {PEMASUKAN_BULANAN:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💸 Total Terpakai</div>
        <div class="metric-val" style="color:#E11D48;">Rp {total_pengeluaran_bln:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💰 Sisa Kas Keseluruhan</div>
        <div class="metric-val" style="color:#2563EB;">Rp {sisa_uang:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    if sisa_uang > 0:
        st.markdown("""
        <div class="metric-card" style="background:#F0FDF4; border-color:#BBF7D0;">
            <div class="metric-label" style="color:#166534;">🟢 Status Kas</div>
            <div class="metric-val" style="color:#15803D;">SURPLUS</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="metric-card" style="background:#FEF2F2; border-color:#FECACA;">
            <div class="metric-label" style="color:#991B1B;">🔴 Status Kas</div>
            <div class="metric-val" style="color:#DC2626;">DEFISIT</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Progress Target Nikah
total_nikah = 0
if not df.empty and 'kategori' in df.columns:
    total_nikah = df[df['kategori'] == 'Tabungan Nikah']['nominal'].sum()

progress = min(float(total_nikah / TARGET_NIKAH), 1.0)
persen = progress * 100

st.markdown(f"""
<div class="target-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 1.15rem; font-weight: 700; color: #1E3A8A;">🎯 Target Kantong Nikah 2028</span>
        <span style="font-size: 1rem; font-weight: 800; color: #2563EB; background: #FFFFFF; padding: 4px 12px; border-radius: 20px;">{persen:.1f}% Terkumpul</span>
    </div>
    <div style="font-size: 1.7rem; font-weight: 800; color: #0F172A;">
        Rp {total_nikah:,.0f} <span style="font-size: 0.95rem; color: #64748B; font-weight: 500;">/ Target Rp 100,000,000</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.progress(progress)

st.markdown("---")

# TABS DASHBOARD: VIEW & UPDATE
tab1, tab2 = st.tabs(["📊 Visualisasi & AI Advisor", "✏️ Kelola & Revisi Transaksi"])

merged = pd.DataFrame()
if not df_bln.empty:
    summary = df_bln.groupby(['jenis_pengeluaran', 'kategori'])['nominal'].sum().reset_index()
    budget_df = pd.DataFrame([
        {"jenis_pengeluaran": j, "kategori": k, "Budget": b}
        for j, k_dict in STRUKTUR_PENGELUARAN.items()
        for k, b in k_dict.items()
    ])
    merged = pd.merge(budget_df, summary, on=['jenis_pengeluaran', 'kategori'], how='left').fillna(0)
    merged.rename(columns={'nominal': 'Realisasi'}, inplace=True)
    merged['Sisa_Kantong'] = merged['Budget'] - merged['Realisasi']

with tab1:
    col1, col2 = st.columns([1.2, 0.8])

    with col1:
        st.subheader("📊 Anggaran vs Penggunaan Per Kantong")
        if not merged.empty:
            fig = px.bar(
                merged, 
                x='kategori', 
                y=['Budget', 'Realisasi'], 
                color_discrete_sequence=['#CBD5E1', '#2563EB'],
                barmode='group',
                hover_data=['jenis_pengeluaran']
            )
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Rupiah (Rp)",
                legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=10, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(tickangle=-30)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 Belum ada data transaksi bulan ini.")

    with col2:
        st.subheader("🤖 UANGABIL AI Advisor")
        st.caption("Analisis otomatis alokasi kantong keuangan Anda.")
        
        if st.button("🔍 Minta Analisis AI", use_container_width=True, type="primary"):
            if not GEMINI_KEY:
                st.error("🔑 Atur GEMINI_API_KEY di Streamlit Secrets!")
            elif merged.empty:
                st.warning("⚠️ Belum ada data transaksi bulan ini.")
            else:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    data_text = merged[['jenis_pengeluaran', 'kategori', 'Budget', 'Realisasi', 'Sisa_Kantong']].to_string(index=False)
                    
                    prompt = f"""
                    Analisis keuangan bulanan UANGABIL TRACKER:
                    - Pemasukan Total: Rp {PEMASUKAN_BULANAN:,.0f}
                    - Total Pengeluaran: Rp {total_pengeluaran_bln:,.0f}
                    - Sisa Saldo Total: Rp {sisa_uang:,.0f}

                    Data Per Kantong:
                    {data_text}

                    Berikan evaluasi ramah dan praktis mengenai kantong mana yang masih aman dan mana yang harus diperketat pengeluarannya.
                    """
                    
                    with st.spinner("🧠 AI sedang menganalisis kantongmu..."):
                        response = client.models.generate_content(
                            model='gemini-2.0-flash',
                            contents=prompt,
                        )
                        if response and response.text:
                            st.markdown("---")
                            st.markdown(response.text)
                except APIError as e:
                    if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ Kuota API gratisan sedang penuh. Silakan tunggu 20 detik lalu coba lagi.")
                    else:
                        st.error(f"Error AI: {e.message}")
                except Exception as e:
                    st.error(f"Error AI: {e}")

# TAB 2: FITUR EDIT / REVISI TRANSAKSI
with tab2:
    st.subheader("✏️ Revisi / Update Transaksi Kantong")
    st.caption("Salah catat nominal atau ingin memindahkan pos kantong? Anda bisa mengubahnya di sini.")
    
    if not df.empty:
        # Pilih Transaksi yang mau diedit
        df['label_pilihan'] = df['tanggal'] + " | " + df['kategori'] + " | Rp " + df['nominal'].astype(str) + " (" + df['keterangan'].fillna('') + ")"
        pilihan_transaksi = st.selectbox("📌 Pilih Transaksi yang Ingin Di-Revisi:", df['label_pilihan'].tolist())
        
        selected_row = df[df['label_pilihan'] == pilihan_transaksi].iloc[0]
        
        st.markdown("---")
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            e_tgl = st.date_input("Tanggal", datetime.strptime(selected_row['tanggal'], "%Y-%m-%d"))
            e_jenis = st.selectbox("Pos Utama", list(STRUKTUR_PENGELUARAN.keys()), index=list(STRUKTUR_PENGELUARAN.keys()).index(selected_row['jenis_pengeluaran']) if selected_row['jenis_pengeluaran'] in STRUKTUR_PENGELUARAN else 0)
            e_kat_options = list(STRUKTUR_PENGELUARAN[e_jenis].keys())
            e_kat = st.selectbox("Nama Kantong", e_kat_options, index=e_kat_options.index(selected_row['kategori']) if selected_row['kategori'] in e_kat_options else 0)
        
        with col_edit2:
            e_nom = st.number_input("Nominal (Rp)", value=float(selected_row['nominal']), step=10000.0)
            e_ket = st.text_input("Keterangan Catatan", value=str(selected_row['keterangan']) if pd.notna(selected_row['keterangan']) else "")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("💾 Simpan Perubahan", use_container_width=True, type="primary"):
                    update_transaksi(selected_row['doc_id'], e_tgl, e_jenis, e_kat, e_nom, e_ket)
                    st.success("✅ Transaksi berhasil diperbarui!")
                    st.rerun()
            
            with col_btn2:
                if st.button("🗑️ Hapus Transaksi", use_container_width=True):
                    hapus_transaksi(selected_row['doc_id'])
                    st.warning("🗑️ Transaksi telah dihapus!")
                    st.rerun()

# Riwayat Transaksi Historis
st.markdown("---")
st.subheader("📑 Jurnal Transaksi Harian")

if not df.empty:
    df_display = df.copy()
    if 'nominal' in df_display.columns:
        df_display['nominal_fmt'] = df_display['nominal'].apply(lambda x: f"Rp {x:,.0f}")
    
    cols_order = [c for c in ['tanggal', 'jenis_pengeluaran', 'kategori', 'nominal_fmt', 'keterangan'] if c in df_display.columns]
    df_show = df_display[cols_order].sort_values(by='tanggal', ascending=False)
    
    st.dataframe(
        df_show, 
        use_container_width=True,
        column_config={
            "tanggal": st.column_config.TextColumn("📅 Tanggal"),
            "jenis_pengeluaran": st.column_config.TextColumn("📂 Pos Pengeluaran"),
            "kategori": st.column_config.TextColumn("🏷️ Nama Kantong"),
            "nominal_fmt": st.column_config.TextColumn("💵 Nominal"),
            "keterangan": st.column_config.TextColumn("📝 Keterangan")
        },
        hide_index=True
    )
