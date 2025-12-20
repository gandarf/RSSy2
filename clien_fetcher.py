import aiohttp
from bs4 import BeautifulSoup
import asyncio

CLIEN_BASE_URL = "https://www.clien.net"
CLIEN_NEWS_URL = "https://www.clien.net/service/board/news"

async def fetch_clien_list():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CLIEN_NEWS_URL, headers=headers, timeout=10) as response:
                if response.status != 200:
                    print(f"Failed to fetch Clien list: {response.status}")
                    return []
                
                html = await response.text()
                return await asyncio.to_thread(_parse_clien_list, html)
    except Exception as e:
        print(f"Error fetching Clien list: {e}")
        return []

def _parse_clien_list(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    # User specified class 'list_title' for title/link and 'rSymph05' for comment count
    # Inspecting typical Clien structure (based on user request):
    # The list items are usually rows. We need to find the specific elements.
    # We will look for elements with class 'list_title' which usually contains the <a> tag.
    
    # Note: 'list_title' might be on the <a> tag itself or a wrapper.
    # Let's find all elements with class 'list_title'.
    
    titles = soup.find_all(class_='list_title')
    
    for item in titles:
        try:
            # The item itself might be the link or contain it.
            # In Clien, .list_title is usually a span or div containing the <a> tag.
            # Or it might be the a tag with class list_subject?
            # User said "list_title 와 rSymph05 class를 읽어".
            # Let's assume list_title contains the text and the link.
            
            link_tag = item.find('a') if item.name != 'a' else item
            if not link_tag and item.has_attr('href'):
                link_tag = item
            
            if not link_tag:
                # Try finding parent if list_title is just text span?
                # Let's assume standard structure: <div class="list_title"><a href="...">Title</a></div>
                # If item is the container.
                link_tag = item.find('a')
            
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get('href')
            
            if not href:
                continue
                
            full_url = CLIEN_BASE_URL + href if href.startswith('/') else href
            
            # Comment count. It is usually inside the list item row, not necessarily inside list_title.
            # We need the parent row to find the sibling 'rSymph05'.
            # Let's try to find the row container.
            # Usually .list_item.symph_row
            
            # Heuristic: verify if rSymph05 is inside list_title or sibling.
            # On Clien, the comment count is often inside the title component or separate column.
            # Let's try to find 'rSymph05' within the same row container.
            
            # Assuming 'item' is a descendant of the row.
            # calculate comment count
            comment_count = 0
            
            # Traverse up to find a container that might hold the comment count
            # OR, if the user meant that rSymph05 is INSIDE list_title (common in mobile views or specific layouts).
            
            comment_span = item.find(class_='rSymph05')
            if not comment_span:
                # Try siblings or parent's siblings?
                # This is risky without seeing HTML.
                # However, usually comment count is separate.
                # Let's try looking for the row.
                row = item.find_parent(class_='list_item')
                if row:
                    comment_span = row.find(class_='rSymph05')
            
            if comment_span:
                 try:
                     comment_count = int(comment_span.get_text(strip=True))
                 except:
                     pass
            
            results.append({
                'title': title,
                'link': full_url,
                'comment_count': comment_count,
                # Use current time as placeholder for published_at as checking detail page for every item is expensive
                # or we can parse it if available in list. Clien list usually has timestamp.
                # But user didn't specify. We'll use None or specific logic later.
                'published_at': None 
            })
            
        except Exception as e:
            continue
            
    return results

async def fetch_clien_article_full(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return ""
                html = await response.text()
                return await asyncio.to_thread(_extract_clien_content, html)
    except Exception as e:
        print(f"Error fetching Clien article {url}: {e}")
        return ""

def _extract_clien_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Extract main article content
    article = soup.find(class_='post_article')
    if not article:
        article = soup.find(class_='content') # Fallback
        
    content_text = ""
    if article:
        content_text = article.get_text(separator=' ', strip=True)
    
    # 2. Extract comments from .comment_view
    comments_section = soup.find(class_='comment_view')
    extracted_comments = []
    if comments_section:
        comment_items = comments_section.find_all(class_='comment_row')
        if not comment_items:
            # Fallback: just get the whole section text if no rows found
            text = comments_section.get_text(separator=' ', strip=True)
            if text:
                extracted_comments.append(text)
        else:
            for row in comment_items:
                comment_content = row.find(class_='comment_content')
                if comment_content:
                    extracted_comments.append(comment_content.get_text(separator=' ', strip=True))
    
    return {
        'body': content_text,
        'comments': extracted_comments[:20]  # Limit to top 20 comments
    }
