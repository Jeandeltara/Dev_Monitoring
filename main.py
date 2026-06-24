import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
import re

# --- CONFIGURATION ---
KEYWORDS_LIST = [r"23.{0,4} інженерно", "дубно"]

def get_soup(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# --- PARSERS ---

def parse_rivnepost(start_time, end_time):
    urls = []
    page = 1
    while True:
        url = "https://rivnepost.rv.ua/category/news" if page == 1 else f"https://rivnepost.rv.ua/category/news/page/{page}/"
        soup = get_soup(url)
        if not soup: break
        articles = soup.select('div.list-item')
        if not articles: break
        stop = False
        for art in articles:
            time_tag = art.find("time")
            if time_tag and time_tag.get("datetime"):
                dt = parser.parse(time_tag["datetime"]).replace(tzinfo=None)
                if dt < start_time: stop = True; break
                if start_time <= dt < end_time:
                    link = art.find("a", href=True)
                    if link: urls.append(link["href"])
        if stop: break
        page += 1
    return urls

def parse_ogo(start_time, end_time):
    urls = []
    page = 1
    while True:
        url = "https://ogo.ua/rubrics/view/region" if page == 1 else f"https://ogo.ua/rubrics/view/region/page/{page}/"
        soup = get_soup(url)
        if not soup: break
        articles = soup.find_all("article")
        if not articles: break
        stop = False
        for art in articles:
            time_tag = art.find("time")
            if time_tag and time_tag.get("datetime"):
                dt = parser.parse(time_tag["datetime"]).replace(tzinfo=None)
                if dt < start_time: stop = True; break
                if start_time <= dt < end_time:
                    link = art.find("a", href=True)
                    if link: urls.append(link["href"])
        if stop: break
        page += 1
    return urls

def parse_7dniv(start_time, end_time):
    urls = []
    page = 1
    while True:
        url = "https://7dniv.rv.ua/news/" if page == 1 else f"https://7dniv.rv.ua/news/page/{page}/"
        soup = get_soup(url)
        if not soup: break
        articles = soup.select('div.post-item')
        if not articles: break
        stop = False
        for art in articles:
            time_tag = art.find("time")
            if time_tag and time_tag.get("datetime"):
                dt = parser.parse(time_tag["datetime"]).replace(tzinfo=None)
                if dt < start_time: stop = True; break
                if start_time <= dt < end_time:
                    link = art.find("a", href=True)
                    if link: urls.append(link["href"])
        if stop: break
        page += 1
    return urls

def parse_rivne1(start_time, end_time):
    urls = []
    offset = 0
    while True:
        url = f"https://rivne1.tv/allnews?offset={offset}"
        soup = get_soup(url)
        if not soup: break
        articles = soup.select('ul.list-st-3 li')
        if not articles: break
        
        # Rivne1 особенность: дата в родительском блоке, тут упрощенная логика
        # Если нужно точное сравнение даты, берем ее из страницы новости
        for art in articles:
            link = art.find("a", href=True)
            if link: urls.append(link["href"])
        if len(articles) < 10: break 
        offset += 40
    return urls

def parse_itvmg(start_time, end_time):
    urls = []
    page = 0
    while True:
        url = "https://itvmg.com/novini" if page == 0 else f"https://itvmg.com/novini/{page*21}"
        soup = get_soup(url)
        if not soup: break
        items = soup.select('.list-style > div')
        if not items: break
        for item in items:
            link = item.find("a", href=True)
            if link: urls.append(link["href"])
        page += 1
        if page > 10: break
    return urls

def parse_teza(start_time, end_time):
    urls = []
    url = "https://teza.tv/category/news/"
    soup = get_soup(url)
    if soup:
        articles = soup.select('article')
        for art in articles:
            link = art.find("a", href=True)
            if link: urls.append(link["href"])
    return urls

# --- MAIN ---

def main():
    end_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)
    
    print("="*70)
    print("STARTING MEDIA MONITORING")
    print(f"Interval: {start_time} to {end_time}")
    print("="*70)

    # Collect all links
    all_links = []
    parsers = [parse_rivnepost, parse_ogo, parse_7dniv, parse_rivne1, parse_itvmg, parse_teza]
    
    for parser_func in parsers:
        try:
            all_links.extend(parser_func(start_time, end_time))
        except Exception as e:
            print(f"Error in {parser_func.__name__}: {e}")

    unique_links = list(set(all_links))
    print(f"Collected {len(unique_links)} unique links.")

    # Здесь вы вызываете свою функцию filter_pages_by_keyword(unique_links, ...)
    
    print("\n" + "="*70)
    print("ЗВІТ МОНІТОРИНГУ ПРЕСИ")
    print(f"Період: {start_time} — {end_time}")
    print("="*70)

if __name__ == "__main__":
    main()
