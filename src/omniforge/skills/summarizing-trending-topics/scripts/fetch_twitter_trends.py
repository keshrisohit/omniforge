import requests
from bs4 import BeautifulSoup
import time

def fetch_twitter_trends():
    """
    Fetch trending topics from Twitter.
    :return: List of trending topics with metadata.
    """
    url = "https://twitter.com/explore/trends"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    trends = soup.find_all('div', {'data-testid': 'trend'})
    trending_topics = []
    for trend in trends:
        topic = trend.find('div', {'data-testid': 'trendName'}).text.strip()
        query = trend.find('a')['href'].split('?')[1].split('&')[0].split('=')[1]
        trending_topics.append({
            'topic': topic,
            'query': query
        })
    return trending_topics

def main():
    try:
        trends = fetch_twitter_trends()
        print(trends)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()