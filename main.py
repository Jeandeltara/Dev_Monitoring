import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from zoneinfo import ZoneInfo

def upload_to_google_drive(file_name, folder_id):
    print(f"Начинаем отправку файла {file_name} на Google Диск...")
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json:
            print("Ошибка: Секрет GOOGLE_CREDENTIALS не найден в настройках GitHub!")
            return

        service_account_info = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(
            service_account_info, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=credentials)

        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        media = MediaFileUpload(file_name, mimetype="text/plain")

        # Добавили supportsAllDrives=True, чтобы корректно работать с правами папки
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        print(f"Успех! Файл успешно загружен на Google Диск. ID файла: {uploaded_file.get('id')}")

    except Exception as e:
        print(f"Ошибка при загрузке на Google Диск: {e}")

def parse_rss_feed(url, target_date):
    """Сканирует одну стандартную RSS-ленту и возвращает ссылки за целевую дату."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return found_urls
        soup = BeautifulSoup(response.text, "xml")
        for item in soup.find_all("item"):
            pub_date_tag = item.find("pubDate")
            link_tag = item.find("link")
            if not pub_date_tag or not link_tag:
                continue
            try:
                news_date = parser.parse(pub_date_tag.text).replace(tzinfo=None).date()
            except Exception:
                continue
            if news_date == target_date:
                found_urls.append(link_tag.text.strip())
    except requests.RequestException:
        pass
    return found_urls


def parse_rayon_site(base_url, target_date):
    """
    Парсит только САМУЮ ПЕРВУЮ (свежую) новость на 1-й и 2-й страницах разделов «Район».
    Полностью игнорирует все последующие блоки, анонсы и боковые колонки.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    
    # Текстовый формат даты для проверки (например, "21.06.2026")
    date_str_target = target_date.strftime("%d.%m.%Y")
    
    urls_to_parse = [
        f"{base_url}/news",
        f"{base_url}/news?page=2"
    ]
    
    for url in urls_to_parse:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Находим самый ПЕРВЫЙ тег ссылки, ведущий на статью (содержит /news/ и цифры ID)
            # Метод find() возвращает только один первый элемент сверху вниз по коду страницы
            first_news_link = soup.find("a", href=re.compile(r"/news/\d+"))
            
            if first_news_link:
                href = first_news_link.get("href")
                if not href:
                    continue
                
                # Собираем абсолютную ссылку
                if not href.startswith("http"):
                    full_url = base_url.rstrip("/") + href
                else:
                    full_url = href
                
                # Поднимаемся к ближайшему контейнеру этой новости, чтобы забрать её дату
                # get_text() соберет весь текст карточки, включая строчку с датой вида "21.06.2026 09:07"
                parent_container = first_news_link.find_parent()
                container_text = ""
                
                for _ in range(3):  # Поднимаемся максимум на 3 уровня, чтобы не захватить лишнего
                    if parent_container:
                        container_text += " " + parent_container.get_text()
                        parent_container = parent_container.parent
                
                # Проверяем, принадлежит ли эта первая новость к сегодняшнему числу
                if date_str_target in container_text:
                    found_urls.append(full_url)
                    print(f"  [Найдено на {url}] Свежая статья: {full_url}")
                else:
                    print(f"  [Пропущено на {url}] Первая статья старая (не за сегодня).")
                            
        except requests.RequestException:
            print(f"  -> Ошибка при скачивании ленты Района: {url}")
            continue
            
    return list(set(found_urls))


def filter_pages_by_keyword(urls, keyword_pattern):
    """Скачивает текст страниц и фильтрует их по регулярному выражению."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    filtered_results = []

    print(f"\nНачинаем фильтрацию страниц по шаблону: '{keyword_pattern}'...")
    
    for index, url in enumerate(urls, 1):
        print(f"[{index}/{len(urls)}] Проверяем страницу: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=7)
            if response.status_code != 200:
                continue
            
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            
            title = soup.title.string.strip() if soup.title else "Без заголовка"
            
            for script in soup(["script", "style", "noscript"]):
                script.extract()
            clean_text = soup.get_text(separator=" ")

            if re.search(keyword_pattern, clean_text, re.IGNORECASE):
                print(f"  -> НАЙДЕНО СОВПАДЕНИЕ в: '{title}'")
                filtered_results.append({
                    "url": url,
                    "title": title,
                    "text": clean_text
                })
                
        except requests.RequestException:
            print(f"  -> Ошибка при скачивании страницы: {url}")
            continue

    return filtered_results

def parse_radiotrek_site():
    """
    Парсит ленту Радіо ТРЕК. Использует текстовые разделители дней как границы.
    Находит строки, начинающиеся с сегодняшнего/вчерашнего числа длиной <= 15 символов,
    и собирает ссылки строго между ними.
    """
    base_url = "https://radiotrek.rv.ua"
    url = f"{base_url}/news/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    
    # Получаем числа текущего и вчерашнего дней
    today_dt = datetime.now()
    yesterday_dt = today_dt - timedelta(days=1)
    
    str_day_today = str(today_dt.day)          # Например: "21"
    str_day_yesterday = str(yesterday_dt.day)  # Например: "20"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return found_urls
            
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Перебираем абсолютно все текстовые узлы на странице сверху вниз
        all_text_nodes = list(soup.find_all(string=True))
        
        start_index = None
        end_index = None
        
        for index, node in enumerate(all_text_nodes):
            clean_text = node.strip()
            
            # Ищем маркер СЕГОДНЯ: строка начинается с числа и её длина не более 15 символов
            if start_index is None and clean_text.startswith(str_day_today) and len(clean_text) <= 15:
                # Дополнительно проверяем, что это капс (характерно для их календаря)
                if clean_text.isupper():
                    start_index = index
                    continue
            
            # Ищем маркер ВЧЕРА: строка начинается с числа вчерашнего дня и длина <= 15 символов
            if start_index is not None and end_index is None and clean_text.startswith(str_day_yesterday) and len(clean_text) <= 15:
                if clean_text.isupper():
                    end_index = index
                    break
        
        if start_index is None:
            print(f"  -> Не удалось найти календарный маркер для сегодняшнего дня ({str_day_today}).")
            return found_urls
            
        # Вырезаем только те текстовые и HTML элементы, которые лежат между границами дней
        # Если вчерашний день не нашли на 1-й странице, берем всё до конца
        if end_index is None:
            target_nodes = all_text_nodes[start_index:]
        else:
            target_nodes = all_text_nodes[start_index:end_index]
            
        # Из собранного куска вытаскиваем ссылки на статьи
        # Так как мы работаем со списком строк, нам нужно найти ссылки, связанные с этими строками
        for node in target_nodes:
            parent = node.find_parent("a")
            if parent:
                href = parent.get("href")
                if href and re.search(r"/news/.*_\d+\.html", href):
                    if not href.startswith("http"):
                        full_url = base_url.rstrip("/") + href
                    else:
                        full_url = href
                    found_urls.append(full_url)
                    
    except requests.RequestException as e:
        print(f"  -> Ошибка при скачивании ленты Радіо ТРЕК: {e}")
        
    return list(set(found_urls))

def parse_suspilne_site():
    """
    Парсит региональную ленту Суспільне Рівне по страницам.
    Сверяет дату из атрибута datetime тега <time>.
    Останавливает пагинацию (break), как только натыкается на вчерашнюю новость.
    """
    base_url = "https://suspilne.media"
    url_regional = f"{base_url}/rivne/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    
    # Получаем сегодняшнюю дату в формате "2026-06-21" для сверки с ISO-форматом сайта
    today_str = datetime.now().date().isoformat()
    
    page = 1
    while True:
        url = f"{url_regional}?p={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                break
                
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            
            articles = soup.find_all("article")
            if not articles:
                break
                
            stop_pagination = False
            
            for article in articles:
                time_tag = article.find("time")
                if not time_tag or not time_tag.get("datetime"):
                    continue
                
                # Извлекаем дату из "2026-06-21T10:31+03:00" -> получаем "2026-06-21"
                article_date = time_tag["datetime"].split("T")[0]
                
                # ЖЕЛЕЗНОЕ УСЛОВИЕ ОСТАНОВКИ: если пошли вчерашние новости — стоп машина
                if article_date < today_str:
                    stop_pagination = True
                    break
                
                # Если новость сегодняшняя — забираем её ссылку
                if article_date == today_str:
                    link_tag = article.find("a")
                    if not link_tag:
                        continue
                        
                    href = link_tag.get("href")
                    if href:
                        if href.startswith("/"):
                            full_url = base_url + href
                        else:
                            full_url = href
                        found_urls.append(full_url)
            
            if stop_pagination:
                break
                
            page += 1
            
        except requests.RequestException:
            print(f"  -> Ошибка при скачивании Суспільного, страница {page}")
            break
            
    return list(set(found_urls))


TARGET_NEWS_LIST = []

# --- БЛОК ЗАПУСКА (Полный конвейер: RSS + Район + Радіо ТРЕК + Суспільне) ---
if __name__ == "__main__":
    GOOGLE_FOLDER_ID = "1HLX_PykEsDvuOpp7gGnEoTaTYN49T050"
    
    # 1. Настройка даты и имени файла
    kyiv_zone = ZoneInfo("Europe/Kyiv")
    now = datetime.now(kyiv_zone)
    file_name = f"{now.strftime('%y%m%d_%H%M')}_report.txt"
    today = now.date()
    
    print("Запуск парсера новостей...")
    print(f"Ищем новости за СЕГОДНЯ: {today}\n")

    # 2. Стандартные RSS-ленты
    rss_urls = [
        "https://rivnepost.rv.ua/rss", 
        "https://ogo.ua/feed",
        "https://vse.rv.ua/rss",
        "https://charivne.info/rss",
        "https://7dniv.rv.ua/feed/",
        "https://rivne.media/rss",
        "https://rivne.media/rss",  
        "https://rivne1.tv/rss",
        "https://itvmg.com/rss",
        "https://teza.tv/rss",
        "https://horyn.info/rss"
    ]

    all_links = []
    
    print("--- ШАГ 1: Сканирование RSS-лент ---")
    for url in rss_urls:
        print(f"Сканируем RSS ленту: {url}...")
        all_links.extend(parse_rss_feed(url, today))
        
    # 3. Сканируем сайты сети «Район»
    print("\n--- ШАГ 2: Сканирование сети «Район» (Сайты без RSS) ---")
    rayon_sites = [
        "https://rivne.rayon.in.ua",
        "https://dubno.rayon.in.ua"
    ]
    for site in rayon_sites:
        print(f"Парсим сайт: {site}...")
        all_links.extend(parse_rayon_site(site, today))

    # 4. Сканируем Радіо ТРЕК
    print("\n--- ШАГ 3: Сканирование Радіо ТРЕК (Сайт без RSS) ---")
    print("Парсим ленту Радіо ТРЕК...")
    all_links.extend(parse_radiotrek_site())

    # 5. Сканируем Суспільне
    print("\n--- ШАГ 4: Сканирование Суспільне Рівне (Сайт без RSS) ---")
    print("Парсим ленту Суспільного...")
    all_links.extend(parse_suspilne_site())

    # Убираем дубликаты
    all_links = list(set(all_links))
    print(f"\nВсего собрано уникальных ссылок из всех источников: {len(all_links)}")

    # 6. Фильтруем собранные ссылки
    keyword = r"23.{0,4} інженерно"  
    TARGET_NEWS_LIST = filter_pages_by_keyword(all_links, keyword)

    # 7. Формируем текст отчета
    final_text = f"ОТЧЕТ: Найденные ссылки за {today} по ключевому слову '{keyword}'\n"
    final_text += "=" * 60 + "\n"
    for item in TARGET_NEWS_LIST:
        final_text += f"- {item['title']}\n  {item['url']}\n\n"

    # 8. Запись локального файла с правильным динамическим именем
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(final_text)
        
    print(f"Локальный файл {file_name} успешно создан.")
    
    # 9. Отправка готового файла на Google Диск
    upload_to_google_drive(file_name, GOOGLE_FOLDER_ID)
            
    print("\n" + "=" * 40)
    print(f"ФИЛЬТРАЦИЯ ЗАВЕРШЕНА. Отобрано статей: {len(TARGET_NEWS_LIST)}")
    print(f"Полный отчет сохранен в файле: {file_name}")
    print("=" * 40)

