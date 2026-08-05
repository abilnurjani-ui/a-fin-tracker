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
    page_icon="💍"
)

# Custom Styling UI Modern & Visual Interaktif
st.markdown("""
    <style>
    /* Global Typography */
    .main-title { font-size: 2.2rem; font-weight: 800; color: #0F172A; margin-bottom: 2px; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 20px; }
    
    /* Card Metric Modern */
    .metric-card {
        background: #FFFFFF;
        padding: 16px 20px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #E2E8F0;
    }
    .metric-label { font-size: 0.85rem; font-weight: 600; color: #64748B; margin-bottom: 4px; }
    .metric-val { font-size: 1.5rem; font-weight: 800; color: #0F172A; }
    
    /* Target Nikah Card */
    .target-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        padding: 20px 24px;
        border-radius: 18px;
        border: 1px solid #BFDBFE;
        margin-bottom: 15px;
    }

    /* Container Styling */
    div[data-testid="stBlock"] {
        border-radius: 16px;
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

# --- 3. CONFIG PEMASUKAN & STRUKTUR 3 POS PENGELUARAN ---
PEMASUKAN_BULANAN = 8183550  # Gaji + Tukin + Uang Makan
TARGET_NIKAH = 100000000
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Struktur Pengelompokan 3 Pos Pengeluaran Utama
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

# Pemetaan Kategori ke Jenis Pengeluaran
KATEGORI_KE_JENIS = {}
for jenis, kat_dict in STRUKTUR_PENGELUARAN.items():
    for kat in kat_dict.keys():
        KATEGORI_KE_JENIS[kat] = jenis

# --- 4. FUNGSIONALITAS DATABASE FIREBASE ---
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

def ambil_semua_transaksi():
    docs = db.collection("transaksi").stream()
    data = [doc.to_dict() for doc in docs]
    if data:
        df_temp = pd.DataFrame(data)
        if 'jenis_pengeluaran' not in df_temp.columns and 'kategori' in df_temp.columns:
            df_temp['jenis_pengeluaran'] = df_temp['kategori'].map(KATEGORI_KE_JENIS).fillna("3. Pengeluaran Dinamis / Variabel")
        return df_temp
    return pd.DataFrame()

# --- 5. SIDEBAR: INPUT DINAMIS ---
st.sidebar.markdown("## 💳 **UANGABIL TRACKER**")
st.sidebar.caption("✨ Personal Financial Command Center")
st.sidebar.markdown("---")

st.sidebar.subheader("➕ Catat Transaksi Baru")

tgl = st.sidebar.date_input("📅 Tanggal Transaksi", datetime.now())

# Selection 1: Jenis Pos Pengeluaran
jenis_selected = st.sidebar.selectbox("📂 Jenis Pengeluaran", list(STRUKTUR_PENGELUARAN.keys()))

# Selection 2: Kategori otomatis berubah
kategori_options = list(STRUKTUR_PENGELUARAN[jenis_selected].keys())
kategori_selected = st.sidebar.selectbox("🏷️ Kategori Sub-Pos", kategori_options)

nominal = st.sidebar.number_input("💵 Nominal (Rp)", min_value=0, step=10000)
ket = st.sidebar.text_input("📝 Catatan Singkat", placeholder="Cth: Bensin, Nasi Padang, Minsoc")

if st.sidebar.button("🚀 Simpan Transaksi", use_container_width=True, type="primary"):
    if nominal > 0:
        simpan_transaksi(tgl, jenis_selected, kategori_selected, nominal, ket)
        st.sidebar.success("✅ Transaksi tersimpan!")
        st.rerun()
    else:
        st.sidebar.warning("Nominal harus lebih dari 0!")

st.sidebar.markdown("---")
st.sidebar.info("📍 **BMKG Samarinda**\n🎯 Target Akad Nikah: **2028**")

# --- 6. DASHBOARD UTAMA ---
st.markdown('<p class="main-title">👋 Halo Abil, Financial Command Center!</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Pantau arus kas harian dan progress tabungan pernikahan 2028 secara fleksibel.</p>', unsafe_allow_html=True)

df = ambil_semua_transaksi()

# Filter Bulan Berjalan
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

# Ringkasan Kas
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
        <div class="metric-label">💸 Total Pengeluaran</div>
        <div class="metric-val" style="color:#E11D48;">Rp {total_pengeluaran_bln:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💰 Sisa Dana (Saldo)</div>
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
    elif sisa_uang == 0:
        st.markdown("""
        <div class="metric-card" style="background:#EFF6FF; border-color:#BFDBFE;">
            <div class="metric-label" style="color:#1E40AF;">🔵 Status Kas</div>
            <div class="metric-val" style="color:#1D4ED8;">BALANCE</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
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
        <span style="font-size: 1.15rem; font-weight: 700; color: #1E3A8A;">🎯 Progress Tabungan Nikah 2028</span>
        <span style="font-size: 1rem; font-weight: 800; color: #2563EB; background: #FFFFFF; padding: 4px 12px; border-radius: 20px;">{persen:.1f}% Terkumpul</span>
    </div>
    <div style="font-size: 1.7rem; font-weight: 800; color: #0F172A;">
        Rp {total_nikah:,.0f} <span style="font-size: 0.95rem; color: #64748B; font-weight: 500;">/ Target Rp 100,000,000</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.progress(progress)

st.markdown("---")

# Visualisasi & AI Analyst
col1, col2 = st.columns([1.2, 0.8])

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

with col1:
    st.subheader("📊 Realisasi vs Budget Bulan Ini")
    if not merged.empty:
        # Plotly Bar Chart Modern
        fig = px.bar(
            merged, 
            x='kategori', 
            y=['Budget', 'Realisasi'], 
            color_discrete_sequence=['#E2E8F0', '#2563EB'],
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
        st.info("💡 Belum ada data transaksi bulan ini. Catat transaksi di sidebar yuk!")

with col2:
    st.subheader("🤖 UANGABIL AI Advisor")
    st.caption("Analisis otomatis alokasi 3 pos keuangan Anda.")
    
    if st.button("🔍 Minta Analisis AI", use_container_width=True, type="primary"):
        if not GEMINI_KEY:
            st.error("🔑 Jangan lupa atur GEMINI_API_KEY di Streamlit Secrets!")
        elif merged.empty:
            st.warning("⚠️ Belum ada transaksi bulan ini untuk dianalisis.")
        else:
            try:
                client = genai.Client(api_key=GEMINI_KEY)
                data_text = merged[['jenis_pengeluaran', 'kategori', 'Budget', 'Realisasi']].to_string(index=False)
                
                prompt = f"""
                Analisis keuangan bulanan UANGABIL TRACKER (Pegawai BMKG Samarinda):
                - Pemasukan Total: Rp {PEMASUKAN_BULANAN:,.0f}
                - Total Pengeluaran: Rp {total_pengeluaran_bln:,.0f}
                - Sisa Saldo: Rp {sisa_uang:,.0f}

                Data Alokasi 3 Pos Pengeluaran:
                {data_text}

                Profil Keuangan:
                - Rutin kirim ke Orang Tua Cilacap (Rp 1.000.000).
                - Target Dana Nikah 2028: Rp 100.000.000.

                Lakukan evaluasi terstruktur berdasarkan 3 Jenis Pos Pengeluaran:
                1. Pengeluaran Tetap & Masa Depan
                2. Pengeluaran Berkala
                3. Pengeluaran Dinamis / Variabel

                Berikan rekomendasi praktis, ramah, dan ringkas area mana yang perlu dikendalikan.
                """
                
                with st.spinner("🧠 AI sedang menganalisis data..."):
                    response = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=prompt,
                    )
                    if response and response.text:
                        st.markdown("---")
                        st.markdown(response.text)
                    else:
                        st.error("Gagal mendapat respon dari AI.")
                        
            except APIError as e:
                if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                    st.warning("⏳ Kuota API gratisan sedang penuh. Silakan tunggu 20-30 detik lalu klik lagi.")
                else:
                    st.error(f"API Error ({e.code}): {e.message}")
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    st.warning("⏳ Kuota API gratisan sedang penuh. Silakan tunggu 20-30 detik lalu klik lagi.")
                else:
                    st.error(f"Error AI: {e}")

# Riwayat Transaksi Historis (Tabel Modern & Cantik)
st.markdown("---")
st.subheader("📝 Jurnal Transaksi Harian (Firestore Cloud)")

if not df.empty:
    df_display = df.copy()
    
    # Format nominal rupiah bersih
    if 'nominal' in df_display.columns:
        df_display['nominal_fmt'] = df_display['nominal'].apply(lambda x: f"Rp {x:,.0f}")
    
    # Pilih dan atur urutan kolom yang elegan
    cols_order = []
    if 'tanggal' in df_display.columns: cols_order.append('tanggal')
    if 'jenis_pengeluaran' in df_display.columns: cols_order.append('jenis_pengeluaran')
    if 'kategori' in df_display.columns: cols_order.append('kategori')
    if 'nominal_fmt' in df_display.columns: cols_order.append('nominal_fmt')
    if 'keterangan' in df_display.columns: cols_order.append('keterangan')
    
    df_show = df_display[cols_order].sort_values(by='tanggal', ascending=False)
    
    # Render Streamlit Dataframe Interaktif dengan Column Configuration
    st.dataframe(
        df_show, 
        use_container_width=True,
        column_config={
            "tanggal": st.column_config.TextColumn("📅 Tanggal"),
            "jenis_pengeluaran": st.column_config.TextColumn("📂 Pos Pengeluaran"),
            "kategori": st.column_config.TextColumn("🏷️ Kategori"),
            "nominal_fmt": st.column_config.TextColumn("💵 Nominal"),
            "keterangan": st.column_config.TextColumn("📝 Keterangan")
        },
        hide_index=True
    )
else:
    st.caption("Belum ada riwayat transaksi yang tersimpan.")
