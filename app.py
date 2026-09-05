import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import calendar
import io

# ==========================================
# KONSTANTA GAJI STANDAR BBS FOOD
# ==========================================
GAJI_BULANAN_KEPALA_REGU = 2500000     # Gaji acuan Kepala Regu Bulanan
GAJI_BULANAN_ANGGOTA = 2377000         # Gaji acuan Anggota Bulanan (Pemasak Brondong & Snack)
GAJI_BULANAN_PACKING_ONLINE = 2000000  # Gaji acuan Packing Online Bulanan
GAJI_HARIAN_TETAP_ADMIN = 100000       # Gaji flat Admin Pabrik per hari

# ====================================================
# FUNGSI MENGHITUNG HARI KERJA EFEKTIF DINAMIS
# ====================================================
def get_hari_kerja_efektif(tahun, bulan):
    """
    Menghitung hari kerja efektif (Total hari dalam 1 bulan DIKURANGI Hari Minggu).
    """
    total_hari = calendar.monthrange(tahun, bulan)[1]
    jumlah_minggu = 0
    for day in range(1, total_hari + 1):
        if calendar.weekday(tahun, bulan, day) == 6:  # 6 = Hari Minggu
            jumlah_minggu += 1
    return max(total_hari - jumlah_minggu, 1)

def get_hari_kerja_abk(tahun, bulan):
    """
    Menghitung hari kerja ABK Kandang (Total hari dalam bulan - 2 hari libur).
    """
    total_hari_bulan = calendar.monthrange(tahun, bulan)[1]
    return max(total_hari_bulan - 2, 1)

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
    "Emping Pedas Manis", "Mie Enak", "K. Jablay", "Brondong", "Kedelai Mesin","Rambut Nenek", "K.Manggar", "Usus Pedas", "Usus Ori"
]
UKURAN_BAL = ["Isi 10", "Isi 12"]

def get_karyawan_list():
    res = supabase.table("MasterKaryawan").select("*").order("nama_karyawan").execute()
    if res.data:
        return res.data
    return []

# Sidebar Navigasi
menu = st.sidebar.radio("Pilih Menu", [
    "1. Input Bungkusan Borongan",
    "2. Input Absensi & Gaji Harian/Bulanan",
    "3. Kasbon Karyawan",
    "4. Master Karyawan",
    "5. Data & Edit Log", 
    "6. Rekap & Ekspor Excel", 
    "7. Cetak Struk Termal"
])

# ----------------------------------------------------
# MENU 1: INPUT BUNGKUSAN BORONGAN
# ----------------------------------------------------
if menu == "1. Input Bungkusan Borongan":
    st.subheader("📦 Input Hasil Bungkusan Borongan")
    
    karyawan_data = get_karyawan_list()
    list_nama = [k["nama_karyawan"] for k in karyawan_data]
    
    if not list_nama:
        st.warning("⚠️ Belum ada data karyawan. Silakan tambahkan di menu 'Master Karyawan' terlebih dahulu!")
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
                
                # --- FITUR DENGAN GAJI POKOK PADA PEMBUNGKUS NON-BRONDONG ---
                gaji_pokok_tambahan = 0
                if item_produk != "Brondong":
                    st.markdown("---")
                    pake_gaji_pokok = st.checkbox("Tambahkan Gaji Pokok Harian Pembungkus Non-Brondong", value=False)
                    if pake_gaji_pokok:
                        gaji_pokok_tambahan = st.number_input("Nominal Gaji Pokok Harian (Rp)", min_value=0, value=20000, step=5000)

                btn_add = st.form_submit_button("➕ Tambahkan ke Daftar")
                if btn_add:
                    total_item_gaji = (item_qty * item_nominal) + gaji_pokok_tambahan
                    st.session_state["items_borongan"].append({
                        "jenis_produk": item_produk + (" + GP" if gaji_pokok_tambahan > 0 else ""),
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
                    st.success(f"Berhasil menyimpan {len(data_to_insert)} item produksi untuk {nama_karyawan}!")
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
                    st.success(f"Berhasil menyimpan hasil {produk_tim} untuk {jumlah_anggota} anggota tim!")
                    st.rerun()

# ----------------------------------------------------
# MENU 2: INPUT ABSENSI & GAJI HARIAN/BULANAN
# ----------------------------------------------------
elif menu == "2. Input Absensi & Gaji Harian/Bulanan":
    st.subheader("🗓️ Input Absensi & Gaji Harian")
    
    karyawan_data = get_karyawan_list()
    if not karyawan_data:
        st.warning("⚠️ Belum ada data karyawan. Tambahkan di menu Master Karyawan!")
    else:
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            tgl_absen = st.date_input("Tanggal Masuk Kerja", value=datetime.today(), key="abs_tgl")
            
            # Filter Karyawan Non-Borongan / Harian / ABK Kandang
            list_karyawan_harian = [
                k for k in karyawan_data 
                if k.get("divisi") in ["Produksi Brondong", "Produksi Snack", "Admin Pabrik", "Packing Online", "ABK Kandang"]
            ]
            
            if not list_karyawan_harian:
                dict_karyawan = {k["nama_karyawan"]: k for k in karyawan_data}
            else:
                dict_karyawan = {k["nama_karyawan"]: k for k in list_karyawan_harian}
                
            pilih_nama_absen = st.selectbox("Pilih Karyawan", list(dict_karyawan.keys()))
            karyawan_terpilih = dict_karyawan[pilih_nama_absen]

            # Input Status Kehadiran
            status_hadir = st.radio("Status Kehadiran:", ["Masuk Full (1 Hari)", "Setengah Hari (0.5 Hari)"], horizontal=True)
            faktor_kehadiran = 1.0 if status_hadir == "Masuk Full (1 Hari)" else 0.5

        divisi = karyawan_terpilih.get("divisi", "Produksi Brondong")
        jabatan = karyawan_terpilih.get("jabatan", "Anggota")
        
        # Parameter Kalender Bulan Berjalan
        thn_cur, bln_cur = tgl_absen.year, tgl_absen.month
        hari_efektif_pabrik = get_hari_kerja_efektif(thn_cur, bln_cur)
        total_hari_kalender = calendar.monthrange(thn_cur, bln_cur)[1]

        # ----------------------------------------------------
        # PERHITUNGAN BASE GAJI STANDAR HARIAN
        # ----------------------------------------------------
        if divisi == "ABK Kandang":
            # Gaji Rp 2.377.000 untuk kerja full 1 bulan minus 2 hari libur
            target_hk_abk = total_hari_kalender - 2
            gaji_standar_harian = 2377000 / target_hk_abk
            ket_hari_kerja = f"Target ABK Kandang: {target_hk_abk} Hari ({total_hari_kalender}-2 Hari)"
        elif divisi == "Admin Pabrik":
            gaji_standar_harian = GAJI_HARIAN_TETAP_ADMIN
            ket_hari_kerja = f"Hari Kerja Pabrik: {hari_efektif_pabrik} Hari"
        elif divisi == "Packing Online":
            gaji_standar_harian = GAJI_BULANAN_PACKING_ONLINE / hari_efektif_pabrik
            ket_hari_kerja = f"Hari Kerja Pabrik: {hari_efektif_pabrik} Hari"
        else: # Produksi Brondong / Snack
            ket_hari_kerja = f"Hari Kerja Pabrik: {hari_efektif_pabrik} Hari"
            if jabatan == "Kepala Regu":
                gaji_standar_harian = GAJI_BULANAN_KEPALA_REGU / hari_efektif_pabrik
            else:
                gaji_standar_harian = GAJI_BULANAN_ANGGOTA / hari_efektif_pabrik

        # Penyesuaian Faktor Kehadiran (Full vs Setengah Hari)
        gaji_setelah_absensi = gaji_standar_harian * faktor_kehadiran

        st.divider()

        # LOGIKA PROSES PERHITUNGAN KHUSUS DIVISI
        gaji_akhir = gaji_setelah_absensi
        catatan_target = ""
        
        if divisi == "Produksi Brondong":
            st.markdown("##### 🎯 Target Produksi Brondong Harian (Acuan Standard: 50 Ball)")
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                target_standar = 50.0
                hasil_actual = st.number_input("Capaian Hasil Produksi (Ball)", min_value=0.0, value=50.0, step=1.0)
            
            # Perhitungan Proporsional (Hasil Actual / 50 * Gaji Harian)
            gaji_akhir = (hasil_actual / target_standar) * gaji_setelah_absensi
            tarif_per_bal = gaji_setelah_absensi / target_standar
            
            with col_t2:
                if hasil_actual < target_standar:
                    selisih_bal = target_standar - hasil_actual
                    potongan_rp = selisih_bal * tarif_per_bal
                    catatan_target = f"Kurang {selisih_bal:g} Bal ({hasil_actual:g}/50) | Potong Rp {potongan_rp:,.0f}"
                    st.warning(f"⚠️ Kurang target {selisih_bal:g} bal. Gaji dipotong Rp {potongan_rp:,.0f}")
                elif hasil_actual > target_standar:
                    bonus_bal = hasil_actual - target_standar
                    bonus_rp = bonus_bal * tarif_per_bal
                    catatan_target = f"Bonus +{bonus_bal:g} Bal ({hasil_actual:g}/50) | Bonus Rp {bonus_rp:,.0f}"
                    st.success(f"🎉 Lebih target +{bonus_bal:g} bal. Diberikan bonus Rp {bonus_rp:,.0f}")
                else:
                    catatan_target = "Target Pas (50 Bal)"
                    st.info("✅ Target 50 Ball tercapai pas (100%).")
                    
        elif divisi == "ABK Kandang":
            st.info("📌 Divisi ABK Kandang: Perhitungan gaji bulanan Rp 2.377.000 (Target masuk full 1 bulan - 2 hari libur, tanpa bonus target).")

        with col_a2:
            st.markdown("##### Rincian Perhitungan Gaji:")
            st.info(f"""
            * **Divisi / Jabatan**: {divisi} ({jabatan})
            * **Ketentuan Hari Kerja**: {ket_hari_kerja}
            * **Status Hadir**: {status_hadir}
            * **Gaji Acuan Harian**: Rp {gaji_setelah_absensi:,.0f}
            * **Status Target**: {catatan_target if divisi == "Produksi Brondong" else "Tanpa Bonus Target"}
            * **Total Diterima Hari Ini**: **Rp {gaji_akhir:,.0f}**
            """)

        with st.form("form_simpan_absensi_abk"):
            override_gaji = st.number_input(
                "Nominal Final Gaji yang Disimpan (Rp)", 
                min_value=0.0, 
                value=float(round(gaji_akhir)), 
                step=1000.0
            )
            
            btn_absensi = st.form_submit_button("💾 Simpan Log Absensi & Gaji", type="primary")

            if btn_absensi:
                ket_simpan = f"{status_hadir}"
                if divisi == "Produksi Brondong":
                    ket_simpan += f" | {catatan_target}"
                elif divisi == "ABK Kandang":
                    ket_simpan += " | ABK Kandang (Rp 2.377.000/Bln)"

                payload_absensi = {
                    "nama_karyawan": pilih_nama_absen,
                    "tanggal": str(tgl_absen),
                    "sistem_gaji": "Harian",
                    "jenis_produk": f"Absensi {divisi}",
                    "ukuran_bal": ket_simpan,
                    "jumlah_borongan": float(hasil_actual) if divisi == "Produksi Brondong" else (1.0 if faktor_kehadiran == 1.0 else 0.5),
                    "nominal_satuan": int(override_gaji),
                    "total_gaji": float(override_gaji)
                }
                
                try:
                    supabase.table("LogHarian").insert(payload_absensi).execute()
                    st.success(f"✅ Gaji Rp {override_gaji:,.0f} untuk {pilih_nama_absen} ({divisi}) berhasil disimpan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")

# ----------------------------------------------------          
# MENU 3: KASBON KARYAWAN
# ----------------------------------------------------
elif menu == "3. Kasbon Karyawan":
    st.subheader("💵 Pencatatan Kasbon / Pinjaman Karyawan")
    
    karyawan_data = get_karyawan_list()
    list_karyawan_aktif = [k["nama_karyawan"] for k in karyawan_data if k.get("status", "Aktif") == "Aktif"]
    
    if not list_karyawan_aktif:
        st.warning("⚠️ Belum ada data karyawan aktif.")
    else:
        col_ks1, col_ks2 = st.columns([1, 1])
        
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
# MENU 4: MASTER KARYAWAN 
# ----------------------------------------------------
elif menu == "Master Karyawan":
    st.subheader("👥 Kelola Master Data Karyawan")

    tab_tambah, tab_lihat = st.tabs(["➕ Tambah Karyawan Baru", "📋 Daftar & Edit Karyawan"])

    # ----------------------------------------------------
    # TAB 1: TAMBAH KARYAWAN BARU
    # ----------------------------------------------------
    with tab_tambah:
        st.markdown("##### Mendaftarkan Karyawan Baru")
        
        with st.form("form_tambah_karyawan_safe", clear_on_submit=True):
            nama = st.text_input("Nama Lengkap Karyawan").strip()
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                list_divisi = [
                    "ABK Kandang",
                    "Produksi Brondong", 
                    "Produksi Snack", 
                    "Admin Pabrik", 
                    "Packing Online",
                    "Pembungkus / Borongan"
                ]
                divisi = st.selectbox("Divisi / Penempatan", list_divisi, key="sb_divisi_add")
                
            with col_d2:
                jabatan = st.selectbox("Jabatan", ["Anggota", "Kepala Regu", "Admin", "Lainnya"], key="sb_jabatan_add")

            btn_simpan_karyawan = st.form_submit_button("💾 Simpan Karyawan Baru", type="primary")

            if btn_simpan_karyawan:
                if not nama:
                    st.warning("⚠️ Nama karyawan wajib diisi!")
                else:
                    payload = {
                        "nama_karyawan": nama.title(),
                        "divisi": divisi,
                        "jabatan": jabatan
                    }
                    try:
                        # Menggunakan nama tabel MasterKaryawan sesuai skema database Anda
                        supabase.table("MasterKaryawan").insert(payload).execute()
                        st.success(f"✅ Karyawan **{nama.title()}** ({divisi}) berhasil didaftarkan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data ke Supabase: {e}")

    # ----------------------------------------------------
    # TAB 2: DAFTAR & HAPUS KARYAWAN
    # ----------------------------------------------------
    with tab_lihat:
        st.markdown("##### Daftar Karyawan Terdaftar")
        
        # Mengambil data menggunakan fungsi bawaan get_karyawan_list()
        karyawan_list = get_karyawan_list()

        if karyawan_list:
            df_karyawan = pd.DataFrame(karyawan_list)
            
            # Filter kolom yang akan ditampilkan
            cols_to_display = [c for c in ["id", "nama_karyawan", "divisi", "jabatan"] if c in df_karyawan.columns]
            
            st.dataframe(
                df_karyawan[cols_to_display] if cols_to_display else df_karyawan,
                column_config={
                    "id": "ID",
                    "nama_karyawan": "Nama Karyawan",
                    "divisi": "Divisi / Penempatan",
                    "jabatan": "Jabatan"
                },
                use_container_width=True
            )
            
            # Form Hapus Karyawan
            st.divider()
            with st.expander("🗑️ Hapus Data Karyawan"):
                dict_hapus = {
                    f"{k.get('nama_karyawan', 'Tanpa Nama')} ({k.get('divisi', '-')})": k.get("id") 
                    for k in karyawan_list if k.get("id")
                }
                
                if dict_hapus:
                    nama_hapus = st.selectbox("Pilih Karyawan yang Akan Dihapus", list(dict_hapus.keys()), key="sb_hapus_karyawan")
                    
                    if st.button("Hapus Permanen", type="secondary", key="btn_hapus_karyawan"):
                        id_hapus = dict_hapus[nama_hapus]
                        try:
                            supabase.table("MasterKaryawan").delete().eq("id", id_hapus).execute()
                            st.success(f"✅ Data karyawan berhasil dihapus.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus data dari Supabase: {e}")
                else:
                    st.write("Tidak ada data karyawan yang valid untuk dihapus.")
        else:
            st.info("ℹ️ Belum ada data karyawan terdaftar di database.")
# ----------------------------------------------------
# MENU 5: DATA & EDIT LOG
# ----------------------------------------------------
elif menu == "5. Data & Edit Log":
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
                st.success(f"Data ID {id_hapus} dihapus!")
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
                    
                    idx_prod = DAFTAR_PRODUK.index(curr.get("jenis_produk")) if curr.get("jenis_produk") in DAFTAR_PRODUK else 0
                    edit_produk = st.selectbox("Jenis Produk / Keterangan", DAFTAR_PRODUK, index=idx_prod)
                    
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
# MENU 6: REKAP & EKSPOR EXCEL (WITH GAJI POKOK BORONGAN SNACK)
# ----------------------------------------------------
elif menu == "6. Rekap & Ekspor Excel":
    st.subheader("📊 Rekapitulasi Gaji & Laporan Produksi Pabrik Bulanan")
    
    col_b, col_t = st.columns(2)
    with col_b:
        bulan = st.selectbox("Pilih Bulan", range(1, 13), index=datetime.today().month - 1)
    with col_t:
        tahun = st.number_input("Pilih Tahun", value=datetime.today().year, step=1)
        
    # Hitung Hari Kerja Efektif Pabrik pada Bulan & Tahun Terpilih
    hari_kerja_efektif = get_hari_kerja_efektif(tahun, bulan)
    st.info(f"📅 Total Hari Kerja Efektif Bulan {bulan}/{tahun}: **{hari_kerja_efektif} Hari Kerja**")

    res = supabase.table("LogHarian").select("*").execute()
    res_kasbon = supabase.table("Kasbon").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        df_filtered = df[(df["tanggal"].dt.month == bulan) & (df["tanggal"].dt.year == tahun)]
        
        if res_kasbon.data:
            df_k = pd.DataFrame(res_kasbon.data)
            df_k["tanggal"] = pd.to_datetime(df_k["tanggal"])
            df_k_filtered = df_k[(df_k["tanggal"].dt.month == bulan) & (df_k["tanggal"].dt.year == tahun)]
        else:
            df_k_filtered = pd.DataFrame(columns=["nama_karyawan", "nominal"])
        
        if not df_filtered.empty:
            st.divider()
            
            tab_gaji, tab_prod = st.tabs(["💵 Rekap Gaji Karyawan", "📦 Rekap Produksi Barang (Harian & Bulanan)"])
            
            # ----------------------------------------------------
            # TAB 1: REKAP GAJI + GAJI POKOK SNACK + BONUS KEHADIRAN
            # ----------------------------------------------------
            with tab_gaji:
                st.markdown("### 👥 Rekapitulasi Gaji Karyawan")
                
                # Cek apakah ada pengerjaan Brondong pada log karyawan
                def cek_is_brondong(group):
                    produk_list = group["jenis_produk"].astype(str).tolist()
                    return any("Brondong" in p for p in produk_list)

                # Grouping awal
                rekap_gaji = df_filtered.groupby(["nama_karyawan", "sistem_gaji"]).agg(
                    total_absensi=('tanggal', 'nunique'),
                    total_hasil=('jumlah_borongan', 'sum'),
                    gaji_borongan=('total_gaji', 'sum')
                ).reset_index()

                # Tambahkan flag apakah borongan brondong
                list_is_brondong = []
                for _, row in rekap_gaji.iterrows():
                    sub_df = df_filtered[df_filtered["nama_karyawan"] == row["nama_karyawan"]]
                    list_is_brondong.append(cek_is_brondong(sub_df))
                
                rekap_gaji["is_brondong"] = list_is_brondong

                # HITUNG GAJI POKOK HARIAN (Khusus Borongan Non-Brondong / Snack = Rp 10.000 / hari masuk)
                def hitung_gaji_pokok_harian(row):
                    if row["sistem_gaji"] == "Borongan" and not row["is_brondong"]:
                        return row["total_absensi"] * 10000
                    return 0

                # HITUNG BONUS KEHADIRAN
                def hitung_bonus_kehadiran(row):
                    masuk = row["total_absensi"]
                    target_hk = hari_kerja_efektif
                    if masuk >= target_hk:
                        return 100000
                    elif masuk == target_hk - 1:
                        return 30000
                    else:
                        return 0

                rekap_gaji["gaji_pokok_snack"] = rekap_gaji.apply(hitung_gaji_pokok_harian, axis=1)
                rekap_gaji["bonus_kehadiran"] = rekap_gaji.apply(hitung_bonus_kehadiran, axis=1)
                
                # TOTAL GAJI KOTOR
                rekap_gaji["gaji_kotor"] = (
                    rekap_gaji["gaji_borongan"] + 
                    rekap_gaji["gaji_pokok_snack"] + 
                    rekap_gaji["bonus_kehadiran"]
                )
                
                # Penggabungan Kasbon
                if not df_k_filtered.empty:
                    rekap_bon = df_k_filtered.groupby("nama_karyawan")["nominal"].sum().reset_index()
                    rekap_bon.rename(columns={"nominal": "total_kasbon"}, inplace=True)
                    rekap_gaji = pd.merge(rekap_gaji, rekap_bon, on="nama_karyawan", how="left")
                else:
                    rekap_gaji["total_kasbon"] = 0
                    
                rekap_gaji["total_kasbon"] = rekap_gaji["total_kasbon"].fillna(0)
                rekap_gaji["gaji_bersih"] = rekap_gaji["gaji_kotor"] - rekap_gaji["total_kasbon"]
                
                # TAMPILAN TABEL DENGAN KOLOM GAJI POKOK SNACK
                st.dataframe(
                    rekap_gaji[[
                        "nama_karyawan", 
                        "sistem_gaji", 
                        "total_absensi", 
                        "total_hasil", 
                        "gaji_borongan", 
                        "gaji_pokok_snack",
                        "bonus_kehadiran", 
                        "gaji_kotor", 
                        "total_kasbon", 
                        "gaji_bersih"
                    ]],
                    column_config={
                        "nama_karyawan": "Nama Karyawan",
                        "sistem_gaji": "Sistem Gaji",
                        "total_absensi": "Hari Masuk",
                        "total_hasil": "Total Hasil/Ball",
                        "gaji_borongan": st.column_config.NumberColumn("Hasil Borongan", format="Rp %d"),
                        "gaji_pokok_snack": st.column_config.NumberColumn("GP Snack (10rb/Hr)", format="Rp %d"),
                        "bonus_kehadiran": st.column_config.NumberColumn("Bonus Kehadiran", format="Rp %d"),
                        "gaji_kotor": st.column_config.NumberColumn("Gaji Kotor Total", format="Rp %d"),
                        "total_kasbon": st.column_config.NumberColumn("Kasbon", format="Rp %d"),
                        "gaji_bersih": st.column_config.NumberColumn("Gaji Bersih", format="Rp %d")
                    },
                    use_container_width=True
                )

            # TAB 2: REKAP PRODUKSI
            with tab_prod:
                st.markdown("### 📦 Rekap Rincian Hasil Produksi per Barang")
                df_prod = df_filtered[df_filtered["sistem_gaji"] == "Borongan"].copy()
                
                if not df_prod.empty:
                    df_prod["tgl_angka"] = df_prod["tanggal"].dt.day
                    pivot_produksi = pd.pivot_table(
                        df_prod,
                        values="jumlah_borongan",
                        index=["jenis_produk", "ukuran_bal"],
                        columns="tgl_angka",
                        aggfunc="sum",
                        fill_value=0
                    )
                    pivot_produksi["TOTAL BULAN INI (BAL)"] = pivot_produksi.sum(axis=1)
                    pivot_produksi = pivot_produksi.sort_values(by="TOTAL BULAN INI (BAL)", ascending=False).reset_index()
                    st.dataframe(pivot_produksi, use_container_width=True)
                else:
                    st.info("Belum ada data pengerjaan borongan produk pada bulan ini.")
                    pivot_produksi = pd.DataFrame()

            # EKSPOR KE EXCEL
            st.divider()
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                rekap_gaji.to_excel(writer, sheet_name='Rekap Gaji Karyawan', index=False)
                if not pivot_produksi.empty:
                    pivot_produksi.to_excel(writer, sheet_name='Rekap Produksi Harian', index=False)
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
# MENU 7: CETAK STRUK TERMAL
# ----------------------------------------------------
elif menu == "7. Cetak Struk Termal":
    st.subheader("🖨️ Cetak Struk Rekap Gaji Bulanan (58mm)")

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
        
        if res_kasbon.data:
            df_k = pd.DataFrame(res_kasbon.data)
            df_k["tanggal"] = pd.to_datetime(df_k["tanggal"])
            df_k_filtered = df_k[(df_k["tanggal"].dt.month == bulan) & (df_k["tanggal"].dt.year == tahun)]
        else:
            df_k_filtered = pd.DataFrame(columns=["nama_karyawan", "nominal"])
        
        if not df_filtered.empty:
            daftar_karyawan = df_filtered["nama_karyawan"].unique()
            pilih_karyawan = st.selectbox("Pilih Nama Karyawan", daftar_karyawan)
            
            df_karyawan = df_filtered[df_filtered["nama_karyawan"] == pilih_karyawan]
            sistem_gaji = df_karyawan["sistem_gaji"].iloc[0]
            total_qty = df_karyawan["jumlah_borongan"].sum()
            gaji_borongan = df_karyawan["total_gaji"].sum()
            total_hari_kerja = df_karyawan["tanggal"].nunique()
            
            # Cek jenis produk yang dikerjakan
            is_brondong = any("Brondong" in str(p) for p in df_karyawan["jenis_produk"].tolist())

            # Hitung Gaji Pokok Snack (10rb/hari)
            if sistem_gaji == "Borongan" and not is_brondong:
                gp_snack = total_hari_kerja * 10000
            else:
                gp_snack = 0

            # Hitung Kasbon Karyawan
            if not df_k_filtered.empty:
                total_kasbon = df_k_filtered[df_k_filtered["nama_karyawan"] == pilih_karyawan]["nominal"].sum()
            else:
                total_kasbon = 0

            # Hitung Bonus Kehadiran
            target_hk = get_hari_kerja_efektif(tahun, bulan)
            if total_hari_kerja >= target_hk:
                bonus_absen = 100000
            elif total_hari_kerja == target_hk - 1:
                bonus_absen = 30000
            else:
                bonus_absen = 0

            # Total Gaji Kotor & Bersih
            gaji_kotor_total = gaji_borongan + gp_snack + bonus_absen
            gaji_bersih = gaji_kotor_total - total_kasbon
            
            nama_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                          "Juli", "Agustus", "September", "Oktober", "November", "Desember"][bulan - 1]
            
            val_hasil = f"{total_qty:g} Ball" if sistem_gaji == "Borongan" else f"{total_hari_kerja} Hari"

            # TAMPILAN STRUK TERMAL HTML
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
                Nama    : {pilih_karyawan}<br>
                Sistem  : {sistem_gaji}<br>
                Absensi : {total_hari_kerja}/{target_hk} Hari Masuk<br>
                Hasil   : {val_hasil}<br>
                --------------------------------<br>
                Hasil Borongan : Rp {gaji_borongan:,.0f}<br>
                GP Snack (10k) : Rp {gp_snack:,.0f}<br>
                Bonus Absen    : Rp {bonus_absen:,.0f}<br>
                --------------------------------<br>
                Total Kotor    : Rp {gaji_kotor_total:,.0f}<br>
                Kasbon/Bon     : Rp {total_kasbon:,.0f}<br>
                --------------------------------<br>
                <strong>GAJI BERSIH   : Rp {gaji_bersih:,.0f}</strong><br>
                --------------------------------<br>
                <center>
                    <i>~ Slip Gaji bersifat rahasia,
                    apabila ada pertanyaan bisa hubungi Admin~</i>
                </center>
            </div>
            """
            st.markdown(struk_html, unsafe_allow_html=True)
            st.caption("Cetak slip menggunakan printer bluetooth 58mm.")
        else:
            st.warning("Tidak ada transaksi pada bulan & tahun ini.")
        
