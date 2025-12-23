import asyncio
import os
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from logger_config import logger

load_dotenv("key.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class GeminiSummarizer:
    def __init__(self):
        if not GEMINI_API_KEY:
            logger.warning("Gemini API Key not found in environment variables. AI features will be disabled.")
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.last_call_time = 0
        self.min_interval = 10.0  # Total safeguard interval
        self.max_retries = 5
        self.lock = asyncio.Lock()  # Atomic rate limit lock

    def _clean_text(self, text):
        if not text:
            return ""
        # If it's HTML, clean with BeautifulSoup, else just strip
        if '<' in text and '>' in text:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        return text.strip()

    async def _call_with_retry_async(self, func, *args, **kwargs):
        """Generic async retry wrapper for API calls with atomic rate limiting"""
        for attempt in range(self.max_retries):
            # Atomic check and update of last_call_time
            async with self.lock:
                elapsed = time.time() - self.last_call_time
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    logger.info(f"Rate limit throttle: waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                
                # Update time BEFORE the call to reserve the slot
                self.last_call_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    wait_time = (2 ** attempt) * 4
                    print(f"Rate limit hit ({error_str}). Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        raise Exception("Max retries exceeded for Gemini API call")

    async def select_top_10_async(self, titles):
        if not GEMINI_API_KEY:
            return []
        
        titles_text = "\n".join([f"{i}. {t}" for i, t in enumerate(titles)])
        prompt = f"""
        Select the top 10 most important or interesting articles from the following list.
        Please focus on economic and technical topics more. If there's no text to review, just ignore it.
        Return ONLY the indices of the selected articles as a comma-separated list (e.g., 0, 2, 5, ...).
        Do not include any other text.
        
        Articles:
        {titles_text}
        """

        try:
            logger.info(f"Gemini select_top_10_async prompt:\n{prompt}")
            response = await self._call_with_retry_async(self.model.generate_content_async, prompt)
            
            text = response.text.strip()
            indices = [int(x.strip()) for x in text.split(',') if x.strip().isdigit()]
            return indices[:10]
        except Exception as e:
            print(f"Error selecting top 10 (async): {e}")
            return []

    async def select_clien_candidates_async(self, candidates):
        """
        Select Top 10 from Clien news based on comment count and keywords.
        candidates: list of dict {'title', 'comment_count'}
        """
        if not GEMINI_API_KEY:
            # Fallback: Sort by comment count
            sorted_indices = sorted(range(len(candidates)), key=lambda k: candidates[k]['comment_count'], reverse=True)
            return sorted_indices[:10]
            
        # Format for prompt
        # "Index. [Comments: N] Title"
        items_text = "\n".join([f"{i}. [Comments: {c['comment_count']}] {c['title']}" for i, c in enumerate(candidates)])

        lines = items_text.splitlines()
        if len(lines) >= 3:
            remaining_lines = lines[3:]
        
        items_text = "\n".join(remaining_lines)
        
        prompt = f"""
        Select the Top 10 articles from the following list from a tech community.
        Criteria:
        1. High comment count.
        2. Relevance to keywords: Google, Apple, Samsung Electronics, Galaxy, TV.
        
        Prioritize articles that match the keywords and have high engagement as much as possible.
        Return ONLY the indices of the selected articles as a comma-separated list excluding index 0,1,2.
        Do not include any notice articles such as "새소식 게시판 이용권한 변경 안내, 새로운소식 게시판 이용규칙, 사이트 이용규칙 (종합)".
        Try to fill out 10 articles as much as possible without notice articles.
        
        Articles:
        {items_text}
        """
        
        try:
             logger.info(f"Gemini select_clien_candidates_async prompt:\n{prompt}")
             response = await self._call_with_retry_async(self.model.generate_content_async, prompt)
             
             text = response.text.strip()
             indices = [int(x.strip()) for x in text.split(',') if x.strip().isdigit()]
             return indices[:10]
        except Exception as e:
            print(f"Error selecting Clien candidates: {e}")
            # Fallback
            return sorted(range(len(candidates)), key=lambda k: candidates[k]['comment_count'], reverse=True)[:10]

    async def summarize_clien_with_comments_async(self, body, comments, max_lines=10):
        if not GEMINI_API_KEY:
            return None, None

        body_text = self._clean_text(body)
        
        if not comments:
            logger.info("No comments found for this article. Skipping comment summary to avoid hallucination.")
            prompt = f"""
            Analyze the following Clien community content and provide a summary in Korean.
            
            1. [ARTICLE SUMMARY]: A concise summary of the main news/article body.
            2. [COMMENT SUMMARY]: Return "댓글이 없습니다."
            
            Instructions:
            - Be objective and professional.
            - Use Markdown (bullet points, bolding).
            - Keep the article summary up to {max_lines} lines.
            - Format your response EXACTLY as follows:
            ---ARTICLE---
            (Article summary here)
            ---COMMENTS---
            댓글이 없습니다.
            
            Article Body:
            {body_text}
            """
        else:
            comments_text = "\n".join([f"- {c}" for c in comments])
            logger.info(f"DEBUG: comments_text for summarization:\n{comments_text}")
            prompt = f"""
            Analyze the following Clien community content and provide two distinct summaries in Korean.
            
            1. [ARTICLE SUMMARY]: A concise summary of the main news/article body.
            2. [COMMENT SUMMARY]: A synthesis of the community's reaction, sentiment, and key discussion points from the comments.
            
            Instructions:
            - Be objective and professional.
            - Use Markdown (bullet points, bolding).
            - Keep the article summary up to {max_lines} lines.
            - Keep the comment summary concise but insightful.
            - Format your response EXACTLY as follows:
            ---ARTICLE---
            (Article summary here)
            ---COMMENTS---
            (Comment summary here)
            
            Article Body:
            {body_text}
            
            Comments:
            {comments_text}
            """
        
        try:
            logger.info(f"Gemini summarize_clien_with_comments_async prompt length: {len(prompt)} chars")
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = await self._call_with_retry_async(
                self.model.generate_content_async, 
                prompt,
                safety_settings=safety_settings
            )
            
            full_text = response.text
            if not full_text:
                return None, None
            
            article_sum = ""
            comment_sum = ""
            
            if "---ARTICLE---" in full_text and "---COMMENTS---" in full_text:
                parts = full_text.split("---COMMENTS---")
                comment_sum = parts[1].strip()
                article_sum = parts[0].replace("---ARTICLE---", "").strip()
            else:
                # Fallback if AI doesn't follow format exactly
                article_sum = full_text
            
            return article_sum, comment_sum
            
        except Exception as e:
            logger.error(f"Error in summarize_clien_with_comments_async: {e}")
            return None, None

    async def summarize_async(self, content, max_lines=None):
        if not GEMINI_API_KEY:
            return None 

        text = self._clean_text(content)
        if not text:
            return None

        length_instruction = "keep it concise."
        if max_lines:
            length_instruction = f"summarize it up to {max_lines} lines."

        prompt = f"""
        Analyze the following content and synthesize a concise summary in Korean.
        
        Instructions:
        1. Summarize the main points clearly.
        2. Do not just copy text. Rewrite in your own words with a professional and objective tone.
        3. Use Markdown formatting (bullet points, bolding) for readability.
        4. {length_instruction}
        
        Content:
        {text}
        """
        
        try:
            logger.info(f"Gemini summarize_async prompt length: {len(prompt)} chars")
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = await self._call_with_retry_async(
                self.model.generate_content_async, 
                prompt,
                safety_settings=safety_settings
            )
            
            if not response.text:
                logger.warning("Gemini returned empty text.")
                return None
            return response.text
        except Exception as e:
            logger.error(f"Error summarizing (async): {e}")
            return None

    async def summarize_short_async(self, content, max_lines=10):
        return await self.summarize_async(content, max_lines=max_lines)
