import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import io

# Page Config
st.set_page_config(page_title="Gaji & Produksi BBS Food", layout="wide")

# CSS khusus Struk Termal 58mm
st.markdown("""
<style>
@media print {
    body * { visibility: hidden; }
    .thermal-receipt, .thermal-receipt * { visibility: visible; }
    .thermal-receipt { 
        position: absolute; left: 0; top: 0; width: 58mm; 
        font-family: 'Courier New', monospace; font-size: 11px; padding: 5px;
    }
}
.thermal-receipt {
    width: 220px; background: #fff; padding: 10px; border: 1px dashed #ccc;
    font-family: 'Courier New', monospace; font-size: 12px; color: #000;
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

st.title("🏭 Sistem Gaji & Produksi Pabrik BBS Food")

# Master Data Produk & Bal
DAFTAR_PRODUK = [
    "Makaroni Ori", "Makaroni Pedas", "Stik Ori", "Stik Pedas", 
    "Seblak Mix", "Jengkol", "Kedelai Ori", "Kedelai Pedas", 
    "K. Tongkol Asin", "K. Tongkol Pedas", "Campuran (Mix)", 
    "Marneng Asin", "Marneng Pedas", "Emping Balado Asin", 
    "Emping Pedas Manis", "Mie Enak", "K. Jablay"
]
UKURAN_BAL = ["Isi 10", "Isi 12"]

# Ambil Daftar Karyawan dari Database MasterKaryawan
def get_karyawan_list():
    res = supabase.table("MasterKaryawan").select("nama_karyawan").order("nama_karyawan").execute()
    if res.data:
        return [item["nama_karyawan"] for item in res.data]
    return []

# Sidebar Navigasi
menu = st.sidebar.radio("Pilih Menu", [
    "Input Gaji & Produksi", 
    "Master Karyawan",
    "Data & Edit Log", 
    "Rekap & Ekspor Excel", 
    "Cetak Struk Termal"
])

# ----------------------------------------------------
# MENU 1: INPUT GAJI & PRODUKSI (MULTI-ITEM)
# ----------------------------------------------------
if menu == "Input Gaji & Produksi":
    st.subheader("📝 Form Input Hasil Produksi & Gaji Harian")
    
    list_karyawan = get_karyawan_list()
    
    if not list_karyawan:
        st.warning("⚠️ Belum ada data karyawan. Silakan tambahkan nama karyawan di menu 'Master Karyawan' terlebih dahulu!")
    else:
        col_hdr1, col_hdr2, col_hdr3 = st.columns(3)
        with col_hdr1:
            nama_karyawan = st.selectbox("Pilih Nama Karyawan", list_karyawan)
        with col_hdr2:
            tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.today())
        with col_hdr3:
            sistem_gaji = st.selectbox("Sistem Gaji", ["Borongan", "Harian"])
            
        st.divider()

        # JIKA SISTEM GAJI BORONGAN (BISA BANYAK PRODUK SEKALEGUS)
        if sistem_gaji == "Borongan":
            st.markdown("##### 📦 Input Hasil Bungkusan Borongan")
            
            # Menggunakan Session State untuk menyimpan item sementara sebelum di-submit
            if "items_borongan" not in st.session_state:
                st.session_state["items_borongan"] = []

            # Sub-Form Tambah Item
            with st.form("form_add_item", clear_on_submit=True):
                col_i1, col_i2, col_i3, col_i4 = st.columns([3, 2, 2, 2])
                with col_i1:
                    item_produk = st.selectbox("Jenis Produk", DAFTAR_PRODUK)
                with col_i2:
                    item_bal = st.selectbox("Ukuran Bal", UKURAN_BAL)
                with col_i3:
                    item_qty = st.number_input("Jumlah (Ball)", min_value=0.1, value=1.0, step=0.5, format="%.1f")
                with col_i4:
                    item_nominal = st.number_input("Gaji per Ball (Rp)", min_value=0, value=4000, step=500)
                
                btn_add = st.form_submit_button("➕ Tambahkan ke Daftar")
                if btn_add:
                    total_item_gaji = item_qty * item_nominal
                    st.session_state["items_borongan"].append({
                        "jenis_produk": item_produk,
                        "ukuran_bal": item_bal,
                        "jumlah_borongan": float(item_qty),
                        "nominal_satuan": int(item_nominal),
                        "total_gaji": float(total_item_gaji)
                    })
                    st.rerun()

            # Tampilkan Daftar Item yang Ditambahkan
            if st.session_state["items_borongan"]:
                st.markdown("**Daftar Bungkusan yang Akan Disimpan:**")
                df_temp = pd.DataFrame(st.session_state["items_borongan"])
                st.dataframe(df_temp[["jenis_produk", "ukuran_bal", "jumlah_borongan", "nominal_satuan", "total_gaji"]], use_container_width=True)
                
                col_bt1, col_bt2 = st.columns([3, 1])
                with col_bt1:
                    total_semua_gaji = sum(x["total_gaji"] for x in st.session_state["items_borongan"])
                    st.success(f"**Total Gaji Diterima (Semua Item): Rp {total_semua_gaji:,.0f}**")
                with col_bt2:
                    if st.button("🗑️ Kosongkan Daftar"):
                        st.session_state["items_borongan"] = []
                        st.rerun()

                st.divider()
                
                # Tombol Simpan Semua Data ke Database
                if st.button("💾 SIMPAN SEMUA DATA LOG", type="primary", use_container_width=True):
                    data_to_insert = []
                    for item in st.session_state["items_borongan"]:
                        data_to_insert.append({
                            "nama_karyawan": nama_karyawan,
                            "tanggal": str(tanggal_masuk),
                            "sistem_gaji": "Borongan",
                            "jenis_produk": item["jenis_produk"],
                            "ukuran_bal": item["ukuran_bal"],
                            "jumlah_borongan": item["jumlah_borongan"],
                            "nominal_satuan": item["nominal_satuan"],
                            "total_gaji": item["total_gaji"]
                        })
                    
                    supabase.table("LogHarian").insert(data_to_insert).execute()
                    st.success(f"Berhasil menyimpan {len(data_to_insert)} item produksi untuk {nama_karyawan}!")
                    st.session_state["items_borongan"] = []
                    st.rerun()
            else:
                st.info("Pilih produk di atas lalu klik '➕ Tambahkan ke Daftar' untuk menyusun hasil bungkusan hari ini.")

        # JIKA SISTEM GAJI HARIAN
        else:
            with st.form("form_harian"):
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    jumlah_hari = st.number_input("Jumlah Hari Masuk", min_value=0.5, value=1.0, step=0.5, format="%.1f")
                with col_h2:
                    gaji_per_hari = st.number_input("Gaji Per Hari (Rp)", min_value=0, value=50000, step=5000)
                
                total_harian = jumlah_hari * gaji_per_hari
                st.info(f"**Total Gaji Harian: Rp {total_harian:,.0f}**")
                
                btn_simpan_harian = st.form_submit_button("Simpan Data Harian", type="primary")
                if btn_simpan_harian:
                    data_harian = {
                        "nama_karyawan": nama_karyawan,
                        "tanggal": str(tanggal_masuk),
                        "sistem_gaji": "Harian",
                        "jenis_produk": "-",
                        "ukuran_bal": "-",
                        "jumlah_borongan": float(jumlah_hari),
                        "nominal_satuan": int(gaji_per_hari),
                        "total_gaji": float(total_harian)
                    }
                    supabase.table("LogHarian").insert(data_harian).execute()
                    st.success(f"Data harian {nama_karyawan} berhasil disimpan!")

# ----------------------------------------------------
# MENU 2: MASTER KARYAWAN
# ----------------------------------------------------
elif menu == "Master Karyawan":
    st.subheader("👥 Kelola Master Data Karyawan")
    
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        st.markdown("##### Tambah Karyawan Baru")
        with st.form("form_karyawan", clear_on_submit=True):
            nama_baru = st.text_input("Nama Karyawan")
            btn_karyawan = st.form_submit_button("Tambah Karyawan")
            
            if btn_karyawan:
                if nama_baru:
                    try:
                        supabase.table("MasterKaryawan").insert({"nama_karyawan": nama_baru.strip().title()}).execute()
                        st.success(f"Karyawan '{nama_baru.strip().title()}' berhasil ditambahkan!")
                        st.rerun()
                    except Exception as e:
                        st.error("Gagal menambahkan. Mungkin nama karyawan sudah ada.")
                else:
                    st.error("Nama karyawan wajib diisi!")

    with col_k2:
        st.markdown("##### Daftar Karyawan Terdaftar")
        res_k = supabase.table("MasterKaryawan").select("*").order("nama_karyawan").execute()
        if res_k.data:
            df_k = pd.DataFrame(res_k.data)
            st.dataframe(df_k[["id", "nama_karyawan"]], use_container_width=True)
            
            id_del_k = st.number_input("Hapus ID Karyawan", min_value=1, step=1, value=1)
            if st.button("Hapus Karyawan"):
                supabase.table("MasterKaryawan").delete().eq("id", int(id_del_k)).execute()
                st.success("Karyawan dihapus!")
                st.rerun()
        else:
            st.info("Belum ada data karyawan.")

# ----------------------------------------------------
# MENU 3: DATA & EDIT LOG
# ----------------------------------------------------
elif menu == "Data & Edit Log":
    st.subheader("📋 Riwayat Data Log Produksi & Edit")
    res = supabase.table("LogHarian").select("*").order("id", desc=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        cols_order = ["id", "tanggal", "nama_karyawan", "sistem_gaji", "jenis_produk", "ukuran_bal", "jumlah_borongan", "nominal_satuan", "total_gaji"]
        for c in cols_order:
            if c not in df.columns:
                df[c] = "-"
                
        st.dataframe(df[cols_order], use_container_width=True)
        st.divider()
        
        col_edit, col_del = st.columns(2)
        
        # Fitur Hapus
        with col_del:
            st.subheader("🗑️ Hapus Data Log")
            id_hapus = st.number_input("Masukkan ID Data yang akan dihapus", min_value=1, step=1, value=1)
            if st.button("Hapus Data Log", type="primary"):
                supabase.table("LogHarian").delete().eq("id", int(id_hapus)).execute()
                st.success(f"Data ID {id_hapus} dihapus!")
                st.rerun()

        # Fitur Edit
        with col_edit:
            st.subheader("✏️ Edit Data Log")
            id_edit = st.number_input("Masukkan ID Data yang akan diubah", min_value=1, step=1, value=1)
            data_edit = [d for d in res.data if d["id"] == int(id_edit)]
            
            if data_edit:
                curr = data_edit[0]
                list_karyawan = get_karyawan_list()
                
                with st.form("form_edit"):
                    idx_nama = list_karyawan.index(curr.get("nama_karyawan")) if curr.get("nama_karyawan") in list_karyawan else 0
                    edit_nama = st.selectbox("Nama Karyawan", list_karyawan if list_karyawan else [curr.get("nama_karyawan")], index=idx_nama)
                    
                    edit_sistem = st.selectbox("Sistem Gaji", ["Borongan", "Harian"], index=0 if curr.get("sistem_gaji") == "Borongan" else 1)
                    
                    idx_prod = DAFTAR_PRODUK.index(curr.get("jenis_produk")) if curr.get("jenis_produk") in DAFTAR_PRODUK else 0
                    edit_produk = st.selectbox("Jenis Produk", DAFTAR_PRODUK, index=idx_prod)
                    
                    idx_bal = UKURAN_BAL.index(curr.get("ukuran_bal")) if curr.get("ukuran_bal") in UKURAN_BAL else 0
                    edit_bal = st.selectbox("Ukuran Bal", UKURAN_BAL, index=idx_bal)
                    
                    edit_jumlah = st.number_input("Jumlah Ball / Hari", value=float(curr.get("jumlah_borongan", 1.0)), step=0.5, format="%.1f")
                    edit_nominal = st.number_input("Nominal Satuan (Rp)", value=int(curr.get("nominal_satuan", 0)), step=500)
                    
                    if st.form_submit_button("Update Data"):
                        total_new = edit_jumlah * edit_nominal
                        supabase.table("LogHarian").update({
                            "nama_karyawan": edit_nama,
                            "sistem_gaji": edit_sistem,
                            "jenis_produk": edit_produk if edit_sistem == "Borongan" else "-",
                            "ukuran_bal": edit_bal if edit_sistem == "Borongan" else "-",
                            "jumlah_borongan": float(edit_jumlah),
                            "nominal_satuan": int(edit_nominal),
                            "total_gaji": float(total_new)
                        }).eq("id", int(id_edit)).execute()
                        st.success("Data berhasil diperbarui!")
                        st.rerun()
            else:
                st.warning(f"ID {int(id_edit)} tidak ditemukan.")
    else:
        st.info("Belum ada data log.")

# ----------------------------------------------------
# MENU 4: REKAP & EKSPOR EXCEL
# ----------------------------------------------------
elif menu == "Rekap & Ekspor Excel":
    st.subheader("📊 Rekapitulasi Gaji & Laporan Produksi Pabrik Bulanan")
    
    col_b, col_t = st.columns(2)
    with col_b:
        bulan = st.selectbox("Pilih Bulan", range(1, 13), index=datetime.today().month - 1)
    with col_t:
        tahun = st.number_input("Pilih Tahun", value=datetime.today().year, step=1)
        
    res = supabase.table("LogHarian").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        df_filtered = df[(df["tanggal"].dt.month == bulan) & (df["tanggal"].dt.year == tahun)]
        
        if not df_filtered.empty:
            st.divider()
            
            st.markdown("### 1. Rekapitulasi Gaji Karyawan")
            rekap_gaji = df_filtered.groupby(["nama_karyawan", "sistem_gaji"]).agg(
                total_absensi=('tanggal', 'nunique'),
                total_ball=('jumlah_borongan', 'sum'),
                total_gaji=('total_gaji', 'sum')
            ).reset_index()
            st.dataframe(rekap_gaji, use_container_width=True)
            
            st.divider()
            
            st.markdown("### 2. Laporan Hasil Produksi Bungkusan Pabrik")
            df_borongan = df_filtered[df_filtered["sistem_gaji"] == "Borongan"]
            
            if not df_borongan.empty:
                rekap_produksi = df_borongan.groupby(["jenis_produk", "ukuran_bal"]).agg(
                    total_pengerjaan=('id', 'count'),
                    total_hasil_ball=('jumlah_borongan', 'sum')
                ).reset_index().sort_values(by="total_hasil_ball", ascending=False)
                st.dataframe(rekap_produksi, use_container_width=True)
            else:
                st.info("Belum ada data borongan/produksi bungkusan di bulan ini.")
                rekap_produksi = pd.DataFrame()

            # EKSPOR EXCEL
            st.divider()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                rekap_gaji.to_excel(writer, sheet_name='Rekap Gaji Karyawan', index=False)
                if not rekap_produksi.empty:
                    rekap_produksi.to_excel(writer, sheet_name='Laporan Produksi Pabrik', index=False)
                df_filtered.to_excel(writer, sheet_name='Detail Transaksi Log', index=False)
                
            nama_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                          "Juli", "Agustus", "September", "Oktober", "November", "Desember"][bulan - 1]
            
            st.download_button(
                label="📥 Download Laporan Lengkap (.xlsx Excel)",
                data=output.getvalue(),
                file_name=f"Laporan_BBS_Food_{nama_bulan}_{tahun}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Tidak ada transaksi pada bulan & tahun ini.")
    else:
        st.info("Belum ada data.")

# ----------------------------------------------------
# MENU 5: CETAK STRUK TERMAL 58MM
# ----------------------------------------------------
elif menu == "Cetak Struk Termal":
    st.subheader("🖨️ Cetak Struk Rekap Gaji Bulanan (58mm)")
    
    col_b, col_t = st.columns(2)
    with col_b:
        bulan = st.selectbox("Pilih Bulan", range(1, 13), index=datetime.today().month - 1)
    with col_t:
        tahun = st.number_input("Pilih Tahun", value=datetime.today().year, step=1)
        
    res = supabase.table("LogHarian").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        df_filtered = df[(df["tanggal"].dt.month == bulan) & (df["tanggal"].dt.year == tahun)]
        
        if not df_filtered.empty:
            daftar_karyawan = df_filtered["nama_karyawan"].unique()
            pilih_karyawan = st.selectbox("Pilih Nama Karyawan", daftar_karyawan)
            
            df_karyawan = df_filtered[df_filtered["nama_karyawan"] == pilih_karyawan]
            sistem_gaji = df_karyawan["sistem_gaji"].iloc[0]
            total_qty = df_karyawan["jumlah_borongan"].sum()
            total_gaji = df_karyawan["total_gaji"].sum()
            total_hari_kerja = df_karyawan["tanggal"].nunique()
            
            nama_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                          "Juli", "Agustus", "September", "Oktober", "November", "Desember"][bulan - 1]
            
            label_qty = "Total Hasil (Ball)" if sistem_gaji == "Borongan" else "Total Hari Kerja"
            
            struk_html = f"""
            <div class="thermal-receipt">
                <center>
                    <strong>BBS FOOD SRAGEN</strong><br>
                    Jl. Jatibatur, Gemolong<br>
                    --------------------------------<br>
                    <strong>SLIP GAJI BULANAN</strong><br>
                    Periode: {nama_bulan} {tahun}<br>
                    --------------------------------
                </center>
                Nama   : {pilih_karyawan}<br>
                Sistem : {sistem_gaji}<br>
                Absensi: {total_hari_kerja} Hari Masuk<br>
                --------------------------------<br>
                {label_qty} : {total_qty:g}<br>
                --------------------------------<br>
                <strong>TOTAL GAJI: Rp {total_gaji:,.0f}</strong><br>
                --------------------------------<br>
                <center>
                    <i>~ Terima Kasih ~</i>
                </center>
            </div>
            """
            st.markdown(struk_html, unsafe_allow_html=True)
            st.caption("Cetak slip menggunakan printer bluetooth 58mm.")
        else:
            st.warning("Tidak ada transaksi pada periode ini.")
