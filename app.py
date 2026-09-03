import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import calendar
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

# Master Data Produk
DAFTAR_PRODUK = [
    "Makaroni Ori", "Makaroni Pedas", "Stik Ori", "Stik Pedas", 
    "Seblak Mix", "Jengkol", "Kedelai Ori", "Kedelai Pedas", 
    "K. Tongkol Asin", "K. Tongkol Pedas", "Campuran (Mix)", 
    "Marneng Asin", "Marneng Pedas", "Emping Balado Asin", 
    "Emping Pedas Manis", "Mie Enak", "K. Jablay", "Brondong"
]
UKURAN_BAL = ["Isi 10", "Isi 12"]

# Acuan Standard Gaji Bulanan Pabrik
GAJI_BULANAN_KEPALA_REGU = 2500000
GAJI_BULANAN_ANGGOTA = 2377000
GAJI_BULANAN_PACKING_ONLINE = 2000000
GAJI_HARIAN_TETAP_ADMIN = 100000  # Nila (Admin Pabrik)

def get_hari_kerja_efektif(tahun, bulan):
    """Menghitung jumlah hari kerja efektif (Senin-Sabtu)"""
    _, total_hari = calendar.monthrange(tahun, bulan)
    hari_kerja = 0
    for day in range(1, total_hari + 1):
        if calendar.weekday(tahun, bulan, day) != 6:  # 6 = Hari Minggu
            hari_kerja += 1
    return hari_kerja

def get_karyawan_list():
    res = supabase.table("MasterKaryawan").select("*").order("nama_karyawan").execute()
    if res.data:
        return res.data
    return []

# Sidebar Navigasi
menu = st.sidebar.radio("Pilih Menu", [
    "Input Bungkusan Borongan",
    "Presensi Harian & Non-Borongan",
    "Master Karyawan",
    "Data & Edit Log", 
    "Rekap & Ekspor Excel", 
    "Cetak Struk Termal"
])

# ----------------------------------------------------
# MENU 1: INPUT BUNGKUSAN BORONGAN
# ----------------------------------------------------
if menu == "Input Bungkusan Borongan":
    st.subheader("📦 Input Hasil Bungkusan Borongan")
    
    karyawan_data = get_karyawan_list()
    # Filter karyawan borongan / pembungkus
    list_nama = [k["nama_karyawan"] for k in karyawan_data if k.get("divisi") == "Pembungkus / Borongan"] or [k["nama_karyawan"] for k in karyawan_data]
    
    if not list_nama:
        st.warning("⚠️ Belum ada data karyawan borongan. Silakan tambahkan di menu 'Master Karyawan'!")
    else:
        tab_ind, tab_tim = st.tabs(["👤 Input Perorangan", "👥 Input Tim / Beregu (Brondong/Snack)"])

        # TAB 1: INDIVIDU
        with tab_ind:
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                nama_karyawan = st.selectbox("Pilih Nama Karyawan", list_nama, key="ind_nama")
            with col_h2:
                tanggal_masuk = st.date_input("Tanggal Kerja", value=datetime.today(), key="ind_tgl")
            
            st.divider()

            if "items_borongan" not in st.session_state:
                st.session_state["items_borongan"] = []

            with st.form("form_add_item", clear_on_submit=True):
                col_i1, col_i2, col_i3, col_i4 = st.columns([3, 2, 2, 2])
                with col_i1:
                    item_produk = st.selectbox("Jenis Produk", DAFTAR_PRODUK, key="ind_prod")
                with col_i2:
                    item_bal = st.selectbox("Ukuran Bal", UKURAN_BAL, key="ind_bal")
                with col_i3:
                    item_qty = st.number_input("Jumlah (Ball)", min_value=0.1, value=1.0, step=0.5, format="%.1f", key="ind_qty")
                with col_i4:
                    default_tarif = 4500 if item_produk == "Brondong" else 4000
                    item_nominal = st.number_input("Gaji per Ball (Rp)", min_value=0, value=default_tarif, step=500, key="ind_nom")
                
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

            if st.session_state["items_borongan"]:
                st.markdown("**Daftar Bungkusan Siap Disimpan:**")
                df_temp = pd.DataFrame(st.session_state["items_borongan"])
                st.dataframe(df_temp[["jenis_produk", "ukuran_bal", "jumlah_borongan", "nominal_satuan", "total_gaji"]], use_container_width=True)
                
                col_bt1, col_bt2 = st.columns([3, 1])
                with col_bt1:
                    total_semua_gaji = sum(x["total_gaji"] for x in st.session_state["items_borongan"])
                    st.success(f"**Total Gaji Borongan: Rp {total_semua_gaji:,.0f}**")
                with col_bt2:
                    if st.button("🗑️ Kosongkan", key="ind_reset"):
                        st.session_state["items_borongan"] = []
                        st.rerun()

                if st.button("💾 SIMPAN SEMUA DATA LOG", type="primary", use_container_width=True, key="ind_save"):
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
                    st.success(f"Berhasil menyimpan data borongan untuk {nama_karyawan}!")
                    st.session_state["items_borongan"] = []
                    st.rerun()

        # TAB 2: TIM / BEREGU
        with tab_tim:
            st.markdown("##### 👥 Input Bungkusan Beregu / Tim (Bagi Rata Otomatis)")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tgl_tim = st.date_input("Tanggal Kerja", value=datetime.today(), key="tim_tgl")
                produk_tim = st.selectbox("Jenis Produk", DAFTAR_PRODUK, index=DAFTAR_PRODUK.index("Brondong") if "Brondong" in DAFTAR_PRODUK else 0, key="tim_prod")
                bal_tim = st.selectbox("Ukuran Bal", UKURAN_BAL, key="tim_bal")
            with col_t2:
                qty_tim = st.number_input("Total Hasil Tim (Ball)", min_value=0.1, value=10.0, step=0.5, format="%.1f", key="tim_qty")
                default_tarif_tim = 4500 if produk_tim == "Brondong" else 4000
                nominal_tim = st.number_input("Gaji per Ball (Rp)", min_value=0, value=default_tarif_tim, step=500, key="tim_nom")
            
            st.divider()
            pilih_anggota = st.multiselect("Pilih Anggota Tim yang Mengerjakan:", list_nama, key="tim_members")
            
            if pilih_anggota:
                jumlah_anggota = len(pilih_anggota)
                ball_per_orang = qty_tim / jumlah_anggota
                gaji_total_tim = qty_tim * nominal_tim
                gaji_per_orang = gaji_total_tim / jumlah_anggota
                
                st.info(f"""
                **Rincian Pembagian Otomatis ({jumlah_anggota} Orang):**
                * **Total Hasil Tim:** {qty_tim:g} Ball @ Rp {nominal_tim:,.0f} (Total Rp {gaji_total_tim:,.0f})
                * **Jatah per Karyawan:** **{ball_per_orang:.2f} Ball** / orang
                * **Gaji per Karyawan:** **Rp {gaji_per_orang:,.0f}** / orang
                """)
                
                if st.button("💾 SIMPAN HASIL TIM", type="primary", use_container_width=True, key="tim_save"):
                    data_tim_to_insert = []
                    for anggota in pilih_anggota:
                        data_tim_to_insert.append({
                            "nama_karyawan": anggota,
                            "tanggal": str(tgl_tim),
                            "sistem_gaji": "Borongan",
                            "jenis_produk": produk_tim,
                            "ukuran_bal": bal_tim,
                            "jumlah_borongan": float(ball_per_orang),
                            "nominal_satuan": int(nominal_tim),
                            "total_gaji": float(gaji_per_orang)
                        })
                    
                    supabase.table("LogHarian").insert(data_tim_to_insert).execute()
                    st.success(f"Berhasil menyimpan hasil tim untuk {jumlah_anggota} anggota!")
                    st.rerun()

# ----------------------------------------------------
# MENU 2: PRESENSI HARIAN & NON-BORONGAN
# ----------------------------------------------------
elif menu == "Presensi Harian & Non-Borongan":
    st.subheader("⏱️ Input Presensi Harian & Non-Borongan")
    
    tgl_presensi = st.date_input("Tanggal Kerja", value=datetime.today(), key="harian_tgl")
    thn = tgl_presensi.year
    bln = tgl_presensi.month
    
    hari_kerja_bln = get_hari_kerja_efektif(thn, bln)
    
    # Hitung standar harian berdasarkan divisi
    gaji_harian_kepala = GAJI_BULANAN_KEPALA_REGU / hari_kerja_bln
    gaji_harian_anggota = GAJI_BULANAN_ANGGOTA / hari_kerja_bln
    gaji_harian_online = GAJI_BULANAN_PACKING_ONLINE / hari_kerja_bln

    karyawan_data = get_karyawan_list()
    # Exclude karyawan borongan murni jika diinginkan, atau tampilkan semua
    harian_karyawan = [k for k in karyawan_data if k.get("divisi") != "Pembungkus / Borongan"] or karyawan_data

    if not harian_karyawan:
        st.warning("⚠️ Belum ada data karyawan harian.")
    else:
        with st.form("form_presensi_harian", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                pilihan_karyawan = st.selectbox(
                    "Pilih Karyawan", 
                    options=harian_karyawan, 
                    format_func=lambda x: f"{x['nama_karyawan']} — Divisi: {x.get('divisi', '-')} ({x.get('jabatan', 'Anggota')})"
                )
                
                divisi = pilihan_karyawan.get('divisi', '')
                jabatan = pilihan_karyawan.get('jabatan', 'Anggota')
                nama_karyawan = pilihan_karyawan.get('nama_karyawan', '')

                # Penentuan Gaji Standar Berdasarkan Divisi
                if divisi == "Admin Pabrik" or nama_karyawan == "Nila":
                    gaji_std_default = GAJI_HARIAN_TETAP_ADMIN  # Rp 100.000 Flat
                    tipe_pembayaran = "Admin (Flat Harian Rp 100.000 - Tanpa Libur)"
                elif divisi == "Packing Online":
                    gaji_std_default = gaji_harian_online
                    tipe_pembayaran = f"Packing Online (Acuan Rp 2.000.000 / {hari_kerja_bln} hari kerja)"
                else:  # Produksi Brondong (Pemasak)
                    gaji_std_default = gaji_harian_kepala if jabatan == "Kepala Regu" else gaji_harian_anggota
                    tipe_pembayaran = f"Pemasak Brondong - {jabatan}"

                st.info(f"**Tipe Sistem:** {tipe_pembayaran}\n\n**Gaji Harian Standard:** Rp {gaji_std_default:,.0f}")

            with col_p2:
                if divisi == "Produksi Brondong":
                    target_bal = 50
                    hasil_bal = st.number_input("Total Hasil Masak Hari Ini (Bal)", min_value=0, value=50, step=1)
                    st.write(f"🎯 **Target Standard:** {target_bal} Bal / Hari (Khusus Anggota)")
                else:
                    hasil_bal = 1  # Kehadiran 1 Hari penuh
                    st.write("📌 **Kehadiran Kerja Harian Penuh**")

            btn_simpan_harian = st.form_submit_button("💾 Hitung & Simpan Presensi", type="primary")

            if btn_simpan_harian:
                potongan = 0
                catatan = ""
                
                # Logika Penghitungan Gaji
                if divisi == "Admin Pabrik" or nama_karyawan == "Nila":
                    gaji_akhir = GAJI_HARIAN_TETAP_ADMIN
                    catatan = "Presensi Admin Pabrik (Gaji harian Rp 100.000)."
                elif divisi == "Packing Online":
                    gaji_akhir = gaji_std_default
                    catatan = "Presensi Packing Online (Harian acuan 2 juta)."
                else: # Pemasak Brondong
                    if jabatan == "Kepala Regu":
                        gaji_akhir = gaji_std_default
                        catatan = f"Kepala Regu: Gaji utuh Rp {gaji_akhir:,.0f}."
                    else:
                        if hasil_bal >= target_bal:
                            gaji_akhir = gaji_std_default
                            catatan = f"Target tercapai ({hasil_bal}/{target_bal} Bal). Gaji utuh."
                        else:
                            persentase = hasil_bal / target_bal
                            gaji_akhir = gaji_std_default * persentase
                            potongan = gaji_std_default - gaji_akhir
                            catatan = f"Tidak capai target ({hasil_bal}/{target_bal} Bal). Dipotong Rp {potongan:,.0f}."

                payload = {
                    "tanggal": str(tgl_presensi),
                    "nama_karyawan": nama_karyawan,
                    "sistem_gaji": "Harian",
                    "jenis_produk": divisi if divisi else "Harian Standard",
                    "ukuran_bal": "-",
                    "jumlah_borongan": float(hasil_bal),
                    "nominal_satuan": int(gaji_std_default),
                    "total_gaji": float(gaji_akhir)
                }
                
                supabase.table("LogHarian").insert(payload).execute()
                st.success(f"✅ Presensi {nama_karyawan} disimpan! Gaji Hari Ini: **Rp {gaji_akhir:,.0f}** ({catatan})")
                st.rerun()

# ----------------------------------------------------
# MENU 3: MASTER KARYAWAN
# ----------------------------------------------------
elif menu == "Master Karyawan":
    st.subheader("👥 Kelola Master Data Karyawan")
    
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        st.markdown("##### Tambah Karyawan Baru")
        with st.form("form_karyawan", clear_on_submit=True):
            nama_baru = st.text_input("Nama Karyawan")
            divisi_baru = st.selectbox("Divisi Kerja", ["Pembungkus / Borongan", "Produksi Brondong", "Packing Online", "Admin Pabrik", "Produksi Snack"])
            jabatan_baru = st.selectbox("Jabatan", ["Anggota", "Kepala Regu", "Admin"])
            btn_karyawan = st.form_submit_button("Tambah Karyawan")
            
            if btn_karyawan:
                if nama_baru:
                    try:
                        payload_k = {
                            "nama_karyawan": nama_baru.strip().title(),
                            "divisi": divisi_baru,
                            "jabatan": jabatan_baru
                        }
                        supabase.table("MasterKaryawan").insert(payload_k).execute()
                        st.success(f"Karyawan '{nama_baru.strip().title()}' berhasil ditambahkan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal menyimpan ke Supabase! Pastikan kolom 'divisi' dan 'jabatan' sudah dibuat di tabel 'MasterKaryawan'. Detail Error: {e}")
                else:
                    st.error("Nama karyawan wajib diisi!")

    with col_k2:
        st.markdown("##### Daftar Karyawan Terdaftar")
        res_k = supabase.table("MasterKaryawan").select("*").order("nama_karyawan").execute()
        if res_k.data:
            df_k = pd.DataFrame(res_k.data)
            cols_show = [c for c in ["id", "nama_karyawan", "divisi", "jabatan"] if c in df_k.columns]
            st.dataframe(df_k[cols_show], use_container_width=True)
            
            id_del_k = st.number_input("Hapus ID Karyawan", min_value=1, step=1, value=1)
            if st.button("Hapus Karyawan"):
                supabase.table("MasterKaryawan").delete().eq("id", int(id_del_k)).execute()
                st.success("Karyawan berhasil dihapus!")
                st.rerun()
        else:
            st.info("Belum ada data karyawan.")
            import streamlit as st

# ... (kode aplikasi Anda)

# Mengambil daftar karyawan dari Supabase
res = supabase.table("MasterKaryawan").select("*").execute()
data_karyawan = res.data

if data_karyawan:
    st.subheader("✏️ Edit Data Karyawan Lama")
    
    # Pilih karyawan yang ingin diubah
    list_nama = [k["nama_karyawan"] for k in data_karyawan]
    karyawan_pilihan = st.selectbox("Pilih Karyawan yang ingin diupdate:", list_nama)
    
    # Cari data detail karyawan terpilih
    detail_k = next((item for item in data_karyawan if item["nama_karyawan"] == karyawan_pilihan), None)
    
    if detail_k:
        with st.form("form_edit_karyawan"):
            divisi_opsi = ["Produksi", "Pembungkus", "Packing Online", "Snack", "Admin Pabrik"]
            
            # Cari index awal agar selectbox otomatis memilih divisi saat ini
            idx_div = divisi_opsi.index(detail_k.get("divisi")) if detail_k.get("divisi") in divisi_opsi else 0
            
            divisi_edit = st.selectbox("Divisi", divisi_opsi, index=idx_div)
            jabatan_edit = st.text_input("Jabatan", value=detail_k.get("jabatan") or "Anggota")
            
            btn_update = st.form_submit_button("💾 Simpan Perubahan")
            
            if btn_update:
                try:
                    supabase.table("MasterKaryawan").update({
                        "divisi": divisi_edit,
                        "jabatan": jabatan_edit
                    }).eq("id", detail_k["id"]).execute()
                    
                    st.success(f"Data {karyawan_pilihan} berhasil diperbarui!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal memperbarui data: {e}")

# ----------------------------------------------------
# MENU 4: DATA & EDIT LOG
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
        
        col_del, col_edit = st.columns(2)
        with col_del:
            st.subheader("🗑️ Hapus Data Log")
            id_hapus = st.number_input("Masukkan ID Data yang akan dihapus", min_value=1, step=1, value=1)
            if st.button("Hapus Data Log", type="primary"):
                supabase.table("LogHarian").delete().eq("id", int(id_hapus)).execute()
                st.success(f"Data ID {id_hapus} berhasil dihapus!")
                st.rerun()

        with col_edit:
            st.subheader("✏️ Edit Data Log")
            id_edit = st.number_input("Masukkan ID Data yang akan diubah", min_value=1, step=1, value=1)
            data_edit = [d for d in res.data if d["id"] == int(id_edit)]
            
            if data_edit:
                curr = data_edit[0]
                karyawan_list = get_karyawan_list()
                list_nama = [k["nama_karyawan"] for k in karyawan_list]
                
                with st.form("form_edit"):
                    idx_nama = list_nama.index(curr.get("nama_karyawan")) if curr.get("nama_karyawan") in list_nama else 0
                    edit_nama = st.selectbox("Nama Karyawan", list_nama if list_nama else [curr.get("nama_karyawan")], index=idx_nama)
                    edit_sistem = st.selectbox("Sistem Gaji", ["Borongan", "Harian"], index=0 if curr.get("sistem_gaji") == "Borongan" else 1)
                    
                    edit_produk = st.text_input("Jenis / Divisi Produk", value=str(curr.get("jenis_produk", "")))
                    edit_jumlah = st.number_input("Jumlah Ball / Hari", value=float(curr.get("jumlah_borongan", 1.0)), step=0.5, format="%.1f")
                    edit_nominal = st.number_input("Nominal Satuan (Rp)", value=int(curr.get("nominal_satuan", 0)), step=500)
                    
                    if st.form_submit_button("Update Data"):
                        total_new = edit_jumlah * edit_nominal
                        supabase.table("LogHarian").update({
                            "nama_karyawan": edit_nama,
                            "sistem_gaji": edit_sistem,
                            "jenis_produk": edit_produk,
                            "jumlah_borongan": float(edit_jumlah),
                            "nominal_satuan": int(edit_nominal),
                            "total_gaji": float(total_new)
                        }).eq("id", int(id_edit)).execute()
                        st.success("Data berhasil diperbarui!")
                        st.rerun()

# ----------------------------------------------------
# MENU 5: REKAP & EKSPOR EXCEL
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
                total_hasil=('jumlah_borongan', 'sum'),
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

# ----------------------------------------------------
# MENU 6: CETAK STRUK TERMAL
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
                Total Hasil : {total_qty:g} Ball/Hari<br>
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
