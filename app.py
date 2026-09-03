import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Gaji Karyawan BBS Food", layout="wide")
st.title("🧾 Aplikasi Rekap Gaji Karyawan BBS Food")

# Inisialisasi Storage Data di Session State
if "data_absensi" not in st.session_state:
    st.session_state.data_absensi = pd.DataFrame(
        columns=["Tanggal", "Nama", "Sistem Gaji", "Pekerjaan", "Hasil (Ball/Unit)", "Upah/Unit (Rp)", "Hadir (Hari)", "Upah Harian (Rp)", "Subtotal (Rp)"]
    )

if "data_penyesuaian" not in st.session_state:
    st.session_state.data_penyesuaian = pd.DataFrame(
        columns=["Nama", "Bonus (Rp)", "Potongan (Rp)"]
    )

# SIDEBAR: INPUT HASIL KERJA HARIAN
with st.sidebar:
    st.header("📝 Input Hasil Kerja Harian")
    tgl = st.date_input("Tanggal Kerja", date.today())
    nama = st.text_input("Nama Karyawan", placeholder="Misal: Sri / Eka")
    sistem = st.selectbox("Sistem Kerja", ["Borongan (per Ball/Unit)", "Harian (per Hari Masuk)"])
    pekerjaan = st.text_input("Jenis Pekerjaan", placeholder="Misal: Pengemasan / Bulking")
    
    if sistem == "Borongan (per Ball/Unit)":
        hasil_ball = st.number_input("Jumlah Hasil (Ball/Unit)", min_value=0.0, value=0.0, step=0.5)
        upah_unit = st.number_input("Tarif Upah per Ball/Unit (Rp)", min_value=0, value=2000, step=100)
        hadir_hari = 0
        upah_harian = 0
        subtotal = hasil_ball * upah_unit
    else:
        hasil_ball = 0.0
        upah_unit = 0
        hadir_hari = st.number_input("Jumlah Kehadiran (Hari)", min_value=0, value=1, step=1)
        upah_harian = st.number_input("Tarif Upah Harian (Rp)", min_value=0, value=50000, step=1000)
        subtotal = hadir_hari * upah_harian
        
    submit_absensi = st.button("➕ Simpan Catatan Harian")

if submit_absensi and nama:
    new_entry = pd.DataFrame([{
        "Tanggal": tgl.strftime("%Y-%m-%d"),
        "Nama": nama.strip(),
        "Sistem Gaji": sistem,
        "Pekerjaan": pekerjaan,
        "Hasil (Ball/Unit)": hasil_ball,
        "Upah/Unit (Rp)": upah_unit,
        "Hadir (Hari)": hadir_hari,
        "Upah Harian (Rp)": upah_harian,
        "Subtotal (Rp)": subtotal
    }])
    st.session_state.data_absensi = pd.concat([st.session_state.data_absensi, new_entry], ignore_index=True)
    st.success(f"Catatan {nama} tanggal {tgl} berhasil disimpan!")

# TAB NAVIGATION
tab1, tab2, tab3 = st.tabs(["📋 Logs Harian & Rekap", "⚙️ Bonus & Potongan", "🧾 Cetak Struk 58mm"])

# TAB 1: LOG HARIAN & TOTAL
with tab1:
    st.subheader("📌 Log Catatan Kerja Harian")
    df_log = st.session_state.data_absensi
    
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True)
        if st.button("🗑️ Hapus Semua Log Harian"):
            st.session_state.data_absensi = pd.DataFrame(
                columns=["Tanggal", "Nama", "Sistem Gaji", "Pekerjaan", "Hasil (Ball/Unit)", "Upah/Unit (Rp)", "Hadir (Hari)", "Upah Harian (Rp)", "Subtotal (Rp)"]
            )
            st.rerun()
    else:
        st.info("Belum ada catatan harian. Masukkan data lewat menu di sebelah kiri.")

# TAB 2: BONUS & POTONGAN PER KARYAWAN
with tab2:
    st.subheader("⚙️ Atur Bonus & Potongan (Kasbon)")
    if not df_log.empty:
        daftar_nama = df_log["Nama"].unique()
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            pilih_karyawan = st.selectbox("Pilih Karyawan", daftar_nama)
        with col_p2:
            input_bonus = st.number_input("Bonus / Insentif (Rp)", min_value=0, value=0, step=1000)
        with col_p3:
            input_potongan = st.number_input("Potongan Kasbon/Dll (Rp)", min_value=0, value=0, step=1000)
            
        if st.button("💾 Simpan Bonus/Potongan"):
            df_adj = st.session_state.data_penyesuaian
            df_adj = df_adj[df_adj["Nama"] != pilih_karyawan]
            new_adj = pd.DataFrame([{"Nama": pilih_karyawan, "Bonus (Rp)": input_bonus, "Potongan (Rp)": input_potongan}])
            st.session_state.data_penyesuaian = pd.concat([df_adj, new_adj], ignore_index=True)
            st.success(f"Bonus & Potongan untuk {pilih_karyawan} diperbarui!")
            
        st.divider()
        st.write("Daftar Bonus & Potongan Terpasang:")
        st.dataframe(st.session_state.data_penyesuaian, use_container_width=True)
    else:
        st.info("Input data log harian terlebih dahulu.")

# TAB 3: CETAK STRUK THERMAL 58MM
with tab3:
    st.subheader("🧾 Cetak Struk Thermal 58mm")
    if not df_log.empty:
        karyawan_pilihan = st.selectbox("Pilih Karyawan untuk Cetak Struk:", df_log["Nama"].unique())
        
        # Filter Log Karyawan
        logs_karyawan = df_log[df_log["Nama"] == karyawan_pilihan]
        
        # Ambil Bonus/Potongan
        adj_karyawan = st.session_state.data_penyesuaian[st.session_state.data_penyesuaian["Nama"] == karyawan_pilihan]
        bonus_val = adj_karyawan["Bonus (Rp)"].values[0] if not adj_karyawan.empty else 0
        potongan_val = adj_karyawan["Potongan (Rp)"].values[0] if not adj_karyawan.empty else 0
        
        subtotal_gaji = logs_karyawan["Subtotal (Rp)"].sum()
        total_gaji = subtotal_gaji + bonus_val - potongan_val
        sistem_kerja = logs_karyawan["Sistem Gaji"].iloc[0]
        
        # Susun Rincian Tanggal untuk Thermal
        rincian_html = ""
        for _, row in logs_karyawan.iterrows():
            if "Borongan" in row["Sistem Gaji"]:
                rincian_html += f"<div>{row['Tanggal']}: {row['Hasil (Ball/Unit)']} Ball x {row['Upah/Unit (Rp)']:,} = {row['Subtotal (Rp)']:,}</div>"
            else:
                rincian_html += f"<div>{row['Tanggal']}: {row['Hadir (Hari)']} Hari x {row['Upah Harian (Rp)']:,} = {row['Subtotal (Rp)']:,}</div>"
                
        # Layout Struk Thermal 58mm (Simulasi Screen)
        st.markdown(
            f"""
            <div style="background:#ffffff; color:#000000; width:220px; padding:10px; font-family:monospace; font-size:10px; border:1px dashed #000; margin:auto;">
                <div style="text-align:center; font-weight:bold; font-size:13px;">BBS FOOD</div>
                <div style="text-align:center; font-size:10px;">SLIP GAJI KARYAWAN</div>
                <div style="border-bottom:1px dashed #000; margin:5px 0;"></div>
                <b>Nama:</b> {karyawan_pilihan}<br>
                <b>Sistem:</b> {sistem_kerja}<br>
                <div style="border-bottom:1px dashed #000; margin:5px 0;"></div>
                <b>RINCIAN HARIAN:</b><br>
                {rincian_html}
                <div style="border-bottom:1px dashed #000; margin:5px 0;"></div>
                <b>Subtotal:</b> Rp {subtotal_gaji:,}<br>
                <b>Bonus:</b> Rp {bonus_val:,}<br>
                <b>Potongan:</b> Rp {potongan_val:,}<br>
                <div style="border-bottom:1px dashed #000; margin:5px 0;"></div>
                <div style="font-size:11px; font-weight:bold;">TOTAL GAJI: Rp {total_gaji:,}</div>
                <div style="border-bottom:1px dashed #000; margin:5px 0;"></div>
                <div style="text-align:center; margin-top:8px;">*** Terima Kasih ***</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.caption("💡 Petunjuk Cetak: Blok/sorot tampilan struk di atas, klik kanan > Print (Ctrl+P), lalu pilih Printer Thermal 58mm Anda.")
    else:
        st.info("Belum ada data gaji yang bisa dicetak.")