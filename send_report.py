import os
import glob
import json
import time
import shutil
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Настройки целевой папки
FOLDER_ID = '1HLX_PykEsDvuOpp7gGnEoTaTYN49T050'

def get_report_files():
    """Ищет исходные файлы по маске (например, YYMMDD_*.txt)"""
    return glob.glob("[0-9][0-9][0-9][0-9][0-9][0-9]_*.txt")

def main():
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
            # 1. Генерируем имя для копии: YYMMDD_hhmmss_*.txt
            timestamp = time.strftime("%H%M%S")
            parts = file_path.split('_', 1)
            temp_filename = f"{parts[0]}_{timestamp}_{parts[1]}"
            
            # 2. Создаем временную копию
            shutil.copy(file_path, temp_filename)
            print(f"Создана временная копия: {temp_filename}")
            
            try:
                # 3. Загружаем копию на диск
                file_metadata = {
                    'name': temp_filename,
                    'parents': [FOLDER_ID]
                }
                media = MediaFileUpload(temp_filename, mimetype='text/plain', resumable=False)
                
                uploaded_file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                print(f"УСПЕХ! Файл {temp_filename} загружен. ID: {uploaded_file.get('id')}")
            
            finally:
                # 4. Удаляем временную копию после попытки загрузки (даже если была ошибка)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                    print(f"Временный файл {temp_filename} удален.")

    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
