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
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.last_call_time = 0
        self.min_interval = 2.0  # Minimum 2 seconds between calls (approx 30 RPM)

    def _clean_text(self, html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:10000]  # Limit context size

    def select_top_10(self, titles):
        if not GEMINI_API_KEY:
            return []
        
        # Prepare the list for the prompt
        titles_text = "\n".join([f"{i}. {t}" for i, t in enumerate(titles)])
        
        try:
            prompt = f"""
            Select the top 10 most important or interesting articles from the following list.
            Return ONLY the indices of the selected articles as a comma-separated list (e.g., 0, 2, 5, ...).
            Do not include any other text.
            
            Articles:
            {titles_text}
            """
            response = self.model.generate_content(prompt)
            self.last_call_time = time.time()
            
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
            return "Error: Gemini API Key not found."

        text = self._clean_text(content)
        if not text:
            return "No content to summarize."

        # Rate limiting
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        try:
            length_instruction = "keep it concise."
            if max_length:
                length_instruction = f"summarize it up to 4 lines."

            prompt = f"""
            Please summarize the following article in Korean. 
            Focus on the main points and {length_instruction}
            
            Article:
            {text}
            """
            response = self.model.generate_content(prompt)
            self.last_call_time = time.time()
            return response.text
        except Exception as e:
            print(f"Error summarizing: {e}")
            return f"Error generating summary: {str(e)}"
            
    def summarize_short(self, content):
        return self.summarize(content, max_length=250)
