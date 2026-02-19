---
name: summarizing-trending-topics
description: Analyzes and summarizes trending topics from Twitter or the web, providing concise overviews and categorization. Use when needing to quickly understand current popular discussions, such as researching social media trends or staying updated on news and events.
---
# summarizing-trending-topics

## Quick start
Use this skill to analyze and summarize trending topics from Twitter or the web, providing concise overviews and categorization. Trigger this skill when needing to quickly understand current popular discussions.

## Core instructions
To summarize trending topics:
1. Fetch trending topics from Twitter API or through web scraping.
2. Analyze each trending topic to understand its context.
3. Generate a concise summary of what each topic is about.
4. Categorize the topic (e.g., news, entertainment, sports) and determine its engagement level if available.

## Examples
- Input: Request to summarize trending topics
- Output:
  - Topic: #COVID19
  - Summary: Discussions and updates about the COVID-19 pandemic.
  - Category: News
  - Engagement: High
- Input: Request to summarize trending topics related to sports
- Output:
  - Topic: #NBA
  - Summary: Latest news, scores, and analysis from the NBA.
  - Category: Sports
  - Engagement: Medium

## Workflow
Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Fetch trending topics
- [ ] Step 2: Analyze each topic
- [ ] Step 3: Generate summary and categorize
- [ ] Step 4: Determine engagement level
```
### Step 1: Fetch trending topics
Use Twitter API or web scraping to fetch current trending topics.

### Step 2: Analyze each topic
Read and analyze the content related to each trending topic to understand its context.

### Step 3: Generate summary and categorize
Create a concise summary for each topic and categorize it based on its content.

### Step 4: Determine engagement level
If available, determine the engagement level of each topic.

## Edge cases
- If a topic spans multiple categories, pick the most dominant one or use "Mixed".
- If engagement data is unavailable, mark as "Unknown".
- If scraping fails, provide an error message and suggest alternatives.
- If a topic is not clearly definable, provide a summary based on available information and categorize as "Miscellaneous" if necessary.