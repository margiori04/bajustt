import streamlit as st
from datetime import datetime
import gspread 
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io

# ---- KONFIGURASI HALAMAN ----
st.set_page_config(page_title="Formulir Data Pembeli Baju", layout="wide")

# ---- AMBIL SECRETS KONFIGURASI ----
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
    try:
        gc = gspread.service_account_from_dict(CREDS_INFO)
        sh = gc.open(spreadsheet_name) 
        return sh
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets: {e}")
        return None

@st.cache_resource(ttl=3600)
def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_info(
            CREDS_INFO, scopes=['https://www.googleapis.com/auth/drive'] 
        )
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Gagal menginisiasi layanan Google Drive: {e}")
        return None

def upload_to_drive(drive_service, uploaded_file, file_name):
    file_metadata = {'name': file_name, 'parents': [DRIVE_FOLDER_ID]}
    file_content = uploaded_file.getvalue()
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=uploaded_file.type, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webContentLink'
    ).execute()
    return f"https://drive.google.com/uc?export=view&id={file.get('id')}"

# -------- UI INPUT DINAMIS ---------
st.title("👕 Aplikasi Pengumpulan Data Pembeli Baju")
st.markdown("Silakan isi data pesanan baju di bawah ini.")

# Pilihan tetap
UKURAN_BAJU = ["XS", "S", "M", "L", "XL", "XXL"]
MODEL_LENGAN = ["Pendek", "Panjang"]
STATUS_BAYAR = ["Belum Bayar", "Lunas Cash", "Lunas Transfer"]

# INPUT DATA DIRI (SEMUA DI LUAR FORM!!)
st.header("Informasi Pembeli & Juru Arah")
col_a, col_b = st.columns(2)
juru_arah = st.text_input("Juru Arah/Koordinator", placeholder="Nama yang bertanggung jawab")
nama = st.text_input("Nama Lengkap", placeholder="Masukkan nama pembeli")
telp = st.text_input("Nomor Telepon", placeholder="08xxxxxxxxxx")
alamat = st.text_area("Alamat Lengkap", placeholder="Masukkan alamat pengiriman")

st.header("Detail Pesanan")
jumlah = st.number_input("Jumlah Baju", min_value=1, step=1, value=1, format="%d")

# ------- DYNAMIC FIELDS: Ukuran & Model per Baju -------
list_ukuran = []
list_model = []
st.write("**Isi ukuran & model untuk setiap baju:**")
for i in range(1, int(jumlah) + 1):
    st.markdown(f"##### Baju {i}")
    col1, col2 = st.columns(2)
    with col1:
        ukuran = st.selectbox(
            f"Ukuran Baju {i}", 
            options=UKURAN_BAJU, 
            key=f"ukuran_{i}"
        )
    with col2:
        model = st.selectbox(
            f"Model Lengan Baju {i}", 
            options=MODEL_LENGAN, 
            key=f"model_{i}"
        )
    list_ukuran.append(ukuran)
    list_model.append(model)

status_bayar = st.radio("Status Pembayaran", options=STATUS_BAYAR)

bukti_transfer = None
if status_bayar == "Lunas Transfer":
    st.subheader("Bukti Transfer (Wajib)")
    bukti_transfer = st.file_uploader(
        "Unggah Foto Bukti Transfer (Max 5MB)", 
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=False,
        key='bukti_transfer_uploader'
    )

# ==== TOMBOL SUBMIT SAJA YANG DI DALAM FORM ====
with st.form(key='form_kirim'):
    submit_button = st.form_submit_button(label='Kirim Data Pesanan')

# ==== LOGIKA SUBMIT ====
if submit_button:
    # Ambil ulang waktu submit
    CURRENT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spreadsheet_obj = get_gspread_client()
    drive_service = get_drive_service()
    url_foto = "N/A"

    # Validasi manual field wajib
    if not all([nama, alamat, telp, juru_arah, int(jumlah) > 0]):
        st.error("❌ Harap lengkapi semua kolom wajib.")
        st.stop()
    if status_bayar == "Lunas Transfer" and bukti_transfer is None:
        st.error("❌ Mohon unggah Bukti Transfer jika status pembayaran Lunas Transfer.")
        st.stop()
    if spreadsheet_obj is None or drive_service is None:
        st.error("Gagal terhubung ke layanan Google. Cek kredensial Secrets Anda.")
        st.stop()

    # Upload foto jika ada
    if bukti_transfer is not None:
        try:
            file_extension = bukti_transfer.name.split(".")[-1]
            file_name_drive = f"Bukti_{nama.replace(' ', '_')}_{datetime.now().timestamp()}.{file_extension}"
            url_foto = upload_to_drive(drive_service, bukti_transfer, file_name_drive)
        except Exception as e:
            st.error(f"❌ Gagal mengunggah foto ke Google Drive: {e}. Pastikan FOLDER ID dan Izin Service Account sudah benar.")
            st.stop()
    
    # Gabung detail baju
    detail_baju_str = "; ".join([f"Baju {i+1}: {list_ukuran[i]}-{list_model[i]}" for i in range(int(jumlah))])

    data_dict = {
        'Nama': nama, 'Alamat': alamat, 'Telp': telp, 'Jumlah Baju': int(jumlah), 
        'Detail Semua Baju': detail_baju_str,  
        'Status Pembayaran': status_bayar, 
        'Juru Arah': juru_arah,
        'Tanggal Pemesanan': CURRENT_TIME, 
        'URL Foto': url_foto
    }
    
    try:
        # Sheet detail (edit kolom jika ingin struktur lain)
        ws_detail = spreadsheet_obj.worksheet(SHEET_DETAIL_NAME)
        data_detail = [
            '', # No
            data_dict['Tanggal Pemesanan'], data_dict['Nama'], data_dict['Alamat'], 
            data_dict['Telp'], data_dict['Detail Semua Baju'],
            data_dict['Status Pembayaran'], data_dict['Juru Arah'], data_dict['URL Foto'] 
        ]
        ws_detail.append_row(data_detail)

        ws_rekap = spreadsheet_obj.worksheet(SHEET_REKAP_NAME)
        data_rekap = [
            '', # No
            data_dict['Tanggal Pemesanan'], data_dict['Nama'], data_dict['Alamat'],
            data_dict['Jumlah Baju'], data_dict['Status Pembayaran'], 
            data_dict['Juru Arah'], data_dict['URL Foto']
        ]
        ws_rekap.append_row(data_rekap)

        st.success(f"✅ Data pesanan untuk {data_dict['Nama']} berhasil direkam ke Sheets.")
        st.balloons()
        st.experimental_rerun()

    except gspread.exceptions.WorksheetNotFound as wnf:
        st.error(f"Gagal: Nama sheet tidak ditemukan: {wnf}. Pastikan nama sheet di Sheets dan Secrets sesuai.")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan data: {e}.")
        st.exception(e)
