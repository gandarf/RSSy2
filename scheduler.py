from apscheduler.schedulers.background import BackgroundScheduler
from database import get_feeds, save_article, update_article_summary, cleanup_old_articles
from rss_fetcher import fetch_feed
from summarizer import GeminiSummarizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
summarizer = GeminiSummarizer()

from database import get_feeds, save_article, update_article_summary, cleanup_old_articles, filter_new_urls, update_feed_last_fetched

def update_feeds_job():
    logger.info("Starting feed update job...")
    feeds = get_feeds(active_only=True)
    
    for feed in feeds:
        try:
            logger.info(f"Fetching feed: {feed['name']} ({feed['url']})")
            parsed_feed = fetch_feed(feed['url'])
            
            # Identify new articles by checking URLs
            all_entries = parsed_feed['entries']
            
            # Update last fetched time regardless of new articles
            update_feed_last_fetched(feed['id'])

            if not all_entries:
                continue
                
            entry_urls = [entry['link'] for entry in all_entries]
            new_urls = set(filter_new_urls(entry_urls))
            
            new_entries = [entry for entry in all_entries if entry['link'] in new_urls]
            
            if not new_entries:
                logger.info("No new articles found.")
                continue
            
            logger.info(f"Found {len(new_entries)} new articles.")
            
            # Select Top 10 from new articles if we have many
            top_10_indices = []
            if len(new_entries) > 10:
                titles = [entry['title'] for entry in new_entries]
                top_10_indices = summarizer.select_top_10(titles)
                if not top_10_indices:
                     logger.warning("Top 10 selection failed (or returned empty). Falling back to first 10 articles.")
                     top_10_indices = list(range(10))
                else:
                    logger.info(f"Selected Top 10 indices: {top_10_indices}")
            else:
                top_10_indices = list(range(len(new_entries))) # All are top if <= 10
            
            for i, entry in enumerate(new_entries):
                summary = ""
                is_top = False
                
                if i in top_10_indices:
                    logger.info(f"Summarizing Top 10 item: {entry['title']}")
                    summary = summarizer.summarize_short(entry['content'])
                    is_top = True
                else:
                    logger.info(f"Saving standard item (no AI summary): {entry['title']}")
                    # Use description/content as is, no AI summary
                    summary = entry['content'] # Or description
                    
                save_article(
                    feed['id'],
                    entry['title'],
                    entry['link'],
                    entry['published_at'],
                    entry['content'],
                    entry['image_url'],
                    summary=summary,
                    is_top_selection=is_top
                )
                    
        except Exception as e:
            logger.error(f"Error updating feed {feed['url']}: {e}")
            
    # Cleanup old articles
    cleanup_old_articles(days=7)
    logger.info("Feed update job completed.")

def start_scheduler():
    scheduler.add_job(update_feeds_job, 'interval', minutes=180, id='update_feeds')
    scheduler.start()
