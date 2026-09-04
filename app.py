import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import calendar
import io

# ==========================================
# KONSTANTA GAJI STANDAR BBS FOOD
# ==========================================
GAJI_BULANAN_KEPALA_REGU = 2500000      # Gaji acuan Kepala Regu Bulanan
GAJI_BULANAN_ANGGOTA = 2377000          # Gaji acuan Anggota Bulanan (Pemasak Brondong & Snack)
GAJI_BULANAN_PACKING_ONLINE = 2000000   # Gaji acuan Packing Online Bulanan
GAJI_HARIAN_TETAP_ADMIN = 100000        # Gaji flat Admin Pabrik per hari

# ====================================================
# FUNGSI BANTUAN HARI KERJA KHUSUS ABK KANDANG (LIBUR 2 HARI / BULAN)
# ====================================================
def get_hari_kerja_abk(tahun, bulan):
    """Menghitung hari kerja ABK Kandang (Total hari dalam bulan - 2 hari libur)."""
    total_hari_bulan = calendar.monthrange(tahun, bulan)[1]
    return max(total_hari_bulan - 2, 1)
    
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
    return total_hari - jumlah_minggu

def get_hari_kerja_abk(tahun, bulan):
    """
    Menghitung hari kerja ABK Kandang (Total hari dalam 1 bulan DIKURANGI 2 Hari Libur).
    """
    total_hari = calendar.monthrange(tahun, bulan)[1]
    return total_hari - 2

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
    "Emping Pedas Manis", "Mie Enak", "K. Jablay", "Brondong","Kedelai Mesin"
]
UKURAN_BAL = ["Isi 10", "Isi 12"]

# Acuan UMR Sragen Bulanan & Fungsi Hari Kerja Efektif (Senin-Sabtu)
GAJI_BULANAN_KEPALA_REGU = 2500000
GAJI_BULANAN_ANGGOTA = 2377000

def get_hari_kerja_efektif(tahun, bulan):
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
    "Kasbon Karyawan",
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
                    # Otomatis tentukan tarif: Brondong = 4500, Lainnya = 4000
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
                    
# ====================================================
# MENU 2: PRESENSI HARIAN & NON-BORONGAN 
# ====================================================
if menu == "Presensi Harian Non-Borongan" or menu == "Presensi Harian & Non-Borongan":
    st.subheader("⏱️ Input Presensi Harian & Non-Borongan")
    
    # 1. TANGGAL KERJA DILUAR FORM
    tgl_presensi = st.date_input("Tanggal Kerja", value=datetime.today(), key="harian_tgl")
    thn = tgl_presensi.year
    bln = tgl_presensi.month
    
    # 2. HITUNG HARI KERJA EFEKTIF
    hari_kerja_pabrik = get_hari_kerja_efektif(thn, bln)
    hari_kerja_abk = get_hari_kerja_abk(thn, bln)

    st.caption(
        f"📅 **Akses Bulan {bln}/{thn}:** "
        f"Pabrik = **{hari_kerja_pabrik} Hari Kerja** (Libur Minggu) | "
        f"ABK Kandang = **{hari_kerja_abk} Hari Kerja** (Libur 2x)"
    )

    karyawan_data = get_karyawan_list()
    
    # FILTER KARYAWAN UNTUK PRESENSI HARIAN:
    harian_karyawan = []
    for k in karyawan_data:
        status_k = str(k.get("status") or k.get("status_karyawan") or "Aktif").strip().capitalize()
        if status_k != "Aktif":
            continue
            
        div = str(k.get("divisi", "") or "").lower().strip()
        sub_div = str(k.get("sub_divisi", "") or k.get("jenis_produk", "") or "").lower().strip()
        
        if "pembungkus" in div or "borongan" in div:
            if "snack" in sub_div or "snack" in div:
                harian_karyawan.append(k)
        else:
            harian_karyawan.append(k)

    if not harian_karyawan:
        st.warning("⚠️ Belum ada data karyawan harian aktif.")
    else:
        with st.form("form_presensi_harian", clear_on_submit=True):
            col_p1, col_p2 = st.columns(2)
            
            with col_p1:
                pilihan_karyawan = st.selectbox(
                    "Pilih Karyawan", 
                    options=harian_karyawan, 
                    format_func=lambda x: f"{x.get('nama_karyawan', '-')} — {x.get('divisi', '-')} ({x.get('jabatan') or x.get('jabatan_karyawan') or 'Anggota'})"
                )
                
                # Normalisasi string & ekstraksi kolom dinamis Supabase
                nama_karyawan = str(pilihan_karyawan.get('nama_karyawan', '') or '').strip()
                divisi_raw = str(pilihan_karyawan.get('divisi', '') or '').strip()
                
                # Ambil jabatan dari kolom 'jabatan' atau 'jabatan_karyawan'
                jabatan_raw = str(
                    pilihan_karyawan.get('jabatan') or 
                    pilihan_karyawan.get('jabatan_karyawan') or 
                    'Anggota'
                ).strip()

                nama_lower = nama_karyawan.lower()
                divisi_lower = divisi_raw.lower()
                jabatan_lower = jabatan_raw.lower()

                # PENGECEKAN KEPALA REGU / SPV YANG SANGAT PRESISI
                # Hanya bernilai True jika secara eksplisit mengandung "kepala" atau "spv"
                is_kepala_regu = ("kepala" in jabatan_lower or "spv" in jabatan_lower or "leader" in jabatan_lower)

                # ----------------------------------------------------
                # PENENTUAN TARIF HARIAN BERDASARKAN DIVISI & JABATAN
                # ----------------------------------------------------
                
                # A. ABK KANDANG
                if "abk" in divisi_lower or "kandang" in divisi_lower:
                    gaji_std_default = GAJI_BULANAN_ANGGOTA / hari_kerja_abk
                    st.info(
                        f"**Tipe:** ABK Kandang ({nama_karyawan})\n\n"
                        f"📅 **Hari Kerja Bulan Ini:** {hari_kerja_abk} Hari\n"
                        f"📌 **Tarif Harian:** Rp {GAJI_BULANAN_ANGGOTA:,.0f} / {hari_kerja_abk} Hari = **Rp {gaji_std_default:,.0f}/hari**"
                    )

                # B. ADMIN PABRIK
                elif "admin" in divisi_lower:
                    gaji_std_default = GAJI_HARIAN_TETAP_ADMIN
                    st.info(f"**Tipe:** Admin Pabrik ({nama_karyawan}) - Flat Harian Rp {gaji_std_default:,.0f}")

                # C. PACKING ONLINE
                elif "packing" in divisi_lower or "online" in divisi_lower:
                    gaji_std_default = GAJI_BULANAN_PACKING_ONLINE / hari_kerja_pabrik
                    st.info(f"**Tipe:** Packing Online ({nama_karyawan})\n\n📌 **Tarif Harian:** Rp {GAJI_BULANAN_PACKING_ONLINE:,.0f} / {hari_kerja_pabrik} Hari = **Rp {gaji_std_default:,.0f}/hari**")

                # D. BUNGKUS SNACK
                elif "pembungkus" in divisi_lower or ("snack" in divisi_lower and "produksi" not in divisi_lower and "pemasak" not in divisi_lower):
                    gaji_pokok_bulanan = GAJI_BULANAN_KEPALA_REGU if is_kepala_regu else GAJI_BULANAN_ANGGOTA
                    gaji_std_default = gaji_pokok_bulanan / hari_kerja_pabrik
                    label_jabatan = "Kepala Regu / SPV" if is_kepala_regu else "Anggota"
                    st.info(
                        f"**Tipe:** Bungkus Snack - **{label_jabatan}** ({nama_karyawan})\n\n"
                        f"📌 **Flat Harian:** Rp {gaji_std_default:,.0f} / hari "
                        f"(Acuan Rp {gaji_pokok_bulanan:,.0f} / {hari_kerja_pabrik} Hari Kerja)"
                    )

                # E. PRODUKSI BRONDONG (EKSPLISIT CEK 'BRONDONG')
                elif "brondong" in divisi_lower:
                    gaji_pokok_bulanan = GAJI_BULANAN_KEPALA_REGU if is_kepala_regu else GAJI_BULANAN_ANGGOTA
                    gaji_std_default = gaji_pokok_bulanan / hari_kerja_pabrik
                    label_jabatan = "Kepala Regu / SPV" if is_kepala_regu else "Anggota"
                    st.info(
                        f"**Tipe:** Pemasak Brondong - **{label_jabatan}** ({nama_karyawan})\n\n"
                        f"🎯 **Gaji Acuan 100% (50 Bal):** Rp {gaji_std_default:,.0f} "
                        f"(Acuan Rp {gaji_pokok_bulanan:,.0f} / {hari_kerja_pabrik} Hari Kerja)"
                    )

                # F. PRODUKSI SNACK / PEMASAK SNACK (EKSPLISIT CEK 'SNACK')
                elif "snack" in divisi_lower:
                    gaji_pokok_bulanan = GAJI_BULANAN_KEPALA_REGU if is_kepala_regu else GAJI_BULANAN_ANGGOTA
                    gaji_std_default = gaji_pokok_bulanan / hari_kerja_pabrik
                    label_jabatan = "Kepala Regu / SPV" if is_kepala_regu else "Anggota"
                    st.info(
                        f"**Tipe:** Pemasak Snack - **{label_jabatan}** ({nama_karyawan})\n\n"
                        f"📌 **Flat Harian:** Rp {gaji_std_default:,.0f} / hari "
                        f"(Acuan Rp {gaji_pokok_bulanan:,.0f} / {hari_kerja_pabrik} Hari Kerja)"
                    )

                # G. FALLBACK UMUM
                else:
                    gaji_pokok_bulanan = GAJI_BULANAN_KEPALA_REGU if is_kepala_regu else GAJI_BULANAN_ANGGOTA
                    gaji_std_default = gaji_pokok_bulanan / hari_kerja_pabrik
                    label_jabatan = "Kepala Regu / SPV" if is_kepala_regu else "Anggota"
                    st.info(
                        f"**Tipe:** Produksi/Umum ({divisi_raw}) - **{label_jabatan}** ({nama_karyawan})\n\n"
                        f"📌 **Tarif Harian:** Rp {gaji_std_default:,.0f} / hari"
                    )

            with col_p2:
                # Hanya Produksi Brondong yang memiliki skema target bal
                if "brondong" in divisi_lower:
                    target_bal = 50
                    st.markdown("##### 🎯 Target & Perhitungan Brondong")
                    hasil_bal = st.number_input("Total Hasil Brondong Hari Ini (Bal)", min_value=0, value=50, step=1)
                    
                    if is_kepala_regu:
                        st.caption("ℹ️ **Kepala Regu:** Menerima gaji utuh harian tanpa potongan target.")
                    else:
                        st.caption(f"🎯 **Target Standard Anggota:** {target_bal} Bal/Hari")
                        rasio = hasil_bal / target_bal
                        gaji_estimasi = gaji_std_default * rasio
                        
                        if hasil_bal < target_bal:
                            potongan = gaji_std_default - gaji_estimasi
                            st.warning(f"⚠️ **Kurang Target:** Dipotong Rp {potongan:,.0f} ({hasil_bal}/{target_bal} Bal)")
                        elif hasil_bal > target_bal:
                            bonus = gaji_estimasi - gaji_std_default
                            st.success(f"🔥 **Bonus Target:** +Rp {bonus:,.0f} ({hasil_bal}/{target_bal} Bal)")
                        else:
                            st.info("✅ Target pas (50 Bal) -> Gaji utuh 100%.")

                else:
                    hasil_bal = 1.0
                    st.success(f"✅ **Gaji Harian Diterima:** Rp {gaji_std_default:,.0f}")

            btn_simpan_harian = st.form_submit_button("💾 Hitung & Simpan Presensi", type="primary")

            if btn_simpan_harian:
                if "brondong" in divisi_lower:
                    if is_kepala_regu:
                        gaji_akhir = gaji_std_default
                        catatan = "Kepala Regu Brondong (Gaji Utuh)."
                    else:
                        target_bal = 50
                        rasio = hasil_bal / target_bal
                        gaji_akhir = gaji_std_default * rasio
                        
                        if hasil_bal == target_bal:
                            catatan = f"Target pas ({hasil_bal} Bal). Gaji 100%."
                        elif hasil_bal < target_bal:
                            potongan = gaji_std_default - gaji_akhir
                            catatan = f"Kurang target ({hasil_bal}/50 Bal). Dipotong Rp {potongan:,.0f}."
                        else:
                            bonus = gaji_akhir - gaji_std_default
                            catatan = f"Lebih target ({hasil_bal}/50 Bal). Bonus +Rp {bonus:,.0f}."

                elif "abk" in divisi_lower or "kandang" in divisi_lower:
                    gaji_akhir = gaji_std_default
                    catatan = f"Presensi ABK Kandang (1/{hari_kerja_abk} Hari Kerja)."

                elif "pembungkus" in divisi_lower:
                    gaji_akhir = gaji_std_default
                    catatan = f"Presensi Bungkus Snack Flat Harian (1/{hari_kerja_pabrik} Hari Kerja)."

                elif "snack" in divisi_lower:
                    gaji_akhir = gaji_std_default
                    catatan = f"Presensi Pemasak Snack Flat Harian (1/{hari_kerja_pabrik} Hari Kerja)."

                elif "admin" in divisi_lower:
                    gaji_akhir = GAJI_HARIAN_TETAP_ADMIN
                    catatan = "Presensi Admin Pabrik."

                else:
                    gaji_akhir = gaji_std_default
                    catatan = "Presensi Harian."

                payload = {
                    "tanggal": str(tgl_presensi),
                    "nama_karyawan": nama_karyawan,
                    "sistem_gaji": "Harian",
                    "jenis_produk": divisi_raw if divisi_raw else "Harian",
                    "ukuran_bal": "-",
                    "jumlah_borongan": float(hasil_bal),
                    "nominal_satuan": int(gaji_std_default),
                    "total_gaji": float(gaji_akhir)
                }
                
                try:
                    supabase.table("LogHarian").insert(payload).execute()
                    st.success(f"✅ Presensi {nama_karyawan} berhasil disimpan! Gaji Diterima: **Rp {gaji_akhir:,.0f}** ({catatan})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")
# ---------------------------------------------------              
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
# MENU 4: MASTER KARYAWAN
# ----------------------------------------------------
elif menu == "Master Karyawan":
    st.subheader("👥 Kelola Master Data Karyawan")
    
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        st.markdown("##### Tambah Karyawan Baru")
        with st.form("form_karyawan", clear_on_submit=True):
            nama_baru = st.text_input("Nama Karyawan")
            divisi_baru = st.selectbox("Divisi Kerja", ["Pembungkus / Borongan", "Produksi Brondong", "Produksi Snack"])
            jabatan_baru = st.selectbox("Jabatan", ["Anggota", "Kepala Regu"])
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
                        st.error("Gagal menambahkan. Pastikan struktur tabel Supabase sudah sesuai.")
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
                st.success("Karyawan dihapus!")
                st.rerun()
        else:
            st.info("Belum ada data karyawan.")

# ----------------------------------------------------
# MENU 5: DATA & EDIT LOG
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
                    edit_produk = st.selectbox("Jenis Produk", DAFTAR_PRODUK, index=idx_prod)
                    
                    edit_jumlah = st.number_input("Jumlah Ball / Hasil", value=float(curr.get("jumlah_borongan", 1.0)), step=0.5, format="%.1f")
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
# MENU 6: REKAP & EKSPOR EXCEL (DENGAN REKAP HARIAN PRODUK)
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
            
            # TAB 1 & 2 DIBAGI AGAR RAPI
            tab_gaji, tab_prod = st.tabs(["💵 Rekap Gaji Karyawan", "📦 Rekap Produksi Barang (Harian & Bulanan)"])
            
            # ----------------------------------------------------
            # TAB 1: REKAP GAJI
            # ----------------------------------------------------
            with tab_gaji:
                st.markdown("### 👥 Rekapitulasi Gaji Karyawan")
                rekap_gaji = df_filtered.groupby(["nama_karyawan", "sistem_gaji"]).agg(
                    total_absensi=('tanggal', 'nunique'),
                    total_hasil=('jumlah_borongan', 'sum'),
                    gaji_kotor=('total_gaji', 'sum')
                ).reset_index()
                
                if not df_k_filtered.empty:
                    rekap_bon = df_k_filtered.groupby("nama_karyawan")["nominal"].sum().reset_index()
                    rekap_bon.rename(columns={"nominal": "total_kasbon"}, inplace=True)
                    rekap_gaji = pd.merge(rekap_gaji, rekap_bon, on="nama_karyawan", how="left")
                else:
                    rekap_gaji["total_kasbon"] = 0
                    
                rekap_gaji["total_kasbon"] = rekap_gaji["total_kasbon"].fillna(0)
                rekap_gaji["gaji_bersih"] = rekap_gaji["gaji_kotor"] - rekap_gaji["total_kasbon"]
                
                st.dataframe(
                    rekap_gaji[["nama_karyawan", "sistem_gaji", "total_absensi", "total_hasil", "gaji_kotor", "total_kasbon", "gaji_bersih"]],
                    use_container_width=True
                )

            # ----------------------------------------------------
            # TAB 2: REKAP PRODUKSI HARIAN & BULANAN (MATRIX)
            # ----------------------------------------------------
            with tab_prod:
                st.markdown("### 📦 Rekap Rincian Hasil Produksi per Barang")
                
                # Filter khusus transaksi borongan/produk
                df_prod = df_filtered[df_filtered["sistem_gaji"] == "Borongan"].copy()
                
                if not df_prod.empty:
                    # Ambil angka tanggal (1, 2, 3... 31)
                    df_prod["tgl_angka"] = df_prod["tanggal"].dt.day
                    
                    # Buat Pivot Table: Baris = Jenis Produk & Ukuran, Kolom = Tanggal (1..31)
                    pivot_produksi = pd.pivot_table(
                        df_prod,
                        values="jumlah_borongan",
                        index=["jenis_produk", "ukuran_bal"],
                        columns="tgl_angka",
                        aggfunc="sum",
                        fill_value=0
                    )
                    
                    # Hitung Total Produksi 1 Bulan (Sum per Baris)
                    pivot_produksi["TOTAL BULAN INI (BAL)"] = pivot_produksi.sum(axis=1)
                    pivot_produksi = pivot_produksi.sort_values(by="TOTAL BULAN INI (BAL)", ascending=False).reset_index()
                    
                    # Tampilkan di Streamlit
                    st.dataframe(pivot_produksi, use_container_width=True)
                else:
                    st.info("Belum ada data pengerjaan borongan produk pada bulan ini.")
                    pivot_produksi = pd.DataFrame()

            # ----------------------------------------------------
            # EKSPOR KE EXCEL (TERMASUK SHEET REKAP PRODUKSI HARIAN)
            # ----------------------------------------------------
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
elif menu == "Cetak Struk Termal":
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
        
        # Filter Data Kasbon
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
            gaji_kotor = df_karyawan["total_gaji"].sum()
            total_hari_kerja = df_karyawan["tanggal"].nunique()
            
            # Hitung Kasbon Karyawan Terpilih
            if not df_k_filtered.empty:
                total_kasbon = df_k_filtered[df_k_filtered["nama_karyawan"] == pilih_karyawan]["nominal"].sum()
            else:
                total_kasbon = 0
                
            gaji_bersih = gaji_kotor - total_kasbon
            
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
                Hasil  : {total_qty:g} Ball/Hari<br>
                --------------------------------<br>
                Gaji Kotor   : Rp {gaji_kotor:,.0f}<br>
                Kasbon/Bon   : Rp {total_kasbon:,.0f}<br>
                --------------------------------<br>
                <strong>GAJI BERSIH  : Rp {gaji_bersih:,.0f}</strong><br>
                --------------------------------<br>
                <center>
                    <i>~ Terima Kasih ~</i>
                </center>
            </div>
            """
            st.markdown(struk_html, unsafe_allow_html=True)
            st.caption("Cetak slip menggunakan printer bluetooth 58mm.")
        else:
            st.warning("Tidak ada transaksi pada bulan & tahun ini.")
