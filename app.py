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
    "Kasbon Karyawan",
    "Stok Bahan & Kemasan"
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
# PADA MENU: Input Bungkusan Borongan
# ----------------------------------------------------

if btn_simpan_borongan:
    try:
        # 1. Simpan Transaksi Log Borongan (Kode Lama)
        payload_borongan = {
            "tanggal": str(tgl_borongan),
            "nama_karyawan": nama_borongan,
            "sistem_gaji": "Borongan",
            "jenis_produk": jenis_produk,
            "ukuran_bal": ukuran_bal,
            "jumlah_borongan": float(jumlah_bal),
            "upah_per_bal": float(tarif_bal),
            "total_gaji": float(total_upah)
        }
        supabase.table("LogHarian").insert(payload_borongan).execute()
        
        # ----------------------------------------------------
        # FITUR BOM (BILL OF MATERIALS) - POTONG MULTI STOK
        # ----------------------------------------------------
        jml_bal = float(jumlah_bal)
        
        # Resep Komposisi Kemasan per 1 Bal
        kebutuhan_kemasan = [
            {"kata_kunci": "Bungkus Makaroni 18g", "jumlah_per_bal": 120 * jml_bal, "satuan": "Pcs"},
            {"kata_kunci": "Bungkus Pack", "jumlah_per_bal": 10 * jml_bal, "satuan": "Pcs"},
            {"kata_kunci": "Bungkus Bal", "jumlah_per_bal": 1 * jml_bal, "satuan": "Pcs"}
        ]
        
        res_stok_all = supabase.table("StokBahan").select("*").execute()
        data_stok_db = res_stok_all.data if res_stok_all.data else []
        
        for item_resep in kebutuhan_kemasan:
            # Cari item di database yang namanya cocok dengan kata kunci resep
            match_bahan = next((b for b in data_stok_db if item_resep["kata_kunci"].lower() in b["nama_bahan"].lower()), None)
            
            if match_bahan:
                stok_lama = float(match_bahan["stok_saat_ini"])
                pemakaian = float(item_resep["jumlah_per_bal"])
                stok_baru = stok_lama - pemakaian
                
                # 1. Update sisa stok baru
                supabase.table("StokBahan").update({"stok_saat_ini": stok_baru}).eq("id", match_bahan["id"]).execute()
                
                # 2. Catat Log Keluar Kemasan
                payload_log_stok = {
                    "tanggal": str(tgl_borongan),
                    "nama_bahan": match_bahan["nama_bahan"],
                    "jenis_transaksi": "Keluar (Produksi/Rusak)",
                    "jumlah": pemakaian,
                    "keterangan": f"Pemakaian Otomatis ({jml_bal:.0f} Bal {jenis_produk} oleh {nama_borongan})"
                }
                supabase.table("LogStok").insert(payload_log_stok).execute()
        
        st.success(f"✅ Borongan berhasil disimpan! Stok 120 Pcs Bungkus Kecil, 10 Pcs Pack, dan 1 Pcs Bal untuk {jml_bal:.0f} Bal otomatis berkurang.")
        st.rerun()

    except Exception as e:
        st.error(f"Gagal menyimpan transaksi: {e}")
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
# MENU 3: KASBON KARYAWAN
# ----------------------------------------------------
elif menu == "Kasbon Karyawan":
    st.subheader("💵 Pencatatan Kasbon / Pinjaman Karyawan")
    
    karyawan_data = get_karyawan_list()
    # Menampilkan hanya karyawan yang berstatus Aktif
    list_karyawan_aktif = [k["nama_karyawan"] for k in karyawan_data if k.get("status", "Aktif") == "Aktif"]
    
    if not list_karyawan_aktif:
        st.warning("⚠️ Belum ada data karyawan aktif.")
    else:
        col_ks1, col_ks2 = st.columns([1, 1])
        
        # TABEL INPUT KASBON BARU
        with col_ks1:
            st.markdown("##### ➕ Input Kasbon Baru (Bon Sabtu)")
            with st.form("form_kasbon", clear_on_submit=True):
                tgl_kasbon = st.date_input("Tanggal Kasbon", value=datetime.today())
                nama_kasbon = st.selectbox("Pilih Karyawan", list_karyawan_aktif)
                nominal_kasbon = st.number_input("Nominal Kasbon (Rp)", min_value=5000, step=5000, value=50000)
                ket_kasbon = st.text_input("Keterangan / Catatan", value="Bon Sabtu")
                
                btn_simpan_kasbon = st.form_submit_button("💾 Simpan Kasbon", type="primary")
                
                if btn_simpan_kasbon:
                    try:
                        payload_kasbon = {
                            "tanggal": str(tgl_kasbon),
                            "nama_karyawan": nama_kasbon,
                            "nominal": float(nominal_kasbon),
                            "keterangan": ket_kasbon
                        }
                        supabase.table("Kasbon").insert(payload_kasbon).execute()
                        st.success(f"✅ Kasbon Rp {nominal_kasbon:,.0f} untuk {nama_kasbon} berhasil dicatat!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan kasbon: {e}")

        # TABEL RIWAYAT & HAPUS KASBON
        with col_ks2:
            st.markdown("##### 📋 Riwayat Transaksi Kasbon")
            res_bon = supabase.table("Kasbon").select("*").order("id", desc=True).limit(20).execute()
            
            if res_bon.data:
                df_bon = pd.DataFrame(res_bon.data)
                st.dataframe(df_bon[["id", "tanggal", "nama_karyawan", "nominal", "keterangan"]], use_container_width=True)
                
                st.divider()
                id_hapus_bon = st.number_input("Hapus Kasbon ID", min_value=1, step=1, value=1)
                if st.button("🗑️ Hapus Kasbon"):
                    try:
                        supabase.table("Kasbon").delete().eq("id", int(id_hapus_bon)).execute()
                        st.success(f"Kasbon ID {id_hapus_bon} berhasil dihapus!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus: {e}")
            else:
                st.info("Belum ada riwayat transaksi kasbon.")
# ----------------------------------------------------
# MENU 4: STOK BAHAN BAKU & KEMASAN
# ----------------------------------------------------
elif menu == "Stok Bahan & Kemasan":
    st.subheader("📦 Manajemen Stok Bahan Baku & Kemasan")
    
    # Fungsi Ambil Data Stok
    res_stok = supabase.table("StokBahan").select("*").order("nama_bahan").execute()
    data_stok = res_stok.data if res_stok.data else []
    
    tab1, tab2, tab3 = st.tabs(["📊 Ringkasan Stok", "➕ Transaksi Stok (Masuk/Keluar)", "⚙️ Tambah / Edit Master Bahan"])
    
    # ------------------------------------------------
    # TAB 1: RINGKASAN STOK & WARNING STOK MINIMUM
    # ------------------------------------------------
    with tab1:
        st.markdown("##### 📌 Status Stok Bahan Baku & Kemasan Saat Ini")
        
        if data_stok:
            df_stok = pd.DataFrame(data_stok)
            
            # Cek Peringatan Stok Tipis
            stok_tipis = df_stok[df_stok["stok_saat_ini"] <= df_stok["stok_minimum"]]
            if not stok_tipis.empty:
                st.warning("⚠️ **PERINGATAN: Bahan/Kemasan Berikut Sudah Hampir Habis!**")
                for _, row in stok_tipis.iterrows():
                    st.write(f"- 🔴 **{row['nama_bahan']}**: Sisa **{row['stok_saat_ini']:,.0f} {row['satuan']}** (Min: {row['stok_minimum']} {row['satuan']})")
                st.divider()

            # Format Tampilan Tabel
            df_tampil = df_stok[["nama_bahan", "kategori", "stok_saat_ini", "satuan", "stok_minimum"]].copy()
            df_tampil.columns = ["Nama Bahan / Kemasan", "Kategori", "Stok Saat Ini", "Satuan", "Stok Minimum"]
            st.dataframe(df_tampil, use_container_width=True)
        else:
            st.info("Belum ada data bahan/kemasan. Silakan tambahkan di tab 'Tambah / Edit Master Bahan'.")

    # ------------------------------------------------
    # TAB 2: INPUT TRANSAKSI MASUK / KELUAR
    # ------------------------------------------------
    with tab2:
        st.markdown("##### 📝 Pencatatan Stok Masuk (Pembelian) atau Keluar (Produksi/Rusak)")
        
        if data_stok:
            list_nama_bahan = [b["nama_bahan"] for b in data_stok]
            
            with st.form("form_trx_stok", clear_on_submit=True):
                tgl_trx = st.date_input("Tanggal Transaksi", value=datetime.today())
                bahan_terpilih = st.selectbox("Pilih Bahan / Kemasan", list_nama_bahan)
                jenis_trx = st.selectbox("Jenis Transaksi", ["Masuk (Pembelian)", "Keluar (Produksi/Rusak)"])
                jumlah_trx = st.number_input("Jumlah Ops", min_value=0.1, step=1.0, value=10.0)
                ket_trx = st.text_input("Keterangan / Beli Di Mana / Digunakan Untuk", value="Pembelian Rutin")
                
                btn_simpan_trx = st.form_submit_button("💾 Simpan Transaksi Stok", type="primary")
                
                if btn_simpan_trx:
                    try:
                        # Cari data bahan
                        item_bahan = next(b for b in data_stok if b["nama_bahan"] == bahan_terpilih)
                        stok_lama = float(item_bahan["stok_saat_ini"])
                        
                        # Hitung Stok Baru
                        if jenis_trx == "Masuk (Pembelian)":
                            stok_baru = stok_lama + float(jumlah_trx)
                        else:
                            stok_baru = stok_lama - float(jumlah_trx)
                        
                        # 1. Update Stok di Supabase
                        supabase.table("StokBahan").update({"stok_saat_ini": stok_baru}).eq("id", item_bahan["id"]).execute()
                        
                        # 2. Catat Log Transaksi
                        payload_log = {
                            "tanggal": str(tgl_trx),
                            "nama_bahan": bahan_terpilih,
                            "jenis_transaksi": jenis_trx,
                            "jumlah": float(jumlah_trx),
                            "keterangan": ket_trx
                        }
                        supabase.table("LogStok").insert(payload_log).execute()
                        
                        st.success(f"✅ Berhasil! Stok {bahan_terpilih} sekarang: {stok_baru:,.1f} {item_bahan['satuan']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal memperbarui stok: {e}")
                        
            st.divider()
            st.markdown("##### 📋 Riwayat 15 Transaksi Stok Terakhir")
            res_log_stok = supabase.table("LogStok").select("*").order("id", desc=True).limit(15).execute()
            if res_log_stok.data:
                st.dataframe(pd.DataFrame(res_log_stok.data)[["tanggal", "nama_bahan", "jenis_transaksi", "jumlah", "keterangan"]], use_container_width=True)
        else:
            st.warning("Tambahkan bahan/kemasan terlebih dahulu di tab sebelah.")

    # ------------------------------------------------
    # TAB 3: MASTER BAHAN & KEMASAN
    # ------------------------------------------------
    with tab3:
        col_m1, col_m2 = st.columns([1, 1])
        
        with col_m1:
            st.markdown("##### ➕ Tambah Item Bahan / Kemasan Baru")
            with st.form("form_master_bahan", clear_on_submit=True):
                nama_b_baru = st.text_input("Nama Bahan / Kemasan", placeholder="Contoh: Plastik Bal 18g, Bumbu Bawang, dll")
                kat_b_baru = st.selectbox("Kategori", ["Kemasan/Plastik", "Bahan Baku Mentah", "Bumbu & Minyak", "Lain-Lain"])
                stok_awal = st.number_input("Stok Awal Saat Ini", min_value=0.0, step=1.0, value=0.0)
                satuan_b = st.selectbox("Satuan", ["Kg", "Bal", "Roll", "Pcs", "Lbr", "Liter"])
                stok_min = st.number_input("Batas Stok Minimum (Warning)", min_value=1.0, step=1.0, value=10.0)
                
                btn_simpan_master = st.form_submit_button("➕ Simpan Bahan Baru", type="primary")
                
                if btn_simpan_master:
                    if nama_b_baru.strip() == "":
                        st.error("Nama bahan tidak boleh kosong!")
                    else:
                        try:
                            payload_master = {
                                "nama_bahan": nama_b_baru.strip(),
                                "kategori": kat_b_baru,
                                "stok_saat_ini": float(stok_awal),
                                "satuan": satuan_b,
                                "stok_minimum": float(stok_min)
                            }
                            supabase.table("StokBahan").insert(payload_master).execute()
                            st.success(f"✅ Item '{nama_b_baru}' berhasil ditambahkan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan: {e}")

        with col_m2:
            st.markdown("##### 🗑️ Hapus Item Master Bahan")
            if data_stok:
                with st.form("form_hapus_bahan"):
                    item_hapus = st.selectbox("Pilih Bahan yang Akan Dihapus", [b["nama_bahan"] for b in data_stok])
                    btn_hapus = st.form_submit_button("🗑️ Hapus Item Master")
                    
                    if btn_hapus:
                        try:
                            supabase.table("StokBahan").delete().eq("nama_bahan", item_hapus).execute()
                            st.success(f"Item '{item_hapus}' berhasil dihapus.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus: {e}")
# ----------------------------------------------------
# MENU 5: MASTER KARYAWAN
# ----------------------------------------------------
elif menu == "Master Karyawan":
    st.subheader("👥 Kelola Master Data Karyawan")
    
    col_k1, col_k2 = st.columns(2)
    
    # KOLOM 1: TAMBAH KARYAWAN BARU
    with col_k1:
        st.subheader("➕ Tambah Karyawan Baru")
        with st.form("form_tambah_karyawan"):
            nama_baru = st.text_input("Nama Karyawan")
            divisi_baru = st.selectbox("Divisi", ["Produksi", "Pembungkus", "Packing Online", "Snack", "Admin Pabrik"])
            jabatan_baru = st.selectbox("Jabatan", ["Anggota", "Kepala Regu"])
            status_baru = st.selectbox("Status", ["Aktif", "Non-Aktif"])
            
            btn_karyawan = st.form_submit_button("➕ Tambah Karyawan")

            if btn_karyawan:
                if nama_baru:
                    try:
                        payload_k = {
                            "nama_karyawan": nama_baru.strip().title(),
                            "divisi": divisi_baru,
                            "jabatan": jabatan_baru,
                            "status": status_baru
                        }
                        supabase.table("MasterKaryawan").insert(payload_k).execute()
                        st.success(f"Karyawan '{nama_baru.strip().title()}' berhasil ditambahkan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data: {e}")
                else:
                    st.error("Nama karyawan wajib diisi!")

    # KOLOM 2: EDIT & KELOLA DATA KARYAWAN LAMA
    with col_k2:
        res = supabase.table("MasterKaryawan").select("*").order("nama_karyawan").execute()
        data_karyawan = res.data

        if data_karyawan:
            st.subheader("✏️ Edit Data & Status Karyawan")
            
            list_nama = [f"{k['nama_karyawan']} ({k.get('status', 'Aktif')})" for k in data_karyawan]
            karyawan_pilihan_str = st.selectbox("Pilih Karyawan yang ingin diubah:", list_nama)
            
            idx_pilihan = list_nama.index(karyawan_pilihan_str)
            detail_k = data_karyawan[idx_pilihan]
            
            with st.form("form_edit_karyawan"):
                divisi_opsi = ["Produksi", "Pembungkus", "Packing Online", "Snack", "Admin Pabrik"]
                status_opsi = ["Aktif", "Non-Aktif"]
                
                idx_div = divisi_opsi.index(detail_k.get("divisi")) if detail_k.get("divisi") in divisi_opsi else 0
                idx_stat = status_opsi.index(detail_k.get("status")) if detail_k.get("status") in status_opsi else 0
                
                divisi_edit = st.selectbox("Divisi", divisi_opsi, index=idx_div)
                jabatan_edit = st.text_input("Jabatan", value=detail_k.get("jabatan") or "Anggota")
                status_edit = st.selectbox("Status Karyawan", status_opsi, index=idx_stat)
                
                btn_update = st.form_submit_button("💾 Simpan Perubahan")
                
                if btn_update:
                    try:
                        supabase.table("MasterKaryawan").update({
                            "divisi": divisi_edit,
                            "jabatan": jabatan_edit,
                            "status": status_edit
                        }).eq("id", detail_k["id"]).execute()
                        
                        st.success(f"Data {detail_k['nama_karyawan']} berhasil diperbarui!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal memperbarui data: {e}")
        else:
            st.info("Belum ada data karyawan terdaftar.")
#----------------------------------------------------
# MENU 6: DATA & EDIT LOG
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
# MENU 7: REKAP & EKSPOR EXCEL
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
# PERBAIKAN MENU REKAP: POTONG KASBON OTOMATIS
# ----------------------------------------------------
elif menu == "Rekap & Ekspor Excel":
    st.subheader("📊 Rekapitulasi Gaji & Laporan Produksi Pabrik Bulanan")
    
    col_b, col_t = st.columns(2)
    with col_b:
        bulan = st.selectbox("Pilih Bulan", range(1, 13), index=datetime.today().month - 1)
    with col_t:
        tahun = st.number_input("Pilih Tahun", value=datetime.today().year, step=1)
        
    res = supabase.table("LogHarian").select("*").execute()
    res_kasbon = supabase.table("Kasbon").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        df_filtered = df[(df["tanggal"].dt.month == bulan) & (df["tanggal"].dt.year == tahun)]
        
        # Filter Data Kasbon
        if res_kasbon.data:
            df_k = pd.DataFrame(res_kasbon.data)
            df_k["tanggal"] = pd.to_datetime(df_k["tanggal"])
            df_k_filtered = df_k[(df_k["tanggal"].dt.month == bulan) & (df_k["tanggal"].dt.year == tahun)]
        else:
            df_k_filtered = pd.DataFrame(columns=["nama_karyawan", "nominal"])
        
        if not df_filtered.empty:
            st.divider()
            st.markdown("### 1. Rekapitulasi Gaji Karyawan (Setelah Potongan Kasbon)")
            
            # Hitung Gaji Kotor
            rekap_gaji = df_filtered.groupby(["nama_karyawan", "sistem_gaji"]).agg(
                total_absensi=('tanggal', 'nunique'),
                total_hasil=('jumlah_borongan', 'sum'),
                gaji_kotor=('total_gaji', 'sum')
            ).reset_index()
            
            # Hitung Total Kasbon per Karyawan
            if not df_k_filtered.empty:
                rekap_bon = df_k_filtered.groupby("nama_karyawan")["nominal"].sum().reset_index()
                rekap_bon.rename(columns={"nominal": "total_kasbon"}, inplace=True)
                rekap_gaji = pd.merge(rekap_gaji, rekap_bon, on="nama_karyawan", how="left")
            else:
                rekap_gaji["total_kasbon"] = 0
                
            rekap_gaji["total_kasbon"] = rekap_gaji["total_kasbon"].fillna(0)
            
            # Gaji Bersih = Gaji Kotor - Total Kasbon
            rekap_gaji["gaji_bersih"] = rekap_gaji["gaji_kotor"] - rekap_gaji["total_kasbon"]
            
            # Tampilkan Tabel
            st.dataframe(
                rekap_gaji[["nama_karyawan", "sistem_gaji", "total_absensi", "total_hasil", "gaji_kotor", "total_kasbon", "gaji_bersih"]],
                use_container_width=True)
# ----------------------------------------------------
# MENU 8: CETAK STRUK TERMAL
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
