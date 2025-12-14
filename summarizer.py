import os
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv("key.env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class GeminiSummarizer:
    def __init__(self):
        if not GEMINI_API_KEY:
            print("WARNING: Gemini API Key not found in environment variables. AI features will be disabled.")
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self.last_call_time = 0
        self.min_interval = 10.0  # Increased to 10 seconds (approx 6 RPM) for extreme safety
        self.max_retries = 5

    def _clean_text(self, html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:4000]  # Limit context size

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _call_with_retry(self, func, *args, **kwargs):
        """Generic retry wrapper for API calls"""
        for attempt in range(self.max_retries):
            self._wait_for_rate_limit()
            try:
                result = func(*args, **kwargs)
                self.last_call_time = time.time()
                return result
            except Exception as e:
                # Check for 429 or quota errors
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    wait_time = (2 ** attempt) * 4  # Aggressive Backoff: 4, 8, 16, 32, 64 seconds
                    print(f"Rate limit hit ({error_str}). Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Non-retriable error
                    raise e
        raise Exception("Max retries exceeded for Gemini API call")

    def select_top_10(self, titles):
        if not GEMINI_API_KEY:
            return []
        
        # Prepare the list for the prompt
        titles_text = "\n".join([f"{i}. {t}" for i, t in enumerate(titles)])
        
        prompt = f"""
        Select the top 10 most important or interesting articles from the following list.
        Please focus on economic, IT related, social topics more.
        Return ONLY the indices of the selected articles as a comma-separated list (e.g., 0, 2, 5, ...).
        Do not include any other text.
        
        Articles:
        {titles_text}
        """

        try:
            # Wrap the generation call
            response = self._call_with_retry(self.model.generate_content, prompt)
            
            # Parse response
            text = response.text.strip()
            # Handle potential non-numeric characters roughly
            indices = [int(x.strip()) for x in text.split(',') if x.strip().isdigit()]
            return indices[:10] # Enforce max 10
            
        except Exception as e:
            print(f"Error selecting top 10: {e}")
            return []

    def summarize(self, content, max_length=None):
        if not GEMINI_API_KEY:
            return None # Return None on API key error to fallback

        text = self._clean_text(content)
        if not text:
            return None

        length_instruction = "keep it concise."
        if max_length:
            length_instruction = f"summarize it up to 4 lines."

        prompt = f"""
        Please summarize the following article in Korean. 
        Focus on the main points and {length_instruction}
        
        Article:
        {text}
        """
        
        try:
            response = self._call_with_retry(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            print(f"Error summarizing: {e}")
            return None # Return None on failure to trigger fallback
            
    def summarize_short(self, content):
        return self.summarize(content, max_length=250)
