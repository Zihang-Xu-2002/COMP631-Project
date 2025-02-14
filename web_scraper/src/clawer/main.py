import requests
from bs4 import BeautifulSoup
import json

class BaseScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com' 
        })

    def fetch_content(self, url):
        """_summary_: Fetch content from a URL

        Args:
            url (string): url of the page

        Returns:
            _type_: _description_
        """
        try:
            response = self.session.get(url)
            response.raise_for_status()  # 检查请求是否成功
            return response.content
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_html(self, html_content):
        """_summary_: Parse HTML content

        Args:
            html_content (_type_): _description_

        Returns:
            _type_: _description_
        """
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            print(f"Error parsing HTML content: {e}")
            return None

    def save_to_json(self, data, filename, doc_type):
        try:
            structured_data = {
                'type': doc_type,
                'data': data
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=4)
            print(f"Data successfully saved to {filename}")
        except Exception as e:
            print(f"Error saving data to {filename}: {e}")

class WikipediaScraper(BaseScraper):
    def __init__(self):
        super().__init__('https://en.wikipedia.org')

    def scrape_page(self, page_name):
        url = f'{self.base_url}/wiki/{page_name}'
        html_content = self.fetch_content(url)
        if html_content is None:
            return None
        
        soup = self.parse_html(html_content)
        if soup is None:
            return None
        
        try:
            page_title = soup.find('h1', id='firstHeading').text
            paragraphs = [p.text.strip() for p in soup.find_all('p')]
            
            data = {
                'title': page_title,
                'paragraphs': paragraphs
            }
            return data
        except AttributeError as e:
            print(f"Error extracting data from {url}: {e}")
            return None

class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__('https://www.indeed.com')

    def scrape_jobs(self, query):
        url = f'{self.base_url}/jobs?q={query}'
        html_content = self.fetch_content(url)
        if html_content is None:
            return None
        
        soup = self.parse_html(html_content)
        if soup is None:
            return None
        
        try:
            job_titles = [h2.text.strip() for h2 in soup.find_all('h2', class_='jobTitle')] # firstly try to get the job title
            return job_titles
        except AttributeError as e:
            print(f"Error extracting data from {url}: {e}")
            return None

# simple test
if __name__ == '__main__':
    # scrape wikipedia
    wiki_scraper = WikipediaScraper()
    wiki_data = wiki_scraper.scrape_page('Web_scraping')
    if wiki_data:
        print('Wikipedia Page Title:', wiki_data['title'])
        print('Wikipedia Page Paragraphs:', len(wiki_data['paragraphs']))
        wiki_scraper.save_to_json(wiki_data, './web_scraper/data/wikipedia_data.json', 'knowledge article')
    else:
        print('Failed to scrape Wikipedia page.')

    # scrape indeed
    indeed_scraper = IndeedScraper()
    job_titles = indeed_scraper.scrape_jobs('software+engineer')
    if job_titles:
        print('Indeed Job Titles:', job_titles)
        indeed_scraper.save_to_json({'job_titles': job_titles}, 'indeed_jobs.json', 'job description')
    else:
        print('Failed to scrape Indeed job listings.')