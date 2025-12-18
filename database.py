import sqlite3
import uuid
from datetime import datetime, timedelta
from logger_config import logger

DB_NAME = "rssy2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    logger.info(f"Initializing database: {DB_NAME}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create feeds table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feeds (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        name TEXT,
        is_active BOOLEAN DEFAULT 1,
        last_fetched_at DATETIME
    )
    ''')
    
    # Create articles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        feed_id TEXT,
        title TEXT,
        original_url TEXT,
        published_at DATETIME,
        raw_content TEXT,
        summary TEXT,
        summarized_at DATETIME,
        image_url TEXT,
        is_top_selection BOOLEAN DEFAULT 0,
        FOREIGN KEY(feed_id) REFERENCES feeds(id)
    )
    ''')
    


    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # Create job_status table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_status (
        id TEXT PRIMARY KEY,
        status TEXT,
        progress_text TEXT,
        total_items INTEGER DEFAULT 0,
        processed_items INTEGER DEFAULT 0,
        updated_at DATETIME
    )
    ''')
    
    # Insert Clien placeholder feed if not exists
    cursor.execute("SELECT id FROM feeds WHERE id = 'clien-community'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO feeds (id, url, name, is_active, last_fetched_at) VALUES (?, ?, ?, ?, ?)",
            ('clien-community', 'https://www.clien.net/service/board/news', 'Clien News (Community)', 0, None)
        )

    conn.commit()
    conn.close()

def add_feed(url, name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    feed_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO feeds (id, url, name) VALUES (?, ?, ?)",
        (feed_id, url, name)
    )
    conn.commit()
    conn.close()
    return feed_id

def get_feeds(active_only=True):
    conn = get_db_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM feeds WHERE is_active = 1")
    else:
        cursor.execute("SELECT * FROM feeds")
    feeds = cursor.fetchall()
    conn.close()
    return feeds

def delete_feed(feed_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles WHERE feed_id = ?", (feed_id,))
    cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    conn.commit()
    conn.close()

def filter_new_urls(urls):
    if not urls:
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(urls))
    cursor.execute(f"SELECT original_url FROM articles WHERE original_url IN ({placeholders})", urls)
    existing_urls = {row['original_url'] for row in cursor.fetchall()}
    conn.close()
    return [url for url in urls if url not in existing_urls]

def save_article(feed_id, title, url, published_at, content, image_url=None, summary=None, is_top_selection=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if article already exists (by URL)
    cursor.execute("SELECT id FROM articles WHERE original_url = ?", (url,))
    if cursor.fetchone():
        conn.close()
        return None  # Already exists
        
    article_id = str(uuid.uuid4())
    # If summary is provided initially (e.g. from batch process)
    summarized_at = datetime.utcnow().isoformat() if summary else None
    
    cursor.execute(
        '''
        INSERT INTO articles (id, feed_id, title, original_url, published_at, raw_content, image_url, summary, summarized_at, is_top_selection)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (article_id, feed_id, title, url, published_at, content, image_url, summary, summarized_at, is_top_selection)
    )
    conn.commit()
    conn.close()
    return article_id

def update_article_summary(article_id, summary):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE articles SET summary = ?, summarized_at = ? WHERE id = ?",
        (summary, datetime.utcnow().isoformat(), article_id)
    )
    conn.commit()
    conn.close()

def get_recent_rss_articles(hours=24):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cursor.execute(
        '''
        SELECT a.*, f.name as feed_name 
        FROM articles a 
        JOIN feeds f ON a.feed_id = f.id 
        WHERE a.published_at > ? AND a.feed_id != 'clien-community'
        ORDER BY a.published_at DESC
        ''',
        (cutoff,)
    )
    articles = cursor.fetchall()
    conn.close()
    return articles

def get_clien_articles(limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch recent Clien articles
    cursor.execute(
        '''
        SELECT * FROM articles 
        WHERE feed_id = 'clien-community' 
        ORDER BY published_at DESC 
        LIMIT ?
        ''',
        (limit,)
    )
    articles = cursor.fetchall()
    conn.close()
    return articles

def cleanup_old_articles(days=7):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cursor.execute("DELETE FROM articles WHERE published_at < ?", (cutoff,))
    conn.commit()
    conn.close()

def clear_articles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles")
    conn.commit()
    conn.close()

def update_feed_last_fetched(feed_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE feeds SET last_fetched_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), feed_id)
    )
    conn.commit()
    conn.close()

def get_last_updated():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_fetched_at) as last_updated FROM feeds WHERE is_active = 1")
    result = cursor.fetchone()
    conn.close()
    if result and result['last_updated']:
        return result['last_updated']
    return None

def get_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result['value']
    return default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value))
    )
    conn.commit()
    conn.close()

def update_job_status(job_id, status, progress_text=None, total_items=None, processed_items=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    fields = ["status = ?", "updated_at = ?"]
    values = [status, datetime.utcnow().isoformat()]
    
    if progress_text is not None:
        fields.append("progress_text = ?")
        values.append(progress_text)
    if total_items is not None:
        fields.append("total_items = ?")
        values.append(total_items)
    if processed_items is not None:
        fields.append("processed_items = ?")
        values.append(processed_items)
        
    values.append(job_id)
    
    query = f"UPDATE job_status SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    
    if cursor.rowcount == 0:
        # Insert if not exists
        cursor.execute(
            "INSERT INTO job_status (id, status, progress_text, total_items, processed_items, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, status, progress_text or "", total_items or 0, processed_items or 0, datetime.utcnow().isoformat())
        )
        
    conn.commit()
    conn.close()

def get_job_status(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_status WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return dict(result)
    return None
