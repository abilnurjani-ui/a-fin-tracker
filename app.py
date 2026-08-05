import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- 1. SETTING HALAMAN & BRANDING ---
st.set_page_config(
    page_title="A-FIN TRACKER", 
    layout="wide", 
    page_icon="📈"
)

# Custom Styling UI Modern
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 0px; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INISIALISASI FIREBASE ---
if not firebase_admin._apps:
    key_dict = dict(st.secrets["firebase"])
    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 3. CONFIG PEMASUKAN & BUDGET BULANAN ---
PEMASUKAN_BULANAN = 8183550  # Gaji (2.938.400) + Tukin (4.595.150) + Uang Makan (650.000)
TARGET_NIKAH = 100000000
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

BUDGET_BULANAN = {
    "Tabungan Nikah": 2700000,
    "Orang Tua (Cilacap)": 1000000,
    "Kebutuhan Pokok": 2000000,
    "Pacaran": 1100000,
    "Keinginan Sendiri": 1000000,
    "Dana Tak Terduga": 383550
}

# --- 4. FUNGSIONALITAS DATABASE FIREBASE ---
def simpan_transaksi(tgl, kategori, nominal, ket):
    doc_ref = db.collection("transaksi").document()
    doc_ref.set({
        "tanggal": tgl.strftime("%Y-%m-%d"),
        "kategori": kategori,
        "nominal": float(nominal),
        "keterangan": ket,
        "created_at": firestore.SERVER_TIMESTAMP
    })

def ambil_semua_transaksi():
    docs = db.collection("transaksi").stream()
    data = [doc.to_dict() for doc in docs]
    if data:
        return pd.DataFrame(data)
    return pd.DataFrame()

# --- 5. SIDEBAR: FORM INPUT ---
st.sidebar.markdown("## 📊 **A-FIN TRACKER**")
st.sidebar.caption("Financial Command Center")
st.sidebar.markdown("---")

st.sidebar.subheader("➕ Tambah Transaksi Harian")
with st.sidebar.form(key='form_transaksi', clear_on_submit=True):
    tgl = st.date_input("Tanggal Transaksi", datetime.now())
    kategori = st.selectbox("Kategori", list(BUDGET_BULANAN.keys()))
    nominal = st.number_input("Nominal (Rp)", min_value=0, step=10000)
    ket = st.text_input("Keterangan", placeholder="Contoh: Makan di Korem, Bensin")
    submit = st.form_submit_button("Simpan ke Cloud Firebase")

    if submit and nominal > 0:
        simpan_transaksi(tgl, kategori, nominal, ket)
        st.sidebar.success("Berhasil tersimpan di Firebase!")
        st.rerun()

# --- 6. DASHBOARD UTAMA ---
st.markdown('<p class="main-title">📈 A-FIN TRACKER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Personal Finance & Marriage Target Preparedness 2028</p>', unsafe_allow_html=True)

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
st.markdown("### 💵 Ringkasan Kas Bulan Ini")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Total Pemasukan", f"Rp {PEMASUKAN_BULANAN:,.0f}")
with col_m2:
    st.metric("Total Pengeluaran", f"Rp {total_pengeluaran_bln:,.0f}")
with col_m3:
    st.metric("Sisa Dana (Balance)", f"Rp {sisa_uang:,.0f}")
with col_m4:
    if sisa_uang > 0:
        st.success("🟢 SURPLUS")
    elif sisa_uang == 0:
        st.info("🔵 BALANCE")
    else:
        st.error(f"🔴 DEFISIT (Over: Rp {abs(sisa_uang):,.0f})")

st.markdown("---")

# Progress Target Nikah
st.markdown("### 🎯 Progress Target Nikah (Rp 100 Juta)")
total_nikah = 0
if not df.empty and 'kategori' in df.columns:
    total_nikah = df[df['kategori'] == 'Tabungan Nikah']['nominal'].sum()

progress = min(float(total_nikah / TARGET_NIKAH), 1.0)
col_p1, col_p2 = st.columns([3, 1])
with col_p1:
    st.progress(progress)
with col_p2:
    st.metric("Terkumpul", f"Rp {total_nikah:,.0f}", f"{(progress*100):.1f}%")

st.markdown("---")

# Visualisasi & AI Analyst
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Realisasi vs Budget Bulan Ini")
    merged = pd.DataFrame()
    if not df_bln.empty:
        summary = df_bln.groupby('kategori')['nominal'].sum().reset_index()
        budget_df = pd.DataFrame(list(BUDGET_BULANAN.items()), columns=['kategori', 'Budget'])
        merged = pd.merge(budget_df, summary, on='kategori', how='left').fillna(0)
        merged.rename(columns={'nominal': 'Realisasi'}, inplace=True)
        
        fig = px.bar(merged, x='kategori', y=['Budget', 'Realisasi'], barmode='group',
                     labels={'value': 'Rupiah', 'kategori': 'Kategori'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada data transaksi bulan ini.")

with col2:
    st.subheader("🤖 A-FIN AI Advisor")
    st.write("Analisis otomatis kondisi saldo dan alokasi Anda.")
    
    if st.button("🔍 Analisis Keuangan Saya via AI"):
        if not GEMINI_KEY:
            st.error("Atur GEMINI_API_KEY di Streamlit Secrets!")
        elif merged.empty:
            st.warning("Belum ada data transaksi bulan ini.")
        else:
            try:
                genai.configure(api_key=GEMINI_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                data_text = merged.to_string(index=False)
                
                prompt = f"""
                Analisis keuangan untuk A-FIN TRACKER (Pegawai BMKG Samarinda):
                - Pemasukan: Rp {PEMASUKAN_BULANAN:,.0f}
                - Pengeluaran Bulan Ini: Rp {total_pengeluaran_bln:,.0f}
                - Sisa Uang: Rp {sisa_uang:,.0f}
                - Rincian:
                {data_text}

                Profil:
                - Rutin kirim ke Orang Tua Cilacap (Rp 1.000.000).
                - Target Dana Nikah 2028: Rp 100.000.000.

                Berikan evaluasi tajam: pos mana yang berpotensi bocor dan saran agar target 2028 tetap aman.
                """
                with st.spinner("A-FIN AI sedang menganalisis data..."):
                    res = model.generate_content(prompt)
                    st.markdown("---")
                    st.markdown(res.text)
            except Exception as e:
                st.error(f"Error AI: {e}")

# Riwayat Transaksi Historis
st.markdown("---")
st.subheader("📝 Live Transaction Log (Firestore Cloud)")
if not df.empty:
    display_df = df.drop(columns=['tanggal_dt', 'created_at'], errors='ignore')
    st.dataframe(display_df.sort_values(by='tanggal', ascending=False), use_container_width=True)
