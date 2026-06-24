import os
import glob
import re
import datetime
import time
import requests
from bs4 import BeautifulSoup
from groq import Groq

# --- API Configuration ---
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Parser Functions ---
def clean_content(element):
    """
    Remove unnecessary tags and return clean text.
    Limits text length to ensure efficient token usage.
    """
    if not element:
        return ""
    for tag in element(['script', 'style', 'noscript', 'iframe', 'ins', 'header', 'footer', 'nav', 'aside', 'svg']):
        tag.extract()
    text = element.get_text(separator=" ", strip=True)
    return text[:2500]  # Cap content length to maintain stability

def parse_itvmg(soup): return clean_content(soup.find('div', itemprop='articleBody'))
def parse_rivne1(soup): return clean_content(soup.find('div', class_='articleBody'))
def parse_rp_rv(soup): return clean_content(soup.find('div', class_='entry-content'))
def parse_rayon(soup): return clean_content(soup.find('article'))
def parse_teza(soup): return clean_content(soup.find('div', class_='post-content'))
def parse_horyn(soup): return clean_content(soup.find('div', class_='entry-content'))

def parse_rivnepost(soup):
    content = soup.find('div', class_='article-body') or soup.find('article')
    return clean_content(content) if content else soup.get_text(separator=" ", strip=True)

def parse_rivnemedia(soup):
    content = soup.find('div', class_='news-content') or soup.find('div', class_='content')
    return clean_content(content) if content else soup.get_text(separator=" ", strip=True)

def get_parser_by_url(url):
    """Select the appropriate parser based on the domain."""
    if 'itvmg.com' in url: return parse_itvmg
    if 'rivne1.tv' in url: return parse_rivne1
    if 'rp.rv.ua' in url: return parse_rp_rv
    if 'rayon.in.ua' in url: return parse_rayon
    if 'teza.tv' in url: return parse_teza
    if 'horyn.info' in url: return parse_horyn
    if 'rivnepost.rv.ua' in url: return parse_rivnepost
    if 'rivne.media' in url: return parse_rivnemedia
    return None

# --- Core Logic ---
def send_to_ai(prompt_text):
    """Send individual article content to Groq for analysis."""
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt_text}],
        model="llama-3.3-70b-versatile",
    )
    return chat_completion.choices[0].message.content

def get_latest_report():
    """Find the most recent file ending with _report.txt."""
    files = glob.glob("*_report.txt")
    return max(files, key=os.path.getctime) if files else None

def extract_urls(file_path):
    """Extract all HTTP/HTTPS links from the report file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return re.findall(r'https?://\S+', content)

def process_and_create_report():
    report_file = get_latest_report()
    if not report_file:
        print("No report file found.")
        return

    urls = extract_urls(report_file)
    print(f"Found {len(urls)} links to process.")
    
    date_str = datetime.datetime.now().strftime("%y%m%d")
    output_filename = f"{date_str}_analysis_report.txt"
    
    # Load analysis instructions
    base_prompt = "Analyze this article, specifically looking for mentions of 'Дубно' or local context:"
    if os.path.exists('prompt.txt'):
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            base_prompt = f.read()

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(f"MEDIA ANALYSIS REPORT - {datetime.datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("="*60 + "\n\n")

        for url in urls:
            try:
                print(f"Processing: {url}")
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, timeout=15, headers=headers)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                parser = get_parser_by_url(url)
                text = parser(soup) if parser else clean_content(soup.find('body'))
                title = soup.title.string.strip() if soup.title else "No Title"
                
                if len(text) > 100:
                    full_prompt = f"{base_prompt}\n\nTitle: {title}\nContent: {text}"
                    analysis = send_to_ai(full_prompt)
                    
                    f.write(f"ARTICLE: {title}\n")
                    f.write(f"URL: {url}\n")
                    f.write(f"ANALYSIS:\n{analysis}\n")
                    f.write("-" * 30 + "\n\n")
                    
                    # Rate limiting: wait 1 second between API calls
                    time.sleep(1)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                f.write(f"Error processing {url}: {e}\n\n")

if __name__ == "__main__":
    process_and_create_report()
