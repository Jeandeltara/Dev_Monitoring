import os
import glob
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Настройки целевой папки
FOLDER_ID = '1HLX_PykEsDvuOpp7gGnEoTaTYN49T050'

def get_latest_report():
    """Ищет самый свежий файл отчета в текущей папке."""
    files = glob.glob("*_report.txt")
    if not files:
        return None
    # Сортируем по имени (так как формат YYMMDD_HHMM_report.txt, самый свежий будет последним)
    files.sort()
    return files[-1]

def main():
    print("Запуск модуля отправки отчета на Google Диск...")
    
    # 1. Получаем токен из переменных окружения (туда его прокинет GitHub)
    token_json_str = os.environ.get("GOOGLE_DRIVE_TOKEN")
    if not token_json_str:
        print("Ошибка: Переменная окружения GOOGLE_DRIVE_TOKEN не найдена!")
        return

    # 2. Находим файл для отправки
    report_file = get_latest_report()
    if not report_file:
        print("Ошибка: В репозитории не найдено ни одного файла *_report.txt для отправки!")
        return
    print(f"Найден файл для отправки: {report_file}")

    try:
        # 3. Авторизуемся в Google API через сохраненные Credentials пользователя
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data)
        
        # Строим клиент для работы с Drive API v3
        service = build('drive', 'v3', credentials=creds)

        # 4. Готовим метаданные файла
        file_metadata = {
            'name': report_file,
            'parents': [FOLDER_ID]
        }
        
        # Готовим само тело файла для загрузки
        media = MediaFileUpload(report_file, mimetype='text/plain', resumable=False)

        print(f"Загрузка файла в папку {FOLDER_ID}...")
        
        # 5. Выполняем загрузку от имени пользователя
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"УСПЕХ! Файл успешно загружен. Google Drive ID: {uploaded_file.get('id')}")

    except Exception as e:
        print(f"Критическая ошибка при работе с Google Drive API: {e}")

if __name__ == "__main__":
    main()
