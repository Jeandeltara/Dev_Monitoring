import os
import json
import glob
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_latest_report():
    print("Запуск модуля отправки на Google Диск...")
    
    # 1. Ищем самый свежий файл отчета в папке репозитория
    report_files = glob.glob("*_report.txt")
    if not report_files:
        print("❌ Ошибка: Файлы отчетов (*_report.txt) не найдены!")
        return
        
    # Сортируем файлы по имени (благодаря YYMMDD в начале, свежий всегда будет последним)
    report_files.sort()
    latest_report = report_files[-1]
    file_name = os.path.basename(latest_report)
    print(f"📁 Найден свежий отчет для отправки: {file_name}")

    # 2. Получаем секретный JSON-ключ из переменных окружения GitHub Actions
    secret_credentials = os.environ.get("GOOGLE_CREDENTIALS")
    if not secret_credentials:
        print("❌ Ошибка: Переменная окружения GOOGLE_CREDENTIALS не найдена!")
        return

    try:
        # Превращаем строку с секретом обратно в JSON-словарь
        creds_dict = json.loads(secret_credentials)
        
        # Область доступа (нам нужны полные права на работу с файлами Диска)
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
        # Строим клиент для работы с Google Drive API (версия v3)
        service = build('drive', 'v3', credentials=creds)
        
        # 3. Настройки файла и целевой папки
        FOLDER_ID = "1HLX_PykEsDvuOpp7gGnEoTaTYN49T050"  # ID вашей папки
        
        file_metadata = {
            'name': file_name,
            'parents': [FOLDER_ID]
        }
        
        # Подготавливаем файл к загрузке в текстовом формате
        media = MediaFileUpload(latest_report, mimetype='text/plain', resumable=True)
        
        print("🚀 Отправка файла в Google Drive...")
        # Выполняем запрос на создание файла на Диске
        drive_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"✅ Успех! Файл успешно загружен на Google Диск. ID файла: {drive_file.get('id')}")

    except Exception as e:
        print(f"❌ Произошла ошибка во время отправки: {e}")

if __name__ == "__main__":
    upload_latest_report()
