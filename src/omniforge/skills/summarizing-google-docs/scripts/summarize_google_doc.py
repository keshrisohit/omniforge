#!/usr/bin/env python3
"""
Google Docs Summarizer

Creates concise summaries of Google Docs by extracting key points, main ideas, and essential information.

Usage:
    python scripts/summarize_google_doc.py --doc-id <GOOGLE_DOC_ID> --output summary.txt

Requirements:
    - Python 3.9+
    - google-api-python-client
    - google-auth-httplib2
    - google-auth-oauthlib
    - requests
    - nltk (for text processing)

Environment Variables:
    - GOOGLE_APPLICATION_CREDENTIALS: Path to Google Cloud service account credentials JSON file
    - GOOGLE_DOC_ID: (Optional) Default Google Doc ID to summarize

"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Third-party imports
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import nltk
    from nltk.tokenize import sent_tokenize
except ImportError as e:
    logging.error(f"Missing required package: {e}. Install with: pip install -r requirements.txt")
    sys.exit(1)

# Download NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class GoogleDocsSummarizer:
    """Handles Google Docs summarization."""

    def __init__(self, credentials_path: str):
        """Initialize the summarizer with Google credentials."""
        self.credentials_path = credentials_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Docs API."""
        try:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/documents.readonly']
            )
            service = build('docs', 'v1', credentials=credentials)
            logger.info("Successfully authenticated with Google Docs API")
            return service
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            sys.exit(1)

    def get_document_content(self, doc_id: str) -> str:
        """Retrieve the full text content of a Google Doc."""
        try:
            doc = self.service.documents().get(documentId=doc_id).execute()
            content = self._extract_text(doc)
            logger.info(f"Retrieved {len(content)} characters from document")
            return content
        except HttpError as e:
            logger.error(f"Failed to retrieve document: {e}")
            sys.exit(1)

    def _extract_text(self, doc: Dict[str, Any]) -> str:
        """Extract plain text from Google Docs structure."""
        text = []
        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                for segment in element['paragraph'].get('elements', []):
                    if 'textRun' in segment:
                        text.append(segment['textRun'].get('content', ''))
        return ''.join(text)

    def summarize_text(self, text: str, max_sentences: int = 10) -> str:
        """Create a summary by extracting key sentences."""
        sentences = sent_tokenize(text)
        if len(sentences) <= max_sentences:
            return text

        # Simple heuristic: take first and last sentences + middle key points
        summary = [sentences[0]]  # First sentence
        step = max(1, len(sentences) // (max_sentences - 2))
        for i in range(1, len(sentences) - 1, step):
            summary.append(sentences[i])
        summary.append(sentences[-1])  # Last sentence

        return ' '.join(summary[:max_sentences])

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Summarize Google Docs")
    parser.add_argument("--doc-id", required=False, help="Google Doc ID to summarize")
    parser.add_argument("--output", required=True, help="Output file path for summary")
    parser.add_argument("--max-sentences", type=int, default=10, help="Maximum sentences in summary")

    try:
        args = parser.parse_args()

        # Get credentials path from environment
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path or not Path(credentials_path).exists():
            logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set or file not found")
            sys.exit(1)

        # Get document ID (from args or environment)
        doc_id = args.doc_id or os.getenv('GOOGLE_DOC_ID')
        if not doc_id:
            logger.error("Google Doc ID required. Use --doc-id or set GOOGLE_DOC_ID environment variable")
            sys.exit(1)

        # Initialize summarizer
        summarizer = GoogleDocsSummarizer(credentials_path)

        # Retrieve and summarize document
        logger.info(f"Retrieving document: {doc_id}")
        document_text = summarizer.get_document_content(doc_id)

        logger.info("Generating summary...")
        summary = summarizer.summarize_text(document_text, args.max_sentences)

        # Save summary
        output_path = Path(args.output)
        output_path.write_text(summary)
        logger.info(f"Summary saved to: {output_path}")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()