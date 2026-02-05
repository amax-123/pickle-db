import os
import json
import io
import firebase_admin
from firebase_admin import credentials, firestore
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import google.generativeai as genai
from googleapiclient.http import MediaIoBaseDownload

# 1. SETUP & AUTH
# Load secrets from Environment Variables (set these in GitHub Secrets later)
FIREBASE_CREDENTIALS = json.loads(os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID") # The ID part of your Drive URL

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize Firebase
cred = credentials.Certificate(FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Drive API (Using the same Firebase Service Account!)
drive_creds = service_account.Credentials.from_service_account_info(
    FIREBASE_CREDENTIALS, scopes=['https://www.googleapis.com/auth/drive.readonly']
)
drive_service = build('drive', 'v3', credentials=drive_creds)

def download_pdf_text(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    # Simple PDF parsing (or send the raw bytes to Gemini 1.5 Pro directly if preferred)
    import PyPDF2
    fh.seek(0)
    reader = PyPDF2.PdfReader(fh)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def process_files():
    # 1. Check Drive for PDFs
    query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print("No files found.")
        return

    for item in items:
        file_id = item['id']
        file_name = item['name']
        
        # 2. Check if we already processed this file in Firestore
        doc_ref = db.collection('processed_files').document(file_id)
        if doc_ref.get().exists:
            print(f"Skipping {file_name} (Already processed)")
            continue

        print(f"Processing new file: {file_name}...")
        
        # 3. Download & Extract Text
        pdf_text = download_pdf_text(file_id)

        # 4. Ask Gemini to Extract Data
        prompt = f"""
        Extract the following tournament details from this text into a clean JSON format:
        - Tournament Name
        - Date(s)
        - Location
        - Events (List of categories with entry fees and prize money)
        - Organizer Contact
        
        TEXT CONTENT:
        {pdf_text}
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        
        try:
            tournament_data = json.loads(response.text)
            
            # 5. Save to Firestore "Tournaments" Collection
            # We let Firestore generate an ID, or use a unique field like name+date
            db.collection('tournaments').add(tournament_data)
            
            # 6. Mark as processed
            doc_ref.set({'file_name': file_name, 'processed_at': firestore.SERVER_TIMESTAMP})
            print(f"Successfully saved {file_name} to database.")
            
        except Exception as e:
            print(f"Error parsing JSON for {file_name}: {e}")

if __name__ == "__main__":
    process_files()
