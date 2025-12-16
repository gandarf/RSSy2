from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_feeds, save_article, update_article_summary, cleanup_old_articles, filter_new_urls, update_feed_last_fetched, get_setting, clear_articles, update_job_status
from rss_fetcher import fetch_feed_async, fetch_article_body_async
from summarizer import GeminiSummarizer
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use AsyncIOScheduler
scheduler = AsyncIOScheduler()
summarizer = GeminiSummarizer()

JOB_ID = 'current_refresh'

async def process_article(feed_id, entry, is_top_candidate, semaphore):
    summary = ""
    is_top = False
    
    # Check if this article was selected as Top 10
    # Note: Logic slightly changed here. 
    # Instead of batch select then process, we might want to batch select first.
    # The original code did: select Top 10 indices from ALL new entries.
    
    # So process_article will just handle summarization IF it was marked as top.
    
    async with semaphore:
        if is_top_candidate:
            logger.info(f"Summarizing Top 10 item: {entry['title']}")
            
            # Fetch full content for top articles
            full_content = await fetch_article_body_async(entry['link'])
            context_content = full_content if full_content else entry['content']
            
            summary = await summarizer.summarize_short_async(context_content)
            if not summary:
                 logger.warning("Summarization failed. Using original content as fallback.")
                 summary = context_content[:500] + "..." # Truncate fallback
            is_top = True
        else:
            # logger.info(f"Saving standard item: {entry['title']}") 
            summary = entry['content']

    # Sync DB write
    save_article(
        feed_id,
        entry['title'],
        entry['link'],
        entry['published_at'],
        entry['content'],
        entry['image_url'],
        summary=summary,
        is_top_selection=is_top
    )
    return 1 # Processed count

async def update_feeds_job():
    logger.info("Starting async feed update job...")
    update_job_status(JOB_ID, "fetching", "Starting update...", 0, 0)
    
    # 1. Clear DB
    logger.info("Clearing existing articles...")
    clear_articles()
    
    # 2. Fetch Feeds
    feeds = get_feeds(active_only=True)
    update_job_status(JOB_ID, "fetching", f"Fetching {len(feeds)} feeds...", len(feeds), 0)
    
    fetch_tasks = [fetch_feed_async(feed['url']) for feed in feeds]
    results = await asyncio.gather(*fetch_tasks)
    
    all_new_entries = []
    
    for i, feed in enumerate(feeds):
        res = results[i]
        feed_id = feed['id']
        entries = res.get('entries', [])
        
        if entries:
            # Update last fetched
            update_feed_last_fetched(feed_id)
            
            # Since we cleared DB, all fetched are "new" effectively.
            # But filter_new_urls logic is still good if we run frequent updates without clearing?
            # User requirement: "Fetch할 때 마다 기존 DB는 무시하고 새로 list를 build"
            # So everything fetched IS new.
            for entry in entries:
                entry['feed_id'] = feed_id # Tag with feed ID
                all_new_entries.append(entry)
                
    update_job_status(JOB_ID, "processing", f"Found {len(all_new_entries)} articles. Selecting Top 10...", len(all_new_entries), 0)
    
    if not all_new_entries:
        logger.info("No articles found.")
        update_job_status(JOB_ID, "completed", "No articles found.", 0, 0)
        return

    # 3. Select Top 10
    top_10_indices = []
    titles = [entry['title'] for entry in all_new_entries]
    
    if len(titles) > 10:
        top_10_indexes_result = await summarizer.select_top_10_async(titles)
        if not top_10_indexes_result:
             logger.warning("Top 10 selection failed. Fallback to first 10.")
             top_10_indices = list(range(10))
        else:
            top_10_indices = top_10_indexes_result
            logger.info(f"Selected Top 10 indices: {top_10_indices}")
    else:
        top_10_indices = list(range(len(titles)))

    top_10_set = set(top_10_indices)
    
    # 4. Process/Summarize Articles
    update_job_status(JOB_ID, "summarizing", "Summarizing articles...", len(all_new_entries), 0)
    
    semaphore = asyncio.Semaphore(3) # Limit concurrent AI calls
    process_tasks = []
    
    processed_count = 0
    
    async def process_wrapper(idx, entry):
        nonlocal processed_count
        try:
            is_top = idx in top_10_set
            await process_article(entry['feed_id'], entry, is_top, semaphore)
        except Exception as e:
            logger.error(f"Error processing article {entry.get('title', 'Unknown')}: {e}")
        finally:
            processed_count += 1
            # Update status
            update_job_status(JOB_ID, "summarizing", f"Processing... {processed_count}/{len(all_new_entries)}", len(all_new_entries), processed_count)

    for i, entry in enumerate(all_new_entries):
        process_tasks.append(process_wrapper(i, entry))
        
    await asyncio.gather(*process_tasks)
    
    # 5. Cleanup
    cleanup_old_articles(days=7)
    update_job_status(JOB_ID, "completed", "Update completed.", len(all_new_entries), len(all_new_entries))
    logger.info("Feed update job completed.")

def start_scheduler():
    interval_minutes = int(get_setting('refresh_interval', 120))
    auto_refresh = get_setting('auto_refresh', 'true') == 'true'

    if auto_refresh:
        scheduler.add_job(update_feeds_job, 'interval', minutes=interval_minutes, id='update_feeds')
        logger.info(f"Scheduler started with interval {interval_minutes} minutes.")
    else:
        logger.info("Scheduler started but auto-refresh is disabled.")
    
    scheduler.start()

def update_job_settings(auto_refresh, interval_minutes):
    job = scheduler.get_job('update_feeds')
    
    if auto_refresh:
        if job:
            job.reschedule(trigger='interval', minutes=interval_minutes)
            logger.info(f"Rescheduled job with interval {interval_minutes} minutes.")
        else:
            scheduler.add_job(update_feeds_job, 'interval', minutes=interval_minutes, id='update_feeds')
            logger.info(f"Added job with interval {interval_minutes} minutes.")
    else:
        if job:
            job.remove()
            logger.info("Removed auto-refresh job.")
