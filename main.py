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
    
    print(f"  --> Сканирую ленту ВСЕ: {target_url} (замена RSS
