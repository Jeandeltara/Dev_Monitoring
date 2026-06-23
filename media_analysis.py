import os
import glob
import re
import requests
from bs4 import BeautifulSoup

# --- Parsers library section ---

def clean_content(element):
    """Utility to remove unwanted tags and extract text"""
    for tag in element(['script', 'style', 'noscript', 'iframe', 'ins', 'header', 'footer']):
        tag.extract()
    return element.get_text(separator=" ", strip=True)

def parse_itvmg(soup):
    container = soup.find('div', itemprop='articleBody')
    return clean_content(container) if container else ""

def parse_rivne1(soup):
    container = soup.find('div', class_='articleBody')
    return clean_content(container) if container else ""

def parse_rp_rv(soup):
    container = soup.find('div', class_='entry-content') # Check specific theme class
    return clean_content(container) if container else ""

def parse_rayon(soup):
    # Extracts the first article found in the feed
    news_items = soup.find_all('article')
    if news_items:
        return clean_content(news_items[0])
    return ""

def parse_teza(soup):
    container = soup.find('div', class_='post-content')
    return clean_content(container) if container else ""

def parse_horyn(soup):
    container = soup.find('div', class_='entry-content')
    return clean_content(container) if container else ""

def get_parser_by_url(url):
    """Router to select the appropriate parser function"""
    if 'itvmg.com' in url: return parse_itvmg
    if 'rivne1.tv' in url: return parse_rivne1
    if 'rp.rv.ua' in url: return parse_rp_rv
    if 'rayon.in.ua' in url: return parse_rayon
    if 'teza.tv' in url: return parse_teza
    if 'horyn.info' in url: return parse_horyn
    return None

# --- Main logic section ---

def get_latest_report():
    files = glob.glob("*_report.txt")
    return max(files, key=os.path.getctime) if files else None

def extract_urls(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return re.findall(r'Ссылка: (https?://\S+)', content)

def process_and_create_prompt():
    report_file = get_latest_report()
    if not report_file:
        print("No report file found.")
        return

    urls = extract_urls(report_file)
    articles_data = []

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            parser = get_parser_by_url(url)
            
            if parser:
                text = parser(soup)
                title = soup.title.string.strip() if soup.title else "No Title"
                articles_data.append(f"### Заголовок: {title}\nИсточник: {url}\nТекст: {text}\n---")
        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Merge with prompt.txt
    if os.path.exists('prompt.txt'):
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            base_prompt = f.read()
    else:
        base_prompt = "Проанализируй следующие статьи:"

    full_prompt = base_prompt + "\n\n" + "\n".join(articles_data)

    with open('prompt_w.txt', 'w', encoding='utf-8') as f:
        f.write(full_prompt)

if __name__ == "__main__":
    process_and_create_prompt()
