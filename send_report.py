import os
import glob
import json
import time
import shutil
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Настройки целевой папки
FOLDER_ID = '1HLX_PykEsDvuOpp7gGnEoTaTYN49T050'

def cleanup_old_files():
    """Удаляет локальные файлы, дата которых старше 3 суток."""
    print("Проверка на наличие устаревших файлов...")
    files = glob.glob("[0-9][0-9][0-9][0-9][0-9][0-9]_*.txt")
    now = datetime.now()
    
    for file_path in files:
        # Извлекаем дату из имени (первые 6 символов YYMMDD)
        date_str = file_path[:6]
        try:
            file_date = datetime.strptime(date_str, "%y%m%d")
            # Если разница больше 3 суток
            if now - file_date > timedelta(days=3):
                os.remove(file_path)
                print(f"Удален устаревший файл: {file_path}")
        except ValueError:
            continue

def get_report_files():
    """Ищет файлы по маске YYMMDD_*.txt"""
    return glob.glob("[0-9][0-9][0-9][0-9][0-9][0-9]_*.txt")

def main():
    # 1. Сначала проводим очистку
    cleanup_old_files()
    
    print("Запуск модуля отправки отчетов...")
    token_json_str = os.environ.get("GOOGLE_DRIVE_TOKEN")
    
    if not token_json_str:
        print("Ошибка: GOOGLE_DRIVE_TOKEN не найден!")
        return

    report_files = get_report_files()
    if not report_files:
        print("Файлы для отправки не найдены.")
        return

    try:
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data)
        service = build('drive', 'v3', credentials=creds)

        for file_path in report_files:
            timestamp = time.strftime("%H%M%S")
            parts = file_path.split('_', 1)
            temp_filename = f"{parts[0]}_{timestamp}_{parts[1]}"
            
            shutil.copy(file_path, temp_filename)
            
            try:
                file_metadata = {'name': temp_filename, 'parents': [FOLDER_ID]}
                media = MediaFileUpload(temp_filename, mimetype='text/plain', resumable=False)
                
                uploaded_file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                print(f"УСПЕХ! Файл {temp_filename} загружен.")
            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
