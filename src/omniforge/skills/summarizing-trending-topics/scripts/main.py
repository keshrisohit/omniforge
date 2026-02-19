import json
from scripts.fetch_twitter_trends import fetch_twitter_trends
from scripts.analyze_trend import analyze_trend

def main():
    try:
        trends = fetch_twitter_trends()
        analyzed_trends = []
        for trend in trends:
            summary, category, engagement_level = analyze_trend(trend['topic'])
            analyzed_trends.append({
                'topic': trend['topic'],
                'summary': summary,
                'category': category,
                'engagement_level': engagement_level
            })
        print(json.dumps(analyzed_trends, indent=4))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()