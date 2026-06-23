import os
import glob
import re
import datetime
import requests
from bs4 import BeautifulSoup
from google import genai

# --- Настройка API ---
# Используем новую клиентскую библиотеку google-genai
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

# --- Parsers library ---
def clean_content(element):
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
    container = soup.find('div', class_='entry-content')
    return clean_content(container) if container else ""

def parse_rayon(soup):
    news_items = soup.find_all('article')
    return clean_content(news_items[0]) if news_items else ""

def parse_teza(soup):
    container = soup.find('div', class_='post-content')
    return clean_content(container) if container else ""

def parse_horyn(soup):
    container = soup.find('div', class_='entry-content')
    return clean_content(container) if container else ""

def get_parser_by_url(url):
    if 'itvmg.com' in url: return parse_itvmg
    if 'rivne1.tv' in url: return parse_rivne1
    if 'rp.rv.ua' in url: return parse_rp_rv
    if 'rayon.in.ua' in url: return parse_rayon
    if 'teza.tv' in url: return parse_teza
    if 'horyn.info' in url: return parse_horyn
    return None

# --- Main logic ---
def send_to_gemini(prompt_text):
    # Используем самую актуальную модель
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt_text,
    )
    return response.text

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

    if os.path.exists('prompt.txt'):
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            base_prompt = f.read()
    else:
        base_prompt = "Проанализируй следующие статьи:"

    # Замена ключевого слова (если оно есть в prompt.txt)
    full_prompt = (base_prompt + "\n\n" + "\n".join(articles_data)).replace('redneck', 'ВАШЕ_КЛЮЧЕВОЕ_СЛОВО')

    with open('prompt_w.txt', 'w', encoding='utf-8') as f:
        f.write(full_prompt)

    # Обработка через Gemini
    analysis_result = send_to_gemini(full_prompt)
    
    date_str = datetime.datetime.now().strftime("%y%m%d")
    with open(f"{date_str}_media_analysis.txt", 'w', encoding='utf-8') as f:
        f.write(analysis_result)

if __name__ == "__main__":
    process_and_create_prompt()
