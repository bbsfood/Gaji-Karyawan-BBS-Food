import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# Page Config
st.set_page_config(page_title="Gaji Karyawan BBS Food", layout="wide")

# CSS khusus tampilan Struk Termal 58mm saat diprint
st.markdown("""
<style>
@media print {
    body * { visibility: hidden; }
    .thermal-receipt, .thermal-receipt * { visibility: visible; }
    .thermal-receipt { 
        position: absolute; 
        left: 0; 
        top: 0; 
        width: 58mm; 
        font-family: 'Courier New', monospace;
        font-size: 11px;
        padding: 5px;
    }
    .no-print { display: none !important; }
}
.thermal-receipt {
    width: 220px;
    background: #fff;
    padding: 10px;
    border: 1px dashed #ccc;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    color: #000;
}
</style>
""", unsafe_allow_html=True)

# 1. Inisialisasi Supabase
try:
    url: str = st.secrets["supabase"]["SUPABASE_URL"]
    key: str = st.secrets["supabase"]["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Gagal terhubung ke Supabase. Cek Secrets Anda.")
    st.stop()

st.title("🏭 Sistem Gaji Karyawan BBS Food")

# Sidebar - Menu Navigasi
menu = st.sidebar.radio("Pilih Menu", ["Input Gaji Harian", "Data & Edit Log", "Rekap Bulanan", "Cetak Struk Termal"])

# ----------------------------------------------------
# MENU 1: INPUT GAJI HARIAN
# ----------------------------------------------------
if menu == "Input Gaji Harian":
    st.subheader("📝 Form Input Gaji Karyawan")
    
    with st.form("form_input", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nama_karyawan = st.text_input("Nama Karyawan")
            tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.today())
            sistem_gaji = st.selectbox("Sistem Gaji", ["Borongan", "Harian"])
            
        with col2:
            if sistem_gaji == "Borongan":
                # Menggunakan step=0.5 dan format desimal (%.1f)
                jumlah_borongan = st.number_input("Jumlah Borongan (Pcs/Ball)", min_value=0.1, value=1.0, step=0.5, format="%.1f")
                nominal_satuan = st.number_input("Gaji per Borongan (Rp)", min_value=0, value=1000, step=500)
                total_gaji = jumlah_borongan * nominal_satuan
            else:
                jumlah_borongan = st.number_input("Jumlah Hari Masuk", min_value=0.5, value=1.0, step=0.5, format="%.1f")
                nominal_satuan = st.number_input("Gaji Per Hari (Rp)", min_value=0, value=50000, step=5000)
                total_gaji = jumlah_borongan * nominal_satuan
                
            st.info(f"**Total Gaji Diterima: Rp {total_gaji:,.0f}**")

        submitted = st.form_submit_button("Simpan Data")
        if submitted:
            if not nama_karyawan:
                st.error("Nama Karyawan tidak boleh kosong!")
            else:
                data = {
                    "nama_karyawan": nama_karyawan.strip().title(),
                    "tanggal": str(tanggal_masuk),
                    "sistem_gaji": sistem_gaji,
                    "jumlah_borongan": float(jumlah_borongan),  # Menggunakan float agar bisa simpan desimal
                    "nominal_satuan": int(nominal_satuan),
                    "total_gaji": int(total_gaji)
                }
                supabase.table("LogHarian").insert(data).execute()
                st.success(f"Data gaji {nama_karyawan} berhasil disimpan!")

# ----------------------------------------------------
# MENU 2: DATA & EDIT LOG
# ----------------------------------------------------
elif menu == "Data & Edit Log":
    st.subheader("📋 Riwayat Data Gaji & Edit")
    res = supabase.table("LogHarian").select("*").order("tanggal", desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[["id", "tanggal", "nama_karyawan", "sistem_gaji", "jumlah_borongan", "nominal_satuan", "total_gaji"]], use_container_width=True)
        
        st.divider()
        col_edit, col_del = st.columns(2)
        
        # Fitur Hapus
        with col_del:
            st.subheader("🗑️ Hapus Data")
            id_hapus = st.number_input("Masukkan ID Data yang akan dihapus", min_value=1, step=1)
            if st.button("Hapus Data", type="primary"):
                supabase.table("LogHarian").delete().eq("id", id_hapus).execute()
                st.success(f"Data dengan ID {id_hapus} berhasil dihapus!")
                st.rerun()

        # Fitur Edit
        with col_edit:
            st.subheader("✏️ Edit Data")
            id_edit = st.number_input("Masukkan ID Data yang akan diubah", min_value=1, step=1)
            data_edit = [d for d in res.data if d["id"] == id_edit]
            
            if data_edit:
                curr = data_edit[0]
                with st.form("form_edit"):
                    edit_nama = st.text_input("Nama", value=curr["nama_karyawan"])
                    edit_sistem = st.selectbox("Sistem Gaji", ["Borongan", "Harian"], index=0 if curr.get("sistem_gaji") == "Borongan" else 1)
                    edit_jumlah = st.number_input("Jumlah Borongan / Hari", value=float(curr["jumlah_borongan"]), step=0.5, format="%.1f")
                    edit_nominal = st.number_input("Nominal Satuan (Rp)", value=curr.get("nominal_satuan", 0))
                    
                    if st.form_submit_button("Update Data"):
                        total_new = edit_jumlah * edit_nominal
                        supabase.table("LogHarian").update({
                            "nama_karyawan": edit_nama,
                            "sistem_gaji": edit_sistem,
                            "jumlah_borongan": edit_jumlah,
                            "nominal_satuan": edit_nominal,
                            "total_gaji": total_new
                        }).eq("id", id_edit).execute()
                        st.success("Data berhasil diperbarui!")
                        st.rerun()
    else:
        st.info("Belum ada data log harian.")

# ----------------------------------------------------
# MENU 3: REKAP BULANAN PER ORANG
# ----------------------------------------------------
elif menu == "Rekap Bulanan":
    st.subheader("📊 Rekapitulasi Gaji Bulanan Per Orang")
    
    col_m, col_y = st.columns(2)
    with col_m:
        bulan = st.selectbox("Pilih Bulan", range(1, 13), index=datetime.today().month - 1)
    with col_y:
        tahun = st.number_input("Pilih Tahun", value=datetime.today().year)
        
    res = supabase.table("LogHarian").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        
        # Filter berdasarkan bulan dan tahun
        df_filtered = df[(df["tanggal"].dt.month == bulan) & (df["tanggal"].dt.year == tahun)]
        
        if not df_filtered.empty:
            rekap = df_filtered.groupby(["nama_karyawan", "sistem_gaji"]).agg(
                total_hari_masuk=('tanggal', 'count'),
                total_borongan=('jumlah_borongan', 'sum'),
                total_pembayaran=('total_gaji', 'sum')
            ).reset_index()
            
            st.dataframe(rekap, use_container_width=True)
            st.metric("Total Pengeluaran Gaji Bulan Ini", f"Rp {rekap['total_pembayaran'].sum():,.0f}")
        else:
            st.warning("Tidak ada data transaksi pada bulan & tahun ini.")

# ----------------------------------------------------
# MENU 4: CETAK STRUK TERMAL 58MM
# ----------------------------------------------------
elif menu == "Cetak Struk Termal":
    st.subheader("🖨️ Cetak Struk Gaji (58mm)")
    
    res = supabase.table("LogHarian").select("*").order("id", desc=True).limit(20).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        selected_id = st.selectbox("Pilih ID Transaksi untuk Dicetak", df["id"])
        
        item = df[df["id"] == selected_id].iloc[0]
        
        # Tampilan preview Struk 58mm
        struk_html = f"""
        <div class="thermal-receipt">
            <center>
                <strong>BBS FOOD SRAGEN</strong><br>
                Jl. Jatibatur, Gemolong<br>
                --------------------------------
            </center>
            Tgl   : {item['tanggal']}<br>
            Nama  : {item['nama_karyawan']}<br>
            Sistem: {item.get('sistem_gaji', 'Borongan')}<br>
            --------------------------------<br>
            Qty   : {item['jumlah_borongan']} @ Rp {item.get('nominal_satuan', 0):,.0f}<br>
            --------------------------------<br>
            <strong>TOTAL : Rp {item['total_gaji']:,.0f}</strong><br>
            --------------------------------<br>
            <center>
                <i>~ Terima Kasih ~</i>
            </center>
        </div>
        """
        st.markdown(struk_html, unsafe_allow_html=True)
        st.caption("Gunakan tombol Print di browser (Ctrl+P) atau sambungkan browser Android ke aplikasi Printer Bluetooth thermal 58mm.")
