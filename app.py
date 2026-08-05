import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from google.genai.errors import APIError
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN DAN TEMA ---
st.set_page_config(
    page_title="UANGABIL TRACKER", 
    layout="wide", 
    page_icon="💳"
)

# Gaya Tampilan Visual Modern
st.markdown("""
    <style>
    .main-title { font-size: 2.1rem; font-weight: 800; color: #0F172A; margin-bottom: 2px; }
    .sub-title { font-size: 1rem; color: #64748B; margin-bottom: 20px; }
    
    .metric-card {
        background: #FFFFFF;
        padding: 16px 20px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #E2E8F0;
    }
    .metric-label { font-size: 0.85rem; font-weight: 600; color: #64748B; margin-bottom: 4px; }
    .metric-val { font-size: 1.45rem; font-weight: 800; color: #0F172A; }
    
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

# --- 3. KONFIGURASI ANGGARAN & KANTONG KEUANGAN ---
PEMASUKAN_DEFAULT = 8183550  # Acuan default jika belum terdapat transaksi pemasukan terinput
TARGET_NIKAH = 100000000
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Pembagian Kantong Utama (Termasuk Pos Pemasukan Dinamis)
STRUKTUR_TRANSAKSI = {
    "0. Pemasukan Kas / Gaji": {
        "Gaji Pokok BMKG": 2938400,
        "Tunjangan Kinerja (Tukin)": 4595150,
        "Uang Makan / Tunjangan Lain": 650000,
        "Pemasukan Sampingan / Bonus": 0
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

# --- 4. FUNGSIONALITAS FORMAT UANG SESUAI STANDAR PERBANKAN ---
def format_rupiah(nominal):
    """Format angka menjadi Rupiah standar Perbankan Indonesia (contoh: Rp1.000.000)."""
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

# --- 6. BILAH SISI (SIDEBAR): INPUT TRANSAKSI ---
st.sidebar.markdown("## 💳 **UANGABIL TRACKER**")
st.sidebar.caption("Sistem Manajemen Keuangan Berbasis Kantong")
st.sidebar.markdown("---")

st.sidebar.subheader("➕ Pencatatan Transaksi Baru")

tgl = st.sidebar.date_input("Tanggal Transaksi", datetime.now())
jenis_selected = st.sidebar.selectbox("Pos Transaksi Utama", list(STRUKTUR_TRANSAKSI.keys()))
kategori_options = list(STRUKTUR_TRANSAKSI[jenis_selected].keys())
kategori_selected = st.sidebar.selectbox("Nama Kantong / Kategori", kategori_options)

# Input Nominal dengan format angka rapi
nominal = st.sidebar.number_input(
    "Nominal Transaksi (Rp)", 
    min_value=0, 
    step=10000, 
    value=0,
    help="Masukkan nominal transaksi"
)

# Indikator Otomatis Format Resmi Rupiah saat mengetik
if nominal > 0:
    st.sidebar.info(f"Format Resmi: **{format_rupiah(nominal)}**")

ket = st.sidebar.text_input("Keterangan", placeholder="Contoh: Belanja bahan pokok, kopi, olahraga")

if st.sidebar.button("Simpan Transaksi", use_container_width=True, type="primary"):
    if nominal > 0:
        simpan_transaksi(tgl, jenis_selected, kategori_selected, nominal, ket)
        st.sidebar.success(f"Berhasil menyimpan {format_rupiah(nominal)} ke {kategori_selected}!")
        st.rerun()
    else:
        st.sidebar.warning("Nominal transaksi harus lebih dari Rp0!")

st.sidebar.markdown("---")
st.sidebar.info("CATAT SEMUA PENGELUARANMU SECARA REAL TIME!!!")

# --- 7. DASHBOARD UTAMA ---
st.markdown('<p class="main-title">Aplikasi Keuangan UANGABIL TRACKER</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Pemantauan Arus Kas Harian dan Alokasi Tabungan Pernikahan Tahun 2028</p>', unsafe_allow_html=True)

df = ambil_semua_transaksi()

# Filter Data Bulan Berjalan & Perhitungan Pemasukan/Pengeluaran
df_bln = pd.DataFrame()
total_pemasukan_bln = 0
total_pengeluaran_bln = 0

if not df.empty and 'tanggal' in df.columns:
    df['tanggal_dt'] = pd.to_datetime(df['tanggal'])
    bln_ini = datetime.now().month
    thn_ini = datetime.now().year
    df_bln = df[(df['tanggal_dt'].dt.month == bln_ini) & (df['tanggal_dt'].dt.year == thn_ini)]
    
    if not df_bln.empty:
        # Perhitungan Pemasukan Kas Terinput Bulan Ini
        df_pemasukan = df_bln[df_bln['jenis_pengeluaran'] == '0. Pemasukan Kas / Gaji']
        if not df_pemasukan.empty:
            total_pemasukan_bln = df_pemasukan['nominal'].sum()
        else:
            total_pemasukan_bln = PEMASUKAN_DEFAULT
            
        # Perhitungan Pengeluaran Bulan Ini
        df_pengeluaran = df_bln[df_bln['jenis_pengeluaran'] != '0. Pemasukan Kas / Gaji']
        if not df_pengeluaran.empty:
            total_pengeluaran_bln = df_pengeluaran['nominal'].sum()
else:
    total_pemasukan_bln = PEMASUKAN_DEFAULT

sisa_uang = total_pemasukan_bln - total_pengeluaran_bln

# Ringkasan Ikhtisar Kas Modern
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Pemasukan Bulan Ini</div>
        <div class="metric-val" style="color:#16A34A;">{format_rupiah(total_pemasukan_bln)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Pengeluaran Bulan Ini</div>
        <div class="metric-val" style="color:#E11D48;">{format_rupiah(total_pengeluaran_bln)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Sisa Saldo Kas</div>
        <div class="metric-val" style="color:#2563EB;">{format_rupiah(sisa_uang)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_m4:
    if sisa_uang > 0:
        st.markdown("""
        <div class="metric-card" style="background:#F0FDF4; border-color:#BBF7D0;">
            <div class="metric-label" style="color:#166534;">Status Kas</div>
            <div class="metric-val" style="color:#15803D;">SURPLUS</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="metric-card" style="background:#FEF2F2; border-color:#FECACA;">
            <div class="metric-label" style="color:#991B1B;">Status Kas</div>
            <div class="metric-val" style="color:#DC2626;">DEFISIT</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Progress Target Tabungan Pernikahan
total_nikah = 0
if not df.empty and 'kategori' in df.columns:
    total_nikah = df[df['kategori'].isin(['Kantong Tabungan Nikah', 'Tabungan Nikah'])]['nominal'].sum()

progress = min(float(total_nikah / TARGET_NIKAH), 1.0)
persen = progress * 100

st.markdown(f"""
<div class="target-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 1.1rem; font-weight: 700; color: #1E3A8A;">🎯 Progress Target Tabungan Pernikahan Tahun 2028</span>
        <span style="font-size: 0.95rem; font-weight: 800; color: #2563EB; background: #FFFFFF; padding: 4px 12px; border-radius: 20px;">{persen:.1f}% Terkumpul</span>
    </div>
    <div style="font-size: 1.6rem; font-weight: 800; color: #0F172A;">
        {format_rupiah(total_nikah)} <span style="font-size: 0.9rem; color: #64748B; font-weight: 500;">/ Target {format_rupiah(TARGET_NIKAH)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.progress(progress)

st.markdown("---")

# TABEL TAB: VISUALISASI DAN KELOLA
tab1, tab2 = st.tabs(["📊 Visualisasi & Analisis AI", "✏️ Kelola & Revisi Transaksi"])

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
    
    # Perhitungan Sisa Alokasi & Penentuan Status Otomatis
    merged['Sisa_Anggaran'] = merged['Anggaran'] - merged['Realisasi']
    
    def hitung_status_otomatis(row):
        sisa = row['Sisa_Anggaran']
        if sisa > 0:
            return "🟢 Aman"
        elif sisa == 0:
            return "🟡 Pas"
        else:
            return "🔴 Overbudget"
            
    merged['Status_Otomatis'] = merged.apply(hitung_status_otomatis, axis=1)

with tab1:
    col1, col2 = st.columns([1.25, 0.75])

    with col1:
        st.subheader("📊 Perbandingan Anggaran dan Realisasi Per Kantong")
        if not merged.empty:
            fig = px.bar(
                merged, 
                x='kategori', 
                y=['Anggaran', 'Realisasi'], 
                color_discrete_sequence=['#CBD5E1', '#2563EB'],
                barmode='group',
                hover_data={
                    'jenis_pengeluaran': True,
                    'Sisa_Anggaran': True,
                    'Status_Otomatis': True
                },
                labels={'kategori': 'Nama Kantong', 'value': 'Nominal (Rp)', 'variable': 'Kategori'}
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
            
            # Tabel Rincian Sisa Alokasi dan Status Per Kantong
            st.markdown("##### 📌 Rincian Sisa Alokasi Anggaran & Status Otomatis")
            df_tabel_sisa = merged.copy()
            df_tabel_sisa['Anggaran_Fmt'] = df_tabel_sisa['Anggaran'].apply(format_rupiah)
            df_tabel_sisa['Realisasi_Fmt'] = df_tabel_sisa['Realisasi'].apply(format_rupiah)
            df_tabel_sisa['Sisa_Fmt'] = df_tabel_sisa['Sisa_Anggaran'].apply(format_rupiah)
            
            st.dataframe(
                df_tabel_sisa[['kategori', 'Anggaran_Fmt', 'Realisasi_Fmt', 'Sisa_Fmt', 'Status_Otomatis']],
                use_container_width=True,
                column_config={
                    "kategori": st.column_config.TextColumn("Nama Kantong"),
                    "Anggaran_Fmt": st.column_config.TextColumn("Anggaran"),
                    "Realisasi_Fmt": st.column_config.TextColumn("Terpakai"),
                    "Sisa_Fmt": st.column_config.TextColumn("Sisa Alokasi"),
                    "Status_Otomatis": st.column_config.TextColumn("Status")
                },
                hide_index=True
            )
        else:
            st.info("💡 Belum terdapat data anggaran pada bulan berjalan.")

    with col2:
        st.subheader("🤖 Penasihat Keuangan AI")
        st.caption("Analisis otomatis posisi keuangan berdasarkan data kantong Anda.")
        
        if st.button("🔍 Dapatkan Analisis Keuangan", use_container_width=True, type="primary"):
            if not GEMINI_KEY:
                st.error("🔑 Harap atur GEMINI_API_KEY pada Streamlit Secrets.")
            else:
                try:
                    client = genai.Client(api_key=GEMINI_KEY)
                    data_text = merged[['jenis_pengeluaran', 'kategori', 'Anggaran', 'Realisasi', 'Sisa_Anggaran', 'Status_Otomatis']].to_string(index=False) if not merged.empty else "Belum ada pengeluaran."
                    
                    prompt = f"""
                    Analisis Keuangan Bulanan UANGABIL TRACKER:
                    - Total Pemasukan Terinput Bulan Ini: {format_rupiah(total_pemasukan_bln)}
                    - Total Pengeluaran Bulan Ini: {format_rupiah(total_pengeluaran_bln)}
                    - Sisa Saldo Kas: {format_rupiah(sisa_uang)}

                    Data Per Kantong Keuangan, Sisa Alokasi & Status Otomatisnya:
                    {data_text}

                    Berikan evaluasi baku, profesional, dan obyektif mengenai kondisi pemasukan vs pengeluaran serta rekomendasi pengendalian anggaran.
                    """
                    
                    with st.spinner("Sistem AI sedang menganalisis data keuangan Anda..."):
                        response = client.models.generate_content(
                            model='gemini-2.0-flash',
                            contents=prompt,
                        )
                        if response and response.text:
                            st.markdown("---")
                            st.markdown(response.text)
                except APIError as e:
                    if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning("⏳ Batas penggunaan API gratis telah tercapai. Harap tunggu 30 detik sebelum mencoba kembali.")
                    else:
                        st.error(f"Kesalahan API: {e.message}")
                except Exception as e:
                    st.error(f"Kesalahan Sistem: {e}")

# TAB 2: REVISI TRANSAKSI
with tab2:
    st.subheader("✏️ Pembaruan dan Revisi Transaksi")
    st.caption("Fasilitas koreksi data transaksi keuangan (Pemasukan maupun Pengeluaran).")
    
    if not df.empty:
        df['label_pilihan'] = df['tanggal'] + " | " + df['kategori'] + " | " + df['nominal'].apply(format_rupiah) + " (" + df['keterangan'].fillna('') + ")"
        pilihan_transaksi = st.selectbox("📌 Pilih Transaksi yang Ingin Diperbarui:", df['label_pilihan'].tolist())
        
        selected_row = df[df['label_pilihan'] == pilihan_transaksi].iloc[0]
        
        st.markdown("---")
        col_edit1, col_edit2 = st.columns(2)
        
        with col_edit1:
            e_tgl = st.date_input("Tanggal Transaksi", datetime.strptime(selected_row['tanggal'], "%Y-%m-%d"))
            e_jenis = st.selectbox("Pos Transaksi Utama", list(STRUKTUR_TRANSAKSI.keys()), index=list(STRUKTUR_TRANSAKSI.keys()).index(selected_row['jenis_pengeluaran']) if selected_row['jenis_pengeluaran'] in STRUKTUR_TRANSAKSI else 0)
            e_kat_options = list(STRUKTUR_TRANSAKSI[e_jenis].keys())
            e_kat = st.selectbox("Nama Kantong / Kategori", e_kat_options, index=e_kat_options.index(selected_row['kategori']) if selected_row['kategori'] in e_kat_options else 0)
        
        with col_edit2:
            e_nom = st.number_input("Nominal Transaksi (Rp)", value=int(selected_row['nominal']), step=10000)
            st.info(f"Format Resmi: **{format_rupiah(e_nom)}**")
            
            e_ket = st.text_input("Keterangan", value=str(selected_row['keterangan']) if pd.notna(selected_row['keterangan']) else "")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("💾 Simpan Perubahan", use_container_width=True, type="primary"):
                    update_transaksi(selected_row['doc_id'], e_tgl, e_jenis, e_kat, e_nom, e_ket)
                    st.success("Perubahan data transaksi berhasil disimpan!")
                    st.rerun()
            
            with col_btn2:
                if st.button("🗑️ Hapus Transaksi", use_container_width=True):
                    hapus_transaksi(selected_row['doc_id'])
                    st.warning("Data transaksi berhasil dihapus.")
                    st.rerun()

# --- 8. JURNAL TRANSAKSI HARIAN (PENGELOMPOKAN FILTER DROPDOWN) ---
st.markdown("---")
st.subheader("📑 Jurnal Transaksi Harian (Firestore Cloud)")

if not df.empty:
    df_display = df.copy()
    if 'nominal' in df_display.columns:
        df_display['nominal_fmt'] = df_display['nominal'].apply(format_rupiah)
    
    # Pilihan Filter Kelompok Transaksi Pilihan Sendiri
    daftar_pos = ["Semua Pos Transaksi"] + list(STRUKTUR_TRANSAKSI.keys())
    pos_filter = st.selectbox("🔍 Filter Berdasarkan Kelompok Pos Transaksi:", daftar_pos)
    
    if pos_filter != "Semua Pos Transaksi":
        df_filtered = df_display[df_display['jenis_pengeluaran'] == pos_filter]
    else:
        df_filtered = df_display

    # Informasi Ringkasan Kelompok
    total_nominal_kelompok = df_filtered['nominal'].sum() if not df_filtered.empty else 0
    st.caption(f"Menampilkan **{len(df_filtered)}** transaksi | Total Akumulasi: **{format_rupiah(total_nominal_kelompok)}**")
    
    cols_order = [c for c in ['tanggal', 'jenis_pengeluaran', 'kategori', 'nominal_fmt', 'keterangan'] if c in df_filtered.columns]
    df_show = df_filtered[cols_order].sort_values(by='tanggal', ascending=False)
    
    st.dataframe(
        df_show, 
        use_container_width=True,
        column_config={
            "tanggal": st.column_config.TextColumn("Tanggal"),
            "jenis_pengeluaran": st.column_config.TextColumn("Pos Transaksi Utama"),
            "kategori": st.column_config.TextColumn("Nama Kantong / Kategori"),
            "nominal_fmt": st.column_config.TextColumn("Nominal Transaksi"),
            "keterangan": st.column_config.TextColumn("Keterangan")
        },
        hide_index=True
    )
else:
    st.caption("Belum terdapat riwayat transaksi yang tersimpan.")
