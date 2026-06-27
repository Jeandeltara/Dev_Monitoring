import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser

# --- КОНФІГУРАЦІЯ ---
KEYWORDS_LIST = [r"23.{0,4} інженерно", "А0451"]

def parse_rss_feed(url, start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    found_urls = []
    print(f"  --> Scanning RSS: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return found_urls
        soup = BeautifulSoup(response.text, "xml")
        for item in soup.find_all("item"):
            pub_date_tag = item.find("pubDate")
            link_tag = item.find("link")
            if not pub_date_tag or not link_tag: continue
            try:
                news_datetime = parser.parse(pub_date_tag.text).replace(tzinfo=None)
                if start_time <= news_datetime < end_time:
                    found_urls.append(link_tag.text.strip())
            except Exception: continue
    except Exception as e:
        print(f"      [Помилка] RSS {url}: {e}")
    return found_urls

def parse_rayon_site(base_url, start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    target_url = base_url.rstrip('/') + "/news"
    collected_links = []
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for anchor in soup.find_all("a", href=True):
                if "/news/" in anchor["href"] and not anchor["href"].endswith("/news"):
                    full_url = base_url.rstrip('/') + anchor["href"] if anchor["href"].startswith("/") else anchor["href"]
                    if full_url not in collected_links: collected_links.append(full_url)
    except Exception as e:
        print(f"      [Помилка] Rayon {base_url}: {e}")
    return collected_links

def parse_charivne_site(start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    base_url = "https://charivne.info"
    collected_links = []
    yesterday_str = start_time.strftime("%d").lstrip('0')
    yesterday_month = start_time.month
    months_ua = {"січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6, "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12}
    
    for page in [1, 2]:
        try:
            response = requests.get(f"{base_url}/allnews?page={page}", headers=headers, timeout=10)
            if response.status_code != 200: break
            soup = BeautifulSoup(response.text, "html.parser")
            for item in soup.select(".allnews-box, .the-news-container"):
                link_tag = item.find("a", href=True)
                if not link_tag: continue
                full_url = link_tag["href"] if link_tag["href"].startswith("http") else base_url + link_tag["href"]
                if full_url not in collected_links: collected_links.append(full_url)
        except Exception: break
    return collected_links

def parse_vse_rv_site(start_time, end_time):
    base_url = "https://vse.rv.ua"
    collected_links = []
    try:
        response = requests.get(f"{base_url}/strichka.html", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a", href=True):
            if anchor["href"].startswith("/article/"):
                collected_links.append(base_url + anchor["href"])
    except Exception: pass
    return list(set(collected_links))

def parse_radiotrek_site(start_time, end_time):
    base_url = "https://radiotrek.rv.ua"
    found_urls = []
    try:
        response = requests.get(f"{base_url}/news/", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a", href=re.compile(r"/news/.*_\d+\.html")):
            href = anchor["href"]
            found_urls.append(href if href.startswith("http") else base_url.rstrip("/") + href)
    except Exception: pass
    return list(set(found_urls))

def parse_suspilne_site(start_time, end_time):
    base_url = "https://suspilne.media"
    found_urls = []
    for page in range(1, 3):
        try:
            response = requests.get(f"{base_url}/rivne/?p={page}", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            for article in soup.find_all("article"):
                time_tag = article.find("time")
                if time_tag and time_tag.get("datetime"):
                    dt = parser.parse(time_tag["datetime"]).replace(tzinfo=None)
                    if start_time <= dt < end_time:
                        link = article.find("a", href=True)
                        if link: found_urls.append(base_url + link["href"])
        except Exception: break
    return list(set(found_urls))

def filter_pages_by_keyword(urls, keywords, start_time, end_time):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    filtered_results = []
    print(f"\n[Етап 2] Глибока фільтрація ({len(urls)} посилань)...")

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200: continue
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title else "Без заголовка"
            clean_text = soup.get_text(separator=" ").lower()
            
            for keyword in keywords:
                pattern = keyword if any(c in keyword for c in ".*{}[]()|+?^$") else r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, f"{title.lower()} {clean_text}", flags=re.UNICODE):
                    filtered_results.append({"url": url, "title": title, "matched_keyword": keyword})
                    break
        except Exception: 
            continue
    return filtered_results

if __name__ == "__main__":
    end_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)
    
    print("="*70 + "\n ПОЧАТОК МОНІТОРИНГУ ПРЕСИ\n" + "="*70)
    all_links = []
    
    # Збір посилань
    rss_urls = ["https://rivnepost.rv.ua/rss", "https://ogo.ua/feed", "https://7dniv.rv.ua/feed/", "https://rivne1.tv/rss", "https://itvmg.com/rss", "https://teza.tv/rss"]
    for url in rss_urls: all_links.extend(parse_rss_feed(url, start_time, end_time))
    for site in ["https://rivne.rayon.in.ua", "https://dubno.rayon.in.ua"]: all_links.extend(parse_rayon_site(site, start_time, end_time))
    all_links.extend(parse_radiotrek_site(start_time, end_time))
    all_links.extend(parse_suspilne_site(start_time, end_time))
    all_links.extend(parse_charivne_site(start_time, end_time))
    all_links.extend(parse_vse_rv_site(start_time, end_time))
    
    all_links = list(set(all_links))
    TARGET_NEWS_LIST = filter_pages_by_keyword(all_links, KEYWORDS_LIST, start_time, end_time)

    # Звіт
    print("\n" + "="*70 + f"\n ПІДСУМКОВИЙ ЗВІТ (Знайдено: {len(TARGET_NEWS_LIST)})\n" + "="*70)
    report_lines = [f"ЗВІТ ЗА ПЕРІОД: {start_time} -> {end_time}", f"Ключові слова: {', '.join(KEYWORDS_LIST)}", "-" * 60]
    
    if TARGET_NEWS_LIST:
        for idx, news in enumerate(TARGET_NEWS_LIST, 1):
            entry = f"{idx}. {news['title']}\n   URL: {news['url']}\n   Ключ: [{news['matched_keyword']}]\n"
            print(entry)
            report_lines.append(entry)
    else:
        msg = "За вказаний період публікацій не знайдено."
        print(msg)
        report_lines.append(msg)
        
    f_name = end_time.strftime("%y%m%d_report.txt")
    with open(f_name, "w", encoding="utf-8") as f: f.write("\n".join(report_lines))
    print(f"\n[Успішно] Звіт створено: {f_name}")
