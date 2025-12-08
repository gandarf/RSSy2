import feedparser
from datetime import datetime
from time import mktime

def parse_date(entry):
    if hasattr(entry, 'published_parsed'):
        return datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()
    if hasattr(entry, 'updated_parsed'):
        return datetime.fromtimestamp(mktime(entry.updated_parsed)).isoformat()
    return datetime.utcnow().isoformat()

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
