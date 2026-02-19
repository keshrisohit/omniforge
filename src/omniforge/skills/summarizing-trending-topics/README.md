# Summarizing Trending Topics
This skill fetches trending topics from Twitter, analyzes each topic, generates a concise summary, and categorizes the topic.

## Installation
To use this skill, install the required packages by running:
```bash
pip install -r requirements.txt
```

## Usage
To run the skill, execute:
```bash
python scripts/main.py
```

## Configuration
You can configure the skill by modifying the `scripts/fetch_twitter_trends.py` and `scripts/analyze_trend.py` files.

## Output
The skill outputs a JSON object with the following structure:
```json
[
    {
        "topic": "Topic 1",
        "summary": "Summary of Topic 1",
        "category": "Category of Topic 1",
        "engagement_level": "Engagement level of Topic 1"
    },
    {
        "topic": "Topic 2",
        "summary": "Summary of Topic 2",
        "category": "Category of Topic 2",
        "engagement_level": "Engagement level of Topic 2"
    }
]
```