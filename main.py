import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser

def parse_rss_feed(url, start_time, end_time):
    """
    Сканирует RSS-ленты стандартных новостных ресурсов.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    print(f"  --> Сканирую RSS: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"      [Ошибка] Ошибка HTTP {response.status_code}")
            return found_urls
        soup = BeautifulSoup(response.text, "xml")
        items = soup.find_all("item")
        
        count_before_time = 0
        for item in items:
            pub_date_tag = item.find("pubDate")
            link_tag = item.find("link")
            if not pub_date_tag or not link_tag:
                continue
            try:
                news_datetime = parser.parse(pub_date_tag.text).replace(tzinfo=None)
            except Exception:
                continue
            
            if start_time <= news_datetime < end_time:
                found_urls.append(link_tag.text.strip())
                count_before_time += 1
        
        if count_before_time > 0:
            print(f"      [Успех] Найдено {count_before_time} новостей в интервале времени.")
    except requests.RequestException as e:
        print(f"      [Ошибка] Ошибка запроса: {e}")
    return found_urls

def parse_rayon_site(base_url, start_time, end_time):
    """
    Сканирует общую ленту новостей Rayon.in.ua и собирает ВСЕ ссылки на статьи.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    target_url = base_url.rstrip('/') + "/news"
    collected_links = []
    
    try:
        print(f"  --> Сканирую общую ленту Rayon: {target_url}...")
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return collected_links
            
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        all_anchors = soup.find_all("a", href=True)
        for anchor in all_anchors:
            href = anchor["href"]
            if "/news/" in href and not href.endswith("/news") and not href.endswith("/news/"):
                if href.startswith("/"):
                    full_url = base_url.rstrip('/') + href
                else:
                    full_url = href
                
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    
        print(f"      [Успех] Собрано {len(collected_links)} потенциальных ссылок для проверки.")
    except Exception as e:
        print(f"      [Ошибка] При сборе ссылок с {base_url}: {e}")
        
    return collected_links

def parse_charivne_site(start_time, end_time):
    """
    Парсит страницы "Усі новини" сайта charivne.info с контролем даты для пагинации.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    base_url = "https://charivne.info"
    collected_links = []
    
    months_ua = {
        "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
        "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12
    }
    
    yesterday_str = start_time.strftime("%d").lstrip('0')
    yesterday_month = start_time.month
    
    print(f"  --> Сканирую charivne.info (замена RSS)...")
    
    pages_to_parse = [1, 2]
    
    for page in pages_to_parse:
        url = f"{base_url}/allnews?page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                break
                
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            
            news_items = soup.find_all("div", class_="allnews-box") or soup.find_all("div", class_="the-news-container")
            
            if not news_items:
                news_items = [a.find_parent("div") for a in soup.find_all("a", href=re.compile(r"/news/\d+")) if a.find_parent("div")]
            
            has_yesterday_date = False
            page_links_count = 0
            
            for item in news_items:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                    
                href = link_tag["href"]
                full_url = href if href.startswith("http") else base_url + href
                item_text = item.get_text().lower()
                
                for m_name, m_num in months_ua.items():
                    if m_num == yesterday_month and m_name in item_text:
                        if yesterday_str in item_text:
                            has_yesterday_date = True
                            break
                
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    page_links_count += 1
            
            print(f"      Страница {page}: Собрано {page_links_count} ссылок.")
            
            if page == 1 and has_yesterday_date:
                print("      [Инфо] На первой странице обнаружена предыдущая дата. Вторая страница не требуется.")
                break
                
        except Exception as e:
            print(f"      [Ошибка] При парсинге страницы {page} на charivne.info: {e}")
            break

    print(f"      [Успех] Итого с charivne.info отправлено на фильтрацию: {len(collected_links)} ссылок.")
    return collected_links

def parse_vse_rv_site(start_time, end_time):
    """
    Сканирует одну страницу ленты новостей сайта ВСЕ (vse.rv.ua/strichka.html) 
    и собирает все ссылки на публикации.
    """
    base_url = "https://vse.rv.ua"
    target_url = f"{base_url}/strichka.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    collected_links = []
    
    print(f"  --> Сканирую ленту ВСЕ: {target_url} (замена RSS)...")
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return collected_links
            
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        all_anchors = soup.find_all("a", href=True)
        for anchor in all_anchors:
            href = anchor["href"]
            if href.startswith("/article/"):
                full_url = base_url + href
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    
        print(f"      [Успех] Собрано {len(collected_links)} потенциальных ссылок с vse.rv.ua.")
    except Exception as e:
        print(f"      [Ошибка] При сборе ссылок с {target_url}: {e}")
        
    return collected_links

def parse_radiotrek_site(start_time, end_time):
    base_url = "https://radiotrek.rv.ua"
    url = f"{base_url}/news/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    
    str_day_today = str(end_time.day)
    print(f"  --> Сканирую Радиотрек ({url})...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return found_urls
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        all_text_nodes = list(soup.find_all(string=True))
        
        start_index, end_index = None, None
        for index, node in enumerate(all_text_nodes):
            clean_text = node.strip()
            if start_index is None and clean_text.startswith(str_day_today) and len(clean_text) <= 15 and clean_text.isupper():
                start_index = index
                continue
            day_before_yesterday = str((start_time - timedelta(days=1)).day)
            if start_index is not None and end_index is None and clean_text.startswith(day_before_yesterday) and len(clean_text) <= 15 and clean_text.isupper():
                end_index = index
                break
        
        if start_index is None:
            print("      [Внимание] Не удалось надежно определить границы блоков дней на Радиотреке.")
            return found_urls
            
        target_nodes = all_text_nodes[start_index:] if end_index is None else all_text_nodes[start_index:end_index]
        for node in target_nodes:
            parent = node.find_parent("a")
            if parent:
                href = parent.get("href")
                if href and re.search(r"/news/.*_\d+\.html", href):
                    found_urls.append(href if href.startswith("http") else base_url.rstrip("/") + href)
    except requests.RequestException as e:
        print(f"      [Ошибка] {e}")
        
    print(f"      [Успех] Собрано {len(set(found_urls))} потенциальных ссылок.")
    return list(set(found_urls))

def parse_suspilne_site(start_time, end_time):
    base_url = "https://suspilne.media"
    url_regional = f"{base_url}/rivne/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    page = 1
    print(f"  --> Сканирую Суспильне ({url_regional})...")
    
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
                
                try:
                    article_datetime = parser.parse(time_tag["datetime"]).replace(tzinfo=None)
                except Exception:
                    continue
                
                if article_datetime < start_time:
                    stop_pagination = True
                    break
                    
                if start_time <= article_datetime < end_time:
                    link_tag = article.find("a")
                    if link_tag and link_tag.get("href"):
                        href = link_tag.get("href")
                        found_urls.append(href if href.startswith("http") else base_url + href)
            
            if stop_pagination:
                break
            page += 1
        except requests.RequestException:
            break
            
    print(f"      [Успех] Собрано {len(set(found_urls))} новостей строго по времени.")
    return list(set(found_urls))

def filter_pages_by_keyword(urls, keywords, start_time, end_time):
    """
    Обходит список URL, извлекает контент по специфическим шаблонам сайтов,
    проверяет временной интервал публикации и ищет ключевые слова/регулярки.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    filtered_results = []

    print(f"\n[ЭТАП 2] Глубокая контентная фильтрация ({len(urls)} ссылок)...")

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            title = soup.title.string.strip() if soup.title else "Без заголовка"
            time_tag = None
            clean_text = ""

            # 1. Шаблон для сети RAYON
            if "rayon.in.ua" in url:
                first_article = soup.find("article")
                if first_article:
                    time_tag = first_article.find("time") or first_article.find("meta", property="article:published_time")
                    for script in first_article(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = first_article.get_text(separator=" ")
                else:
                    continue

            # 2. Шаблон для RIVNE.MEDIA
            elif "rivne.media" in url:
                article_container = soup.find("article")
                if article_container:
                    time_tag = article_container.find("time") or article_container.find("meta", property="article:published_time")
                    for script in article_container(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = article_container.get_text(separator=" ")
                else:
                    continue

            # 3. Шаблон для CHARIVNE.INFO
            elif "charivne.info" in url:
                article_container = soup.find("article") or soup.find("div", class_="the-news-container") or soup.find("div", class_="single-news")
                if article_container:
                    time_tag = article_container.find("time") or soup.find("meta", property="article:published_time")
                    for script in article_container(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = article_container.get_text(separator=" ")
                else:
                    time_tag = soup.find("meta", property="article:published_time")
                    for script in soup(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = soup.get_text(separator=" ")

            # 4. Шаблон для ВСЕ (vse.rv.ua) - Изолируем фрейм статьи
            elif "vse.rv.ua" in url:
                article_container = soup.find("div", class_="article-inner__content")
                if article_container:
                    time_tag = soup.find("meta", property="article:published_time")
                    for script in article_container(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = article_container.get_text(separator=" ")
                else:
                    time_tag = soup.find("meta", property="article:published_time")
                    for script in soup(["script", "style", "noscript"]):
                        script.extract()
                    clean_text = soup.get_text(separator=" ")

            # 5. Дефолтный шаблон для остальных сайтов (Радиотрек, Суспильне и т.д.)
            else:
                time_tag = soup.find("time") or soup.find("meta", property="article:published_time")
                for script in soup(["script", "style", "noscript"]):
                    script.extract()
                clean_text = soup.get_text(separator=" ")

            # Валидация времени публикации
            if time_tag:
                try:
                    pub_time_str = time_tag.get("datetime") or time_tag.get("content") or time_tag.text.strip()
                    pub_time = parser.parse(pub_time_str).replace(tzinfo=None)
                    if not (start_time <= pub_time < end_time):
                        continue
                except Exception:
                    pass

            # Проверка контента на ключевые слова или регулярные выражения
            text_to_check = f"{title} {clean_text}".lower()
            
            for keyword in keywords:
                # Если фраза содержит спецсимволы регулярок, ищем её напрямую
                if any(char in keyword for char in ".*{}[]()|+?^$"):
                    match = re.search(keyword.lower(), text_to_check, flags=re.UNICODE)
                else:
                    # Обычные слова изолируем границами \b
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    match = re.search(pattern, text_to_check, flags=re.UNICODE)
                
                if match:
                    filtered_results.append({
                        "url": url,
                        "title": title,
                        "matched_keyword": keyword
                    })
                    break

        except Exception as e:
            continue

    print(f"  --> Фильтрация окончена. Найдено целевых новостей: {len(filtered_results)}")
    return filtered_results


if __name__ == "__main__":
    # Вычисление временного диапазона мониторинга (за последние 24 часа от 14:00)
    end_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)

    print("="*70)
    print(" ЗАПУСК МОНИТОРИНГА ПРЕССЫ")
    print(f" Целевой интервал: c {start_time} по {end_time}")
    print("="*70)

    all_links = []

    # -----------------------------------------------------------------
    # ШАГ 1: Сбор через RSS
    # -----------------------------------------------------------------
    rss_urls = [
        "https://rivnepost.rv.ua/rss",
        "https://ogo.ua/feed",
        "https://7dniv.rv.ua/feed/",
        "https://rivne1.tv/rss",
        "https://itvmg.com/rss",
        "https://teza.tv/rss"
    ]

    print("\n[ЭТАП 1.1] Сбор ссылок с RSS-источников...")
    for rss_url in rss_urls:
        links_from_rss = parse_rss_feed(rss_url, start_time, end_time)
        all_links.extend(links_from_rss)

    # -----------------------------------------------------------------
    # ШАГ 2: Сбор через HTML-ленты (Сайты без RSS)
    # -----------------------------------------------------------------
    print("\n[ЭТАП 1.2] Сбор ссылок со страниц новостей (HTML-парсинг)...")

    # А. Сеть сайтов "Район"
    rayon_sites = ["https://rivne.rayon.in.ua", "https://dubno.rayon.in.ua"]
    for site in rayon_sites:
        links_from_rayon = parse_rayon_site(site, start_time, end_time)
        all_links.extend(links_from_rayon)

    # Б. Стабильные HTML-модули (Радиотрек и Суспильне)
    links_from_radiotrek = parse_radiotrek_site(start_time, end_time)
    all_links.extend(links_from_radiotrek)

    links_from_suspilne = parse_suspilne_site(start_time, end_time)
    all_links.extend(links_from_suspilne)
    
    # В. Чаривне (замена RSS, пагинация)
    links_from_charivne = parse_charivne_site(start_time, end_time)
    all_links.extend(links_from_charivne)

    # Г. Сайт ВСЕ (замена RSS, парсинг одной страницы ленты)
    links_from_vse = parse_vse_rv_site(start_time, end_time)
    all_links.extend(links_from_vse)

    # -----------------------------------------------------------------
    # ШАГ 3: Очистка буфера от дубликатов
    # -----------------------------------------------------------------
    all_links = list(set(all_links))
    print(f"\n Всего уникальных кандидатов отправлено на глубокую фильтрацию: {len(all_links)}")

    # -----------------------------------------------------------------
    # ШАГ 4: Глубокая контентная фильтрация по шаблонам
    # -----------------------------------------------------------------
    keywords_list = [r"23.{0,4} інженерно"] 
    TARGET_NEWS_LIST = filter_pages_by_keyword(all_links, keywords_list, start_time, end_time)

    # -----------------------------------------------------------------
    # ШАГ 5: Формирование структуры финального отчета
    # -----------------------------------------------------------------
    print("\n" + "="*70)
    print(f" ФИНАЛЬНЫЙ ОТЧЕТ МОНИТОРИНГА (Найдено статей: {len(TARGET_NEWS_LIST)})")
    print("="*70)
    
    report_lines = []
    report_lines.append(f"ОТЧЕТ МОНИТОРИНГА СМИ ЗА ПЕРИОД: {start_time} -> {end_time}")
    report_lines.append(f"Ключевые слова поиска: {', '.join(keywords_list)}")
    report_lines.append(f"Всего проанализировано уникальных ссылок: {len(all_links)}")
    report_lines.append("-" * 60)
    
    if TARGET_NEWS_LIST:
        for idx, news in enumerate(TARGET_NEWS_LIST, 1):
            entry = f"{idx}. {news['title']}\n   Ссылка: {news['url']}\n   Найдено по ключу: [{news['matched_keyword']}]\n"
            print(entry)
            report_lines.append(entry)
    else:
        no_news_msg = "За указанный период релевантных публикаций не обнаружено."
        print(no_news_msg)
        report_lines.append(no_news_msg)
        
    report_lines.append("="*70)
    
    # -----------------------------------------------------------------
    # ШАГ 6: Автоматическое именование файла в формате YYMMDD_hhmm_report.txt
    # -----------------------------------------------------------------
    # Используем end_time (или datetime.now()) для генерации имени файла
    output_filename = end_time.strftime("%y%m%d_%H%M_report.txt")
    
    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write("\n".join(report_lines))
        print(f"\n[Успех] Отчет успешно создан локально: {output_filename}")
    except Exception as e:
        print(f"\n[Ошибка] Не удалось записать отчет в файл: {e}")
