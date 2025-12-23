import asyncio
from clien_fetcher import fetch_clien_article_full

async def main():
    url = "https://www.clien.net/service/board/news/19114568"
    print(f"Fetching {url}...")
    result = await fetch_clien_article_full(url)
    print("Fetch result keys:", result.keys())
    comments = result.get('comments', [])
    print(f"Number of comments fetched: {len(comments)}")
    for i, c in enumerate(comments):
        print(f"Comment {i+1}: {c[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
