from apscheduler.schedulers.background import BackgroundScheduler
from database import get_feeds, save_article, update_article_summary, cleanup_old_articles
from rss_fetcher import fetch_feed
from summarizer import GeminiSummarizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
summarizer = GeminiSummarizer()

def update_feeds_job():
    logger.info("Starting feed update job...")
    feeds = get_feeds(active_only=True)
    
    for feed in feeds:
        try:
            logger.info(f"Fetching feed: {feed['name']} ({feed['url']})")
            parsed_feed = fetch_feed(feed['url'])
            
            for entry in parsed_feed['entries']:
                # Save article (returns ID if new, None if exists)
                article_id = save_article(
                    feed['id'],
                    entry['title'],
                    entry['link'],
                    entry['published_at'],
                    entry['content'],
                    entry['image_url']
                )
                
                if article_id:
                    logger.info(f"New article found: {entry['title']}")
                    # Generate summary
                    summary = summarizer.summarize(entry['content'])
                    update_article_summary(article_id, summary)
                    logger.info(f"Summarized article: {article_id}")
                    
        except Exception as e:
            logger.error(f"Error updating feed {feed['url']}: {e}")
            
    # Cleanup old articles
    cleanup_old_articles(days=7)
    logger.info("Feed update job completed.")

def start_scheduler():
    scheduler.add_job(update_feeds_job, 'interval', minutes=60, id='update_feeds')
    scheduler.start()
