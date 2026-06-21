import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser
from zoneinfo import ZoneInfo

def parse_rss_feed(url, target_date):
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    date_str_target = target_date.strftime("%d.%m.%Y")
    urls_to_parse = [f"{base_url}/news", f"{base_url}/news?page=2"]
    
    for url in urls_to_parse:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")
            first_news_link = soup.find("a", href=re.compile(r"/news/\d+"))
            
            if first_news_link:
                href = first_news_link.get("href")
                if not href:
                    continue
                full_url = href if href.startswith("http") else base_url.rstrip("/") + href
                parent_container = first_news_link.find_parent()
                container_text = ""
                for _ in range(3):
                    if parent_container:
                        container_text += " " + parent_container.get_text()
                        parent_container = parent_container.parent
                if date_str_target in container_text:
                    found_urls.append(full_url)
        except requests.RequestException:
            continue
    return list(set(found_urls))

def filter_pages_by_keyword(urls, keyword_pattern):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    filtered_results = []
    for index, url in enumerate(urls, 1):
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
                filtered_results.append({"url": url, "title": title, "text": clean_text})
        except requests.RequestException:
            continue
    return filtered_results

def parse_radiotrek_site(target_date):
    base_url = "https://radiotrek.rv.ua"
    url = f"{base_url}/news/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    str_day_today = str(target_date.day)
    str_day_yesterday = str((target_date - timedelta(days=1)).day)
    
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
            if start_index is not None and end_index is None and clean_text.startswith(str_day_yesterday) and len(clean_text) <= 15 and clean_text.isupper():
                end_index = index
                break
        
        if start_index is None:
            return found_urls
        target_nodes = all_text_nodes[start_index:] if end_index is None else all_text_nodes[start_index:end_index]
        for node in target_nodes:
            parent = node.find_parent("a")
            if parent:
                href = parent.get("href")
                if href and re.search(r"/news/.*_\d+\.html", href):
                    found_urls.append(href if href.startswith("http") else base_url.rstrip("/") + href)
    except requests.RequestException:
        pass
    return list(set(found_urls))

def parse_suspilne_site(target_date):
    base_url = "https://suspilne.media"
    url_regional = f"{base_url}/rivne/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    today_str = target_date.isoformat()
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
                article_date = time_tag["datetime"].split("T")[0]
                if article_date < today_str:
                    stop_pagination = True
                    break
                if article_date == today_str:
                    link_tag = article.find("a")
                    if link_tag and link_tag.get("href"):
                        href = link_tag.get("href")
                        found_urls.append(href if href.startswith("http") else base_url + href)
            if stop_pagination:
                break
            page += 1
        except requests.RequestException:
            break
    return list(set(found_urls))

if __name__ == "__main__":
    kyiv_zone = ZoneInfo("Europe/Kyiv")
    now = datetime.now(kyiv_zone)
    today = now.date()
    
    # Имя файла теперь создается в едином стиле
    file_name = f"{now.strftime('%y%m%d_%H%M')}_report.txt"
    
    rss_urls = [
        "https://rivnepost.rv.ua/rss", "https://ogo.ua/feed", "https://vse.rv.ua/rss",
        "https://charivne.info/rss", "https://7dniv.rv.ua/feed/", "https://rivne.media/rss",
        "https://rivne1.tv/rss", "https://itvmg.com/rss", "https://teza.tv/rss", "https://horyn.info/rss"
    ]
    
    all_links = []
    for url in rss_urls:
        all_links.extend(parse_rss_feed(url, today))
        
    rayon_sites = ["https://rivne.rayon.in.ua", "https://dubno.rayon.in.ua"]
    for site in rayon_sites:
        all_links.extend(parse_rayon_site(site, today))
        
    all_links.extend(parse_radiotrek_site(today))
    all_links.extend(parse_suspilne_site(today))
    all_links = list(set(all_links))
    
    keyword = r"23.{0,4} інженерно"  
    TARGET_NEWS_LIST = filter_pages_by_keyword(all_links, keyword)
    
    final_text = f"ОТЧЕТ: Найденные ссылки за {today} по ключевому слову '{keyword}'\n"
    final_text += "=" * 60 + "\n"
    for item in TARGET_NEWS_LIST:
        final_text += f"- {item['title']}\n  {item['url']}\n\n"
        
    with open(file_name, "w", encoding="utf-8") as file:
        file.write(final_text) 
        
    print(f"Файл {file_name} успешно сохранен локально.")
