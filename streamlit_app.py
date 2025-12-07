import streamlit as st
import pandas as pd
from datetime import datetime
import gspread 
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="Formulir Data Pembeli Baju",
    layout="wide"
)

# =================================================================
# ## KONFIGURASI DAN FUNGSI KONEKSI GOOGLE API
# =================================================================

# Ambil konfigurasi dari Streamlit Secrets
try:
    CREDS_INFO = st.secrets["gcp_service_account"]
    spreadsheet_name = st.secrets["spreadsheet_name"] 
    SHEET_DETAIL_NAME = st.secrets["sheet_detail"]
    SHEET_REKAP_NAME = st.secrets["sheet_rekap"]
    DRIVE_FOLDER_ID = st.secrets["drive_folder_id"]
except KeyError as e:
    st.error(f"Kesalahan Konfigurasi: Kunci '{e.args[0]}' tidak ditemukan di .streamlit/secrets.toml. Mohon periksa file secrets Anda.")
    st.stop()

@st.cache_resource(ttl=3600)
def get_gspread_client():
    """Mengotentikasi ke Google Sheets dan mengembalikan objek Spreadsheet."""
    try:
        gc = gspread.service_account_from_dict(CREDS_INFO)
        sh = gc.open(spreadsheet_name) 
        return sh
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets: {e}")
        return None

@st.cache_resource(ttl=3600)
def get_drive_service():
    """Mengotentikasi dan mengembalikan objek layanan Google Drive."""
    try:
        # Scope untuk akses Drive
        creds = service_account.Credentials.from_service_account_info(
            CREDS_INFO, 
            scopes=['https://www.googleapis.com/auth/drive'] 
        )
        # Bangun service Drive API
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Gagal menginisiasi layanan Google Drive: {e}")
        return None

def upload_to_drive(drive_service, uploaded_file, file_name):
    """Mengunggah file dari Streamlit ke Google Drive."""
    
    file_metadata = {
        'name': file_name,
        'parents': [DRIVE_FOLDER_ID]
    }
    
    # Membaca file yang diunggah Streamlit ke objek bytes
    file_content = uploaded_file.getvalue()
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=uploaded_file.type, resumable=True)
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webContentLink' 
    ).execute()
    
    # URL Foto yang dapat diakses publik (jika folder sudah diset publik)
    return f"https://drive.google.com/uc?export=view&id={file.get('id')}"

# =================================================================
# ## FORMULIR APLIKASI
# =================================================================

spreadsheet_obj = get_gspread_client()
drive_service = get_drive_service()
CURRENT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

st.title("👕 Aplikasi Pengumpulan Data Pembeli Baju")
st.markdown("Silakan isi data pesanan baju di bawah ini.")

UKURAN_BAJU = ["S", "M", "L", "XL", "XXL"]
MODEL_LENGAN = ["Pendek", "Panjang", "3/4"]
STATUS_BAYAR = ["Belum Bayar", "DP", "Lunas Cash", "Lunas Transfer"]

bukti_transfer = None
url_foto = "N/A"

with st.form(key='data_form'):
    st.header("Informasi Pembeli & Juru Arah")
    col_a, col_b = st.columns(2)
    with col_a:
        nama = st.text_input("Nama Lengkap", placeholder="Masukkan nama pembeli")
        telp = st.text_input("Nomor Telepon", placeholder="08xxxxxxxxxx")
    with col_b:
        juru_arah = st.text_input("Juru Arah/Koordinator", placeholder="Nama yang bertanggung jawab")
    
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
    
    if status_bayar == "Lunas Transfer":
        st.subheader("Bukti Transfer (Wajib)")
        bukti_transfer = st.file_uploader(
            "Unggah Foto Bukti Transfer (Max 5MB)", 
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=False,
            key='bukti_transfer_uploader'
        )
    
    submit_button = st.form_submit_button(label='Kirim Data Pesanan')

# =================================================================
# ## LOGIKA PENGIRIMAN DATA
# =================================================================
if submit_button:
    # --- Validasi ---
    if not all([nama, alamat, telp, juru_arah, jumlah > 0]):
        st.error("❌ Harap lengkapi semua kolom wajib.")
        st.stop()
    
    if status_bayar == "Lunas Transfer" and bukti_transfer is None:
        st.error("❌ Mohon unggah Bukti Transfer jika status pembayaran Lunas Transfer.")
        st.stop()

    if spreadsheet_obj is None or drive_service is None:
        st.error("Gagal terhubung ke layanan Google. Cek kredensial Secrets Anda.")
        st.stop()

    # --- 1. UPLOAD FOTO (Jika ada) ---
    if bukti_transfer is not None:
        try:
            file_extension = bukti_transfer.name.split(".")[-1]
            file_name_drive = f"Bukti_{nama.replace(' ', '_')}_{datetime.now().timestamp()}.{file_extension}"
            url_foto = upload_to_drive(drive_service, bukti_transfer, file_name_drive)
        except Exception as e:
            st.error(f"❌ Gagal mengunggah foto ke Google Drive: {e}. Pastikan FOLDER ID dan Izin Service Account sudah benar.")
            st.stop()

    # --- 2. PERSIAPAN DATA DICT ---
    data_dict = {
        'Nama': nama, 'Alamat': alamat, 'Telp': telp, 'Jumlah Baju': int(jumlah), 
        'Ukuran Baju': ukuran, 'Model Lengan': model, 
        'Status Pembayaran': status_bayar, 'Juru Arah': juru_arah,
        'Tanggal Pemesanan': CURRENT_TIME, 'URL Foto': url_foto
    }
    
    try:
        # --- 3. PENULISAN KE SHEET 'DETAIL PESANAN' (10 KOLOM) ---
        ws_detail = spreadsheet_obj.worksheet(SHEET_DETAIL_NAME)
        data_detail = [
            '', # No
            data_dict['Tanggal Pemesanan'], data_dict['Nama'], data_dict['Alamat'], 
            data_dict['Telp'], data_dict['Ukuran Baju'], data_dict['Model Lengan'], 
            data_dict['Status Pembayaran'], data_dict['Juru Arah'], 
            data_dict['URL Foto'] 
        ]
        ws_detail.append_row(data_detail)

        # --- 4. PENULISAN KE SHEET 'REKAP PESANAN' (8 KOLOM) ---
        ws_rekap = spreadsheet_obj.worksheet(SHEET_REKAP_NAME)
        data_rekap = [
            '', # No
            data_dict['Tanggal Pemesanan'], data_dict['Nama'], data_dict['Alamat'],
            data_dict['Jumlah Baju'], data_dict['Status Pembayaran'], 
            data_dict['Juru Arah'], data_dict['URL Foto'] # PERBAIKAN: URL Foto di kolom ke-8
        ]
        ws_rekap.append_row(data_rekap)

        st.success(f"✅ Data pesanan untuk {data_dict['Nama']} berhasil direkam ke Sheets dan Foto Bukti Transfer diunggah.")
        st.balloons()
        st.experimental_rerun()

    except gspread.exceptions.WorksheetNotFound as wnf:
        st.error(f"Gagal: Nama sheet tidak ditemukan: {wnf}. Pastikan nama sheet di Sheets dan Secrets sesuai.")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan data: {e}.")
        st.exception(e)
