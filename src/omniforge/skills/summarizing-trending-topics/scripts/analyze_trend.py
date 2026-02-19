import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer
import nltk
nltk.download('punkt')
nltk.download('stopwords')

def analyze_trend(topic):
    """
    Analyze a trending topic.
    :param topic: Topic to analyze.
    :return: Summary, category, engagement level.
    """
    url = f"https://www.google.com/search?q={topic}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    summary = ""
    category = ""
    engagement_level = ""
    sentences = sent_tokenize(soup.get_text())
    stop_words = set(stopwords.words('english'))
    stemmer = PorterStemmer()
    for sentence in sentences:
        words = word_tokenize(sentence)
        filtered_words = [stemmer.stem(word.lower()) for word in words if word.isalpha() and word.lower() not in stop_words]
        if len(filtered_words) > 5:
            summary += sentence + " "
            break
    if "news" in topic.lower() or "update" in topic.lower():
        category = "News"
    elif "movie" in topic.lower() or "show" in topic.lower():
        category = "Entertainment"
    elif "sport" in topic.lower() or "game" in topic.lower():
        category = "Sports"
    else:
        category = "Other"
    return summary, category, engagement_level

def main():
    try:
        topic = input("Enter topic: ")
        summary, category, engagement_level = analyze_trend(topic)
        print(f"Summary: {summary}")
        print(f"Category: {category}")
        print(f"Engagement Level: {engagement_level}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()