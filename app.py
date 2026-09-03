import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Inisialisasi Koneksi ke Supabase
url: str = st.secrets["supabase"]["SUPABASE_URL"]
key: str = st.secrets["supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("Sistem Log Gaji Karyawan BBS Food")

# 2. Form Input Data
with st.form("form_log", clear_on_submit=True):
    st.subheader("Input Log Harian")
    tanggal = st.date_input("Tanggal")
    nama = st.text_input("Nama Karyawan")
    jumlah = st.number_input("Hasil Borongan", min_value=0, step=1)
    total = st.number_input("Total Gaji (Rp)", min_value=0, step=1000)
    
    submitted = st.form_submit_button("Simpan Data")
    
    if submitted:
        if not nama:
            st.error("Nama Karyawan wajib diisi!")
        else:
            # Data yang akan dikirim ke Supabase
            data_input = {
                "tanggal": str(tanggal),
                "nama_karyawan": nama,
                "jumlah_borongan": int(jumlah),
                "total_gaji": int(total)
            }
            
            # Eksekusi simpan data ke tabel LogHarian
            supabase.table("LogHarian").insert(data_input).execute()
            st.success(f"Data untuk {nama} berhasil disimpan!")

st.divider()

# 3. Menampilkan Data yang Sudah Tersimpan
st.subheader("Data Log Harian Tersimpan")

# Mengambil seluruh data dari tabel LogHarian
response = supabase.table("LogHarian").select("*").order("id", desc=True).execute()

if response.data:
    df = pd.DataFrame(response.data)
    # Merapikan kolom yang ditampilkan
    df_display = df[["id", "tanggal", "nama_karyawan", "jumlah_borongan", "total_gaji"]]
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("Belum ada data tersimpan di database.")
