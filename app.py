import streamlit as st
import pandas as pd
from datetime import date, datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gaji Karyawan BBS Food", layout="wide")
st.title("🧾 Aplikasi Rekap Gaji Karyawan BBS Food")

# Koneksi ke Google Sheets via st-gsheets-connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_log():
    try:
        df = conn.read(worksheet="LogHarian", ttl=0)
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=["Tanggal", "Nama", "Sistem Gaji", "Pekerjaan", "Hasil (Ball/Unit)", "Upah/Unit (Rp)", "Hadir (Hari)", "Upah Harian (Rp)", "Subtotal (Rp)"])
        return df
    except Exception:
        return pd.DataFrame(columns=["Tanggal", "Nama", "Sistem Gaji", "Pekerjaan", "Hasil (Ball/Unit)", "Upah/Unit (Rp)", "Hadir (Hari)", "Upah Harian (Rp)", "Subtotal (Rp)"])

def get_data_adj():
    try:
        df = conn.read(worksheet="Penyesuaian", ttl=0)
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=["Nama", "Bonus (Rp)", "Potongan (Rp)"])
        return df
    except Exception:
        return pd.DataFrame(columns=["Nama", "Bonus (Rp)", "Potongan (Rp)"])

df_log = get_data_log()
df_adj = get_data_adj()

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
    new_row = pd.DataFrame([{
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
    updated_df = pd.concat([df_log, new_row], ignore_index=True)
    conn.update(worksheet="LogHarian", data=updated_df)
    st.success(f"Catatan {nama} berhasil tersimpan ke Google Sheets!")
    st.rerun()

# TAB NAVIGATION
tab1, tab2, tab3 = st.tabs(["📋 Logs Harian & Kelola Data", "⚙️ Bonus & Potongan", "🧾 Cetak Struk 58mm"])

# TAB 1: LOG HARIAN, EDIT, & HAPUS
with tab1:
    st.subheader("📌 Log Catatan Kerja Harian")
    
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True)
        st.divider()
        st.subheader("🛠️ Edit atau Hapus Data Log")
        
        list_opsi = [f"Baris {idx + 1} | {row['Tanggal']} - {row['Nama']} ({row['Pekerjaan']})" for idx, row in df_log.iterrows()]
        pilih_baris = st.selectbox("Pilih Baris Data yang Ingin Diubah/Dihapus:", range(len(list_opsi)), format_func=lambda x: list_opsi[x])
        row_terpilih = df_log.iloc[pilih_baris]
        
        col_edit, col_hapus = st.columns([2, 1])
        
        with col_edit:
            with st.expander("✏️ Edit Data Baris Terpilih", expanded=False):
                with st.form("form_edit"):
                    edit_tgl = st.date_input("Tanggal", datetime.strptime(str(row_terpilih["Tanggal"]), "%Y-%m-%d"))
                    edit_nama = st.text_input("Nama Karyawan", value=row_terpilih["Nama"])
                    edit_sistem = st.selectbox("Sistem Kerja", ["Borongan (per Ball/Unit)", "Harian (per Hari Masuk)"], index=0 if "Borongan" in str(row_terpilih["Sistem Gaji"]) else 1)
                    edit_pekerjaan = st.text_input("Jenis Pekerjaan", value=row_terpilih["Pekerjaan"])
                    
                    if edit_sistem == "Borongan (per Ball/Unit)":
                        edit_hasil = st.number_input("Hasil (Ball/Unit)", min_value=0.0, value=float(row_terpilih["Hasil (Ball/Unit)"]), step=0.5)
                        edit_upah_unit = st.number_input("Upah/Unit (Rp)", min_value=0, value=int(row_terpilih["Upah/Unit (Rp)"]), step=100)
                        edit_hadir = 0
                        edit_upah_harian = 0
                        edit_subtotal = edit_hasil * edit_upah_unit
                    else:
                        edit_hasil = 0.0
                        edit_upah_unit = 0
                        edit_hadir = st.number_input("Hadir (Hari)", min_value=0, value=int(row_terpilih["Hadir (Hari)"]), step=1)
                        edit_upah_harian = st.number_input("Upah Harian (Rp)", min_value=0, value=int(row_terpilih["Upah Harian (Rp)"]), step=1000)
                        edit_subtotal = edit_hadir * edit_upah_harian
                    
                    simpan_edit = st.form_submit_button("💾 Update Data")
                    
                    if simpan_edit:
                        df_log.at[pilih_baris, "Tanggal"] = edit_tgl.strftime("%Y-%m-%d")
                        df_log.at[pilih_baris, "Nama"] = edit_nama.strip()
                        df_log.at[pilih_baris, "Sistem Gaji"] = edit_sistem
                        df_log.at[pilih_baris, "Pekerjaan"] = edit_pekerjaan
                        df_log.at[pilih_baris, "Hasil (Ball/Unit)"] = edit_hasil
                        df_log.at[pilih_baris, "Upah/Unit (Rp)"] = edit_upah_unit
                        df_log.at[pilih_baris, "Hadir (Hari)"] = edit_hadir
                        df_log.at[pilih_baris, "Upah Harian (Rp)"] = edit_upah_harian
                        df_log.at[pilih_baris, "Subtotal (Rp)"] = edit_subtotal
                        conn.update(worksheet="LogHarian", data=df_log)
                        st.success("Data berhasil diperbarui di Google Sheets!")
                        st.rerun()

        with col_hapus:
            st.write("🗑️ **Hapus Data Baris**")
            if st.button("❌ Hapus Baris Terpilih", type="primary"):
                df_log = df_log.drop(pilih_baris).reset_index(drop=True)
                conn.update(worksheet="LogHarian", data=df_log)
                st.success("Baris berhasil dihapus!")
                st.rerun()
    else:
        st.info("Belum ada catatan harian di Google Sheets.")

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
            df_adj_clean = df_adj[df_adj["Nama"] != pilih_karyawan]
            new_adj = pd.DataFrame([{"Nama": pilih_karyawan, "Bonus (Rp)": input_bonus, "Potongan (Rp)": input_potongan}])
            updated_adj = pd.concat([df_adj_clean, new_adj], ignore_index=True)
            conn.update(worksheet="Penyesuaian", data=updated_adj)
            st.success(f"Bonus & Potongan {pilih_karyawan} tersimpan!")
            st.rerun()
            
        st.divider()
        st.write("Daftar Bonus & Potongan Terpasang:")
        st.dataframe(df_adj, use_container_width=True)

# TAB 3: CETAK STRUK THERMAL 58MM
with tab3:
    st.subheader("🧾 Cetak Struk Thermal 58mm")
    if not df_log.empty:
        karyawan_pilihan = st.selectbox("Pilih Karyawan untuk Cetak Struk:", df_log["Nama"].unique())
        logs_karyawan = df_log[df_log["Nama"] == karyawan_pilihan]
        
        adj_karyawan = df_adj[df_adj["Nama"] == karyawan_pilihan]
        bonus_val = int(adj_karyawan["Bonus (Rp)"].values[0]) if not adj_karyawan.empty else 0
        potongan_val = int(adj_karyawan["Potongan (Rp)"].values[0]) if not adj_karyawan.empty else 0
        
        subtotal_gaji = int(logs_karyawan["Subtotal (Rp)"].sum())
        total_gaji = subtotal_gaji + bonus_val - potongan_val
        sistem_kerja = logs_karyawan["Sistem Gaji"].iloc[0]
        
        rincian_html = ""
        for _, row in logs_karyawan.iterrows():
            if "Borongan" in str(row["Sistem Gaji"]):
                rincian_html += f"<div>{row['Tanggal']}: {row['Hasil (Ball/Unit)']} Ball x {int(row['Upah/Unit (Rp)']):,} = {int(row['Subtotal (Rp)']):,}</div>"
            else:
                rincian_html += f"<div>{row['Tanggal']}: {row['Hadir (Hari)']} Hari x {int(row['Upah Harian (Rp)']):,} = {int(row['Subtotal (Rp)']):,}</div>"
                
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
