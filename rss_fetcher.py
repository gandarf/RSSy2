import feedparser
from datetime import datetime
import calendar
from time import mktime
from bs4 import BeautifulSoup

def parse_date(entry):
    if hasattr(entry, 'published_parsed'):
        return datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed)).isoformat()
    if hasattr(entry, 'updated_parsed'):
        return datetime.utcfromtimestamp(calendar.timegm(entry.updated_parsed)).isoformat()
    return datetime.utcnow().isoformat()

def clean_html(text):
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, 'html.parser')
        # preserve some structure or just get text? 
        # Requirement: "HTML 부분이 나오지 않게" -> Just text is safest and best for tokens
        return soup.get_text(separator=' ', strip=True) 
    except Exception:
        return text

def fetch_feed(feed_url):
    feed = feedparser.parse(feed_url)
    entries = []
    
    for entry in feed.entries:
        # Extract image if available
        image_url = None
        if 'media_content' in entry:
            image_url = entry.media_content[0]['url']
        elif 'media_thumbnail' in entry:
            image_url = entry.media_thumbnail[0]['url']
            
        content = ""
        if 'content' in entry:
            content = entry.content[0].value
        elif 'summary' in entry:
            content = entry.summary
        elif 'description' in entry:
            content = entry.description
        
        # Clean HTML from content
        content = clean_html(content)
            
        entries.append({
            'title': entry.title,
            'link': entry.link,
            'published_at': parse_date(entry),
            'content': content,
            'image_url': image_url
        })
        
    return {
        'title': feed.feed.get('title', 'Unknown Feed'),
        'entries': entries
    }

import aiohttp
import asyncio

async def fetch_feed_async(feed_url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(feed_url) as response:
                content = await response.text()
                # Run feedparser in a thread executor as it is CPU bound parsing
                feed = await asyncio.to_thread(feedparser.parse, content)
                
                entries = []
                for entry in feed.entries:
                    # Extract image if available
                    image_url = None
                    if 'media_content' in entry:
                        image_url = entry.media_content[0]['url']
                    elif 'media_thumbnail' in entry:
                        image_url = entry.media_thumbnail[0]['url']
                        
                    content_text = ""
                    if 'content' in entry:
                        content_text = entry.content[0].value
                    elif 'summary' in entry:
                        content_text = entry.summary
                    elif 'description' in entry:
                        content_text = entry.description
                    
                    # Clean HTML from content
                    content_text = clean_html(content_text)
                        
                    entries.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published_at': parse_date(entry),
                        'content': content_text,
                        'image_url': image_url
                    })
                    
                return {
                    'title': feed.feed.get('title', 'Unknown Feed'),
                    'entries': entries
                }
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
            return {'title': 'Error', 'entries': []}
