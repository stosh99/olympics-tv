#!/usr/bin/env python3
"""
Source Scraper - Takes resolved queries from source_resolver,
searches via SerpAPI, fetches full articles, and builds a
consolidated source file for the commentary writer.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import requests
import logging
import time
import re
from datetime import datetime
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SERPAPI_KEY = os.getenv('SERPAPI_KEY')
SERPAPI_URL = "https://serpapi.com/search"

# Domains to skip (paywalls, low-quality, or non-article pages)
SKIP_DOMAINS = {
    'youtube.com', 'twitter.com', 'x.com', 'facebook.com',
    'instagram.com', 'tiktok.com', 'reddit.com',
    'pinterest.com', 'linkedin.com',
}

# Max articles per search query
MAX_ARTICLES_PER_QUERY = 3
# Max total articles per event
MAX_TOTAL_ARTICLES = 12
# Request timeout for article fetching
FETCH_TIMEOUT = 15
# Delay between fetches to be polite
FETCH_DELAY = 1.0


def search_serpapi(query, num_results=5):
    """Run a search query via SerpAPI, return organic results."""
    if not SERPAPI_KEY or SERPAPI_KEY == 'your_key_here':
        logger.error("SERPAPI_KEY not configured")
        return []

    params = {
        'engine': 'google',
        'q': query,
        'api_key': SERPAPI_KEY,
        'num': num_results,
        'gl': 'us',
        'hl': 'en',
    }

    try:
        resp = requests.get(SERPAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get('organic_results', [])
    except Exception as e:
        logger.error(f"SerpAPI search failed for '{query}': {e}")
        return []



def fetch_article_text(url):
    """Fetch and extract article text from a URL using newspaper3k or fallback."""
    domain = urlparse(url).netloc.replace('www.', '')
    if domain in SKIP_DOMAINS:
        logger.debug(f"Skipping social/video domain: {domain}")
        return None

    try:
        # Try newspaper3k first (best article extraction)
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        
        text = article.text.strip()
        if len(text) < 200:
            logger.debug(f"Article too short ({len(text)} chars): {url}")
            return None
        
        return {
            'url': url,
            'domain': domain,
            'title': article.title or '',
            'text': text,
            'authors': article.authors or [],
            'publish_date': str(article.publish_date) if article.publish_date else None,
        }
    except ImportError:
        # Fallback: raw requests + basic extraction
        return _fetch_article_fallback(url, domain)
    except Exception as e:
        logger.warning(f"newspaper3k failed for {url}: {e}")
        return _fetch_article_fallback(url, domain)


def _fetch_article_fallback(url, domain):
    """Fallback article fetcher using requests + basic HTML stripping."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        
        # Basic HTML to text
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Remove script/style/nav elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # Try to find article body
        article_body = (
            soup.find('article') or
            soup.find('div', class_=re.compile(r'article|story|content|post', re.I)) or
            soup.find('main') or
            soup.body
        )
        
        if not article_body:
            return None
        
        # Extract paragraphs
        paragraphs = article_body.find_all('p')
        text = '\n\n'.join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30)
        
        if len(text) < 200:
            return None
        
        title = soup.title.string.strip() if soup.title and soup.title.string else ''
        
        return {
            'url': url,
            'domain': domain,
            'title': title,
            'text': text,
            'authors': [],
            'publish_date': None,
        }
    except Exception as e:
        logger.warning(f"Fallback fetch failed for {url}: {e}")
        return None



def scrape_for_event(resolved_data):
    """
    Main scraping function. Takes output from source_resolver.resolve_sources(),
    searches for each query, fetches articles, deduplicates, returns consolidated data.
    """
    if not resolved_data:
        return None

    event_label = resolved_data['event_label']
    logger.info(f"Scraping sources for: {event_label}")

    all_articles = []
    seen_urls = set()
    seen_domains = set()

    for q in resolved_data['queries']:
        query_text = q['query']
        query_type = q['type']
        logger.info(f"  Searching [{query_type}]: {query_text}")

        results = search_serpapi(query_text)
        articles_from_query = 0

        for r in results:
            if articles_from_query >= MAX_ARTICLES_PER_QUERY:
                break
            if len(all_articles) >= MAX_TOTAL_ARTICLES:
                break

            url = r.get('link', '')
            domain = urlparse(url).netloc.replace('www.', '')

            # Skip duplicates and already-seen domains (prefer diversity)
            if url in seen_urls:
                continue
            if domain in seen_domains:
                # Allow max 2 articles from same domain (e.g., olympics.com)
                domain_count = sum(1 for a in all_articles if a['domain'] == domain)
                if domain_count >= 2:
                    continue

            seen_urls.add(url)
            logger.info(f"    Fetching: {url}")
            
            time.sleep(FETCH_DELAY)
            article = fetch_article_text(url)
            
            if article:
                article['query_type'] = query_type
                article['query_reason'] = q.get('reason', '')
                article['snippet'] = r.get('snippet', '')
                all_articles.append(article)
                seen_domains.add(domain)
                articles_from_query += 1
                logger.info(f"    + Got {len(article['text'])} chars from {domain}")
            else:
                logger.info(f"    - Failed or too short: {domain}")

    logger.info(f"Scraping complete: {len(all_articles)} articles for {event_label}")
    return all_articles


def build_consolidated_file(resolved_data, articles):
    """
    Build the consolidated source file that gets passed to the commentary writer.
    Results first (ground truth), then all sources labeled.
    """
    lines = []

    # === EVENT CONTEXT ===
    lines.append("=== EVENT CONTEXT ===")
    lines.append(f"Event: {resolved_data['event_label']}")
    lines.append(f"Date: {resolved_data['event_date']}")
    lines.append(f"Discipline: {resolved_data['discipline']}")
    lines.append(f"Medal Event: {'Yes' if resolved_data['is_medal_event'] else 'No'}")
    lines.append("")

    # === RESULTS (ground truth from DB) ===
    lines.append("=== RESULTS (from database - ground truth) ===")
    for r in resolved_data['results']:
        medal = ""
        if r.get('medal_type'):
            medal_map = {'ME_GOLD': 'Gold', 'ME_SILVER': 'Silver', 'ME_BRONZE': 'Bronze'}
            medal = f" [{medal_map.get(r['medal_type'], r['medal_type'])}]"
        
        pos = ""
        if r.get('position'):
            pos = f"#{r['position']}"
        elif r.get('wlt'):
            wlt_map = {'W': 'Winner', 'L': 'Loser', 'T': 'Tie'}
            pos = wlt_map.get(r['wlt'], r['wlt'])
        
        mark = r.get('mark', '')
        lines.append(f"  {pos} {r['name']} ({r['noc']}) - {mark}{medal}")
    lines.append("")


    # === SOURCES ===
    for i, article in enumerate(articles, 1):
        lines.append(f"=== SOURCE {i}: {article['domain']} ===")
        lines.append(f"URL: {article['url']}")
        lines.append(f"Title: {article['title']}")
        if article.get('authors'):
            lines.append(f"Authors: {', '.join(article['authors'])}")
        if article.get('publish_date'):
            lines.append(f"Published: {article['publish_date']}")
        lines.append(f"Found via: {article['query_type']} search - {article['query_reason']}")
        lines.append(f"Snippet: {article['snippet']}")
        lines.append("---")
        lines.append(article['text'])
        lines.append("")

    if not articles:
        lines.append("=== NO SOURCES FOUND ===")
        lines.append("No articles could be fetched for this event.")
        lines.append("")

    return '\n'.join(lines)


def scrape_event(event_unit_code):
    """
    End-to-end: resolve sources, search, fetch, build consolidated file.
    Returns (consolidated_text, articles_metadata, resolved_data) or None on failure.
    """
    from source_resolver import resolve_sources

    resolved = resolve_sources(event_unit_code)
    if not resolved:
        logger.error(f"Could not resolve sources for {event_unit_code}")
        return None

    articles = scrape_for_event(resolved)
    consolidated = build_consolidated_file(resolved, articles or [])

    # Build metadata for DB storage
    sources_meta = [{
        'url': a['url'],
        'domain': a['domain'],
        'title': a['title'],
        'query_type': a['query_type'],
        'char_count': len(a['text']),
    } for a in (articles or [])]

    return {
        'consolidated_text': consolidated,
        'sources_metadata': sources_meta,
        'resolved_data': resolved,
        'article_count': len(articles or []),
    }


if __name__ == '__main__':
    import sys
    
    code = sys.argv[1] if len(sys.argv) > 1 else 'SSKW500M--------------FNL-000100'
    
    result = scrape_event(code)
    if not result:
        print("Scraping failed")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Scraped {result['article_count']} articles")
    print(f"Consolidated file: {len(result['consolidated_text'])} chars")
    print(f"\nSources:")
    for s in result['sources_metadata']:
        print(f"  [{s['query_type']}] {s['domain']}: {s['title']} ({s['char_count']} chars)")
    
    # Save consolidated file for inspection
    outfile = f"scraped_{code[:20]}.txt"
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(result['consolidated_text'])
    print(f"\nSaved to: {outfile}")
