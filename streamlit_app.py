import streamlit as st
import pandas as pd
from datetime import datetime

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Formulir Data Pembeli Baju",
    layout="wide"
)

st.title("👕 Aplikasi Pengumpulan Data Pembeli Baju")

# --- Daftar Pilihan Dropdown ---
UKURAN_BAJU = ["XS","S", "M", "L", "XL", "XXL", "XXXL"]
MODEL_LENGAN = ["Pendek", "Panjang"]
STATUS_BAYAR = ["Belum Bayar", "Lunas Cash", "Lunas Transfer"]

# --- Formulir Input Data ---
with st.form(key='data_form'):
    st.header("Informasi Pembeli")
    nama = st.text_input("Nama Lengkap", placeholder="Masukkan nama pembeli")
    alamat = st.text_area("Alamat Lengkap", placeholder="Masukkan alamat pengiriman")

    st.header("Detail Pesanan")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        jumlah = st.number_input("Jumlah Baju", min_value=1, step=1)
    
    with col2:
        ukuran = st.selectbox("Ukuran Baju", options=UKURAN_BAJU)

    with col3:
        model = st.selectbox("Model Lengan Baju", options=MODEL_LENGAN)
    
    status_bayar = st.radio("Status Pembayaran", options=STATUS_BAYAR)
    
    # Tombol Submit
    submit_button = st.form_submit_button(label='Kirim Data Pesanan')

# --- Logika Pengiriman Data ---
if submit_button:
    if not nama or not alamat or jumlah <= 0:
        st.error("❌ Harap lengkapi Nama, Alamat, dan Jumlah Baju.")
    else:
        # Data yang akan dikirim
        data_pesanan = {
            'Nama': nama,
            'Alamat': alamat,
            'Jumlah Baju': jumlah,
            'Ukuran Baju': ukuran,
            'Model Lengan': model,
            'Status Pembayaran': status_bayar,
            'Waktu Input': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # --- Tempatkan Logika Penulisan ke Google Sheets di Sini ---
        # FUNGSI INI PERLU MENGGUNAKAN LIBRARY SEPERTI `gspread` UNTUK BERKOMUNIKASI DENGAN GOOGLE SHEETS
        # Untuk menyederhanakan, kita asumsikan fungsi penulisan_ke_sheet(data_pesanan) sudah siap
        
        try:
            # Gantilah dengan fungsi nyata untuk menulis ke Google Sheet
            # penulisan_ke_sheet(data_pesanan) 
            
            st.success("✅ Data pesanan berhasil direkam!")
            st.balloons()
            
            # Opsional: Tampilkan data yang baru saja direkam
            st.subheader("Data yang Direkam:")
            st.write(pd.DataFrame([data_pesanan]))

        except Exception as e:
            st.error(f"Terjadi kesalahan saat menyimpan data: {e}")
