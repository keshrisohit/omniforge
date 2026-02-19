```markdown
# Google Docs Summarizer

This script creates concise summaries of Google Docs by extracting key points, main ideas, and essential information.

## Usage

```bash
# Basic usage
python {{baseDir}}/scripts/summarize_google_doc.py --doc-id <GOOGLE_DOC_ID> --output summary.txt

# With custom sentence limit
python {{baseDir}}/scripts/summarize_google_doc.py --doc-id <GOOGLE_DOC_ID> --output summary.txt --max-sentences 15
```

## Setup

1. **Enable Google Docs API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable "Google Docs API"
   - Create credentials (Service Account key)
   - Download JSON credentials file

2. **Set environment variables**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
export GOOGLE_DOC_ID="your-google-doc-id"  # Optional, can also use --doc-id flag
```

3. **Install dependencies**
```bash
pip install -r {{baseDir}}/requirements.txt
```

## Parameters

- `--doc-id`: Google Doc ID to summarize (can also set GOOGLE_DOC_ID environment variable)
- `--output`: Output file path for summary
- `--max-sentences`: Maximum sentences in summary (default: 10)

## Requirements

- Python 3.9+
- Google Cloud service account with Google Docs API access
- Internet connection for API calls

## Error Handling

The script includes comprehensive error handling for:
- Missing credentials
- Invalid document IDs
- API authentication failures
- Network connectivity issues
- File I/O errors
```