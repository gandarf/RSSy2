import sqlite3
import uuid
from datetime import datetime, timedelta

DB_NAME = "rssy2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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
        FOREIGN KEY(feed_id) REFERENCES feeds(id)
    )
    ''')
    
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

def save_article(feed_id, title, url, published_at, content, image_url=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if article already exists (by URL)
    cursor.execute("SELECT id FROM articles WHERE original_url = ?", (url,))
    if cursor.fetchone():
        conn.close()
        return None  # Already exists
        
    article_id = str(uuid.uuid4())
    cursor.execute(
        '''
        INSERT INTO articles (id, feed_id, title, original_url, published_at, raw_content, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (article_id, feed_id, title, url, published_at, content, image_url)
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

def get_recent_articles(hours=24):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    cursor.execute(
        '''
        SELECT a.*, f.name as feed_name 
        FROM articles a 
        JOIN feeds f ON a.feed_id = f.id 
        WHERE a.published_at > ? 
        ORDER BY a.published_at DESC
        ''',
        (cutoff,)
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
