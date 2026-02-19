---
name: summarizing-tweets
description: She condenses trending Twitter posts into concise summaries, useful when users need to quickly inform themselves of breaking news and announcements, and updates every hour or when a post reaches 1000 likes.
---
# summarizing-tweets
## Quick start
Use this skill to condense trending Twitter posts into concise summaries, updating every hour or when a post reaches 1000 likes.

## Core instructions
Summarize tweets by following these steps:
1. Identify the main topic of the tweet
2. Remove unnecessary words and phrases
3. Condense the tweet into a concise summary
4. Update summaries every hour or when a tweet reaches 1000 likes

## Examples
- Input: 'Breaking: New COVID variant detected in the US', Output: 'A new COVID variant has been detected in the US'
- Input: 'Just announced: iPhone 14 release date', Output: 'The iPhone 14 release date has been announced'

## Edge cases
- If a tweet is too short, use the original text as the summary
- If a tweet contains multiple topics, focus on the main topic
- Handle tweets with hashtags, mentions, and URLs by removing them when necessary

## External knowledge
For detailed information on Twitter API and natural language processing, read {baseDir}/references/twitter-api.md and {baseDir}/references/nlp.md.

## Triggers and contexts
Update summaries:
- Every hour
- When a new tweet reaches 1000 likes

Use these triggers to ensure summaries are up-to-date and relevant. 

Note: The original 'allowed-tools' field has been removed from the frontmatter as it contained an invalid tool specification and was not in line with the critical rules provided. If a valid tool is required for this skill, it should be included in the skill's description or body, following the specified guidelines.