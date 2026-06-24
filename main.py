import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser

# --- КОНФІГУРАЦІЯ ---
KEYWORDS_LIST = [r"23.{0,4} інженерно"]

def parse_rss_feed(url, start_time, end_time):
    """
    Scans RSS feeds of standard news resources and returns a list of article URLs 
    published within the specified time interval.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    print(f"  --> Scanning RSS: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"      [Помилка] HTTP Error {response.status_code}")
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
            print(f"      [Успішно] Знайдено {count_before_time} новин у заданому інтервалі.")
    except requests.RequestException as e:
        print(f"      [Помилка] Помилка запиту: {e}")
    return found_urls

def parse_rayon_site(base_url, start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    target_url = base_url.rstrip('/') + "/news"
    collected_links = []
    
    try:
        print(f"  --> Scanning general Rayon feed: {target_url}...")
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return collected_links
            
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        all_anchors = soup.find_all("a", href=True)
        for anchor in all_anchors:
            href = anchor["href"]
            if "/news/" in href and not href.endswith("/news") and not href.endswith("/news/"):
                full_url = base_url.rstrip('/') + href if href.startswith("/") else href
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    
        print(f"      [Успішно] Зібрано {len(collected_links)} потенційних посилань для перевірки.")
    except Exception as e:
        print(f"      [Помилка] Помилка при зборі посилань з {base_url}: {e}")
        
    return collected_links

def parse_charivne_site(start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    base_url = "https://charivne.info"
    collected_links = []
    
    months_ua = {
        "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
        "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12
    }
    
    yesterday_str = start_time.strftime("%d").lstrip('0')
    yesterday_month = start_time.month
    
    print(f"  --> Scanning charivne.info (RSS replacement)...")
    
    for page in [1, 2]:
        url = f"{base_url}/allnews?page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200: break
                
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            
            news_items = soup.find_all("div", class_="allnews-box") or soup.find_all("div", class_="the-news-container")
            if not news_items:
                news_items = [a.find_parent("div") for a in soup.find_all("a", href=re.compile(r"/news/\d+")) if a.find_parent("div")]
            
            has_yesterday_date = False
            page_links_count = 0
            
            for item in news_items:
                link_tag = item.find("a", href=True)
                if not link_tag: continue
                    
                full_url = link_tag["href"] if link_tag["href"].startswith("http") else base_url + link_tag["href"]
                item_text = item.get_text().lower()
                
                for m_name, m_num in months_ua.items():
                    if m_num == yesterday_month and m_name in item_text:
                        if yesterday_str in item_text:
                            has_yesterday_date = True
                            break
                
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    page_links_count += 1
            
            print(f"      Сторінка {page}: Зібрано {page_links_count} посилань.")
            if page == 1 and has_yesterday_date:
                print("      [Інфо] Дата вчорашнього дня знайдена. Друга сторінка не потрібна.")
                break
        except Exception as e:
            print(f"      [Помилка] Помилка на сторінці {page} (charivne.info): {e}")
            break

    print(f"      [Успішно] Всього відправлено на фільтрацію: {len(collected_links)} посилань.")
    return collected_links

def parse_vse_rv_site(start_time, end_time):
    base_url = "https://vse.rv.ua"
    target_url = f"{base_url}/strichka.html"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    collected_links = []
    
    print(f"  --> Scanning VSE feed: {target_url} (RSS replacement)...")
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code != 200: return collected_links
            
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        for anchor in soup.find_all("a", href=True):
            if anchor["href"].startswith("/article/"):
                full_url = base_url + anchor["href"]
                if full_url not in collected_links:
                    collected_links.append(full_url)
                    
        print(f"      [Успішно] Зібрано {len(collected_links)} потенційних посилань.")
    except Exception as e:
        print(f"      [Помилка] Помилка при зборі з {target_url}: {e}")
        
    return collected_links

def parse_radiotrek_site(start_time, end_time):
    base_url = "https://radiotrek.rv.ua"
    url = f"{base_url}/news/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    
    str_day_today = str(end_time.day)
    print(f"  --> Scanning Radiotrek ({url})...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return found_urls
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        all_text_nodes = list(soup.find_all(string=True))
        
        start_index, end_index = None, None
        for index, node in enumerate(all_text_nodes):
            clean_text = node.strip()
            if start_index is None and clean_text.startswith(str_day_today) and len(clean_text) <= 15 and clean_text.isupper():
                start_index = index
                continue
            day_before = str((start_time - timedelta(days=1)).day)
            if start_index is not None and end_index is None and clean_text.startswith(day_before) and len(clean_text) <= 15 and clean_text.isupper():
                end_index = index
                break
        
        if start_index is None:
            print("      [Попередження] Не вдалося надійно визначити межі блоків на Radiotrek.")
            return found_urls
            
        target_nodes = all_text_nodes[start_index:] if end_index is None else all_text_nodes[start_index:end_index]
        for node in target_nodes:
            parent = node.find_parent("a")
            if parent:
                href = parent.get("href")
                if href and re.search(r"/news/.*_\d+\.html", href):
                    found_urls.append(href if href.startswith("http") else base_url.rstrip("/") + href)
    except requests.RequestException as e:
        print(f"      [Помилка] {e}")
        
    print(f"      [Успішно] Зібрано {len(set(found_urls))} потенційних посилань.")
    return list(set(found_urls))

def parse_suspilne_site(start_time, end_time):
    base_url = "https://suspilne.media"
    url_regional = f"{base_url}/rivne/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    page = 1
    print(f"  --> Scanning Suspilne ({url_regional})...")
    
    while True:
        url = f"{url_regional}?p={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200: break
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            
            stop_pagination = False
            for article in articles:
                time_tag
