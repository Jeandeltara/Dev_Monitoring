import os
import glob
import json
import time
import shutil
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration for Google Drive
FOLDER_ID = '1HLX_PykEsDvuOpp7gGnEoTaTYN49T050'

def cleanup_old_files():
    """Remove local files older than 3 days."""
    print("Checking for outdated files...")
    files = glob.glob("[0-9][0-9][0-9][0-9][0-9][0-9]_*.txt")
    now = datetime.now()
    
    for file_path in files:
        date_str = file_path[:6]
        try:
            file_date = datetime.strptime(date_str, "%y%m%d")
            if now - file_date > timedelta(days=3):
                os.remove(file_path)
                print(f"Removed outdated file: {file_path}")
        except ValueError:
            continue

def get_report_files():
    """Get list of files matching the YYMMDD_*.txt pattern."""
    return glob.glob("[0-9][0-9][0-9][0-9][0-9][0-9]_*.txt")

def send_email(file_path):
    """Send an email report using SMTP."""
    recipient = os.environ.get("EMAIL_RECIPIENT")
    smtp_user = os.environ.get("GMAIL_SMTP_USERNAME")
    smtp_pass = os.environ.get("GMAIL_SMTP_PASSWORD")

    if not all([recipient, smtp_user, smtp_pass]):
        print("Skipping email: missing environment variables.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = "Звіт про моніторинг регіональної преси"
    msg['From'] = smtp_user
    msg['To'] = recipient

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        print(f"Email successfully sent for {file_path}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    cleanup_old_files()
    
    token_json_str = os.environ.get("GOOGLE_DRIVE_TOKEN")
    if not token_json_str:
        print("Error: GOOGLE_DRIVE_TOKEN not found!")
        return

    report_files = get_report_files()
    if not report_files:
        print("No report files found.")
        return

    try:
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data)
        service = build('drive', 'v3', credentials=creds)

        for file_path in report_files:
            # 1. Send via Email
            send_email(file_path)

            # 2. Upload to Drive
            timestamp = time.strftime("%H%M%S")
            parts = file_path.split('_', 1)
            temp_filename = f"{parts[0]}_{timestamp}_{parts[1]}"
            
            shutil.copy(file_path, temp_filename)
            try:
                file_metadata = {'name': temp_filename, 'parents': [FOLDER_ID]}
                media = MediaFileUpload(temp_filename, mimetype='text/plain', resumable=False)
                service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                print(f"SUCCESS! File {temp_filename} uploaded to Drive.")
            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    main()
