import os
import time
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class GeminiSummarizer:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.last_call_time = 0
        self.min_interval = 2.0  # Minimum 2 seconds between calls (approx 30 RPM)

    def _clean_text(self, html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:10000]  # Limit context size

    def summarize(self, content):
        if not GEMINI_API_KEY:
            return "Error: Gemini API Key not found."

        text = self._clean_text(content)
        if not text:
            return "No content to summarize."

        # Rate limiting
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        try:
            prompt = f"""
            Please summarize the following article in Korean. 
            Focus on the main points and keep it concise.
            
            Article:
            {text}
            """
            response = self.model.generate_content(prompt)
            self.last_call_time = time.time()
            return response.text
        except Exception as e:
            print(f"Error summarizing: {e}")
            return f"Error generating summary: {str(e)}"
