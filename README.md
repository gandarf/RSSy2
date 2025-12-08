# RSSy2 - AI News Briefing

RSSy2 is an AI-powered RSS feed summarizer that uses Google Gemini to generate concise Korean summaries of news articles.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Create a `.env` file in the project root and add your Gemini API key:
    ```
    GEMINI_API_KEY=your_api_key_here
    ```

3.  **Run the Application:**
    ```bash
    uvicorn main:app --reload
    ```

4.  **Access the Dashboard:**
    Open your browser and go to `http://localhost:8000`.

## Features

-   **Feed Management:** Add and remove RSS feeds via the web UI.
-   **AI Summarization:** Automatically fetches and summarizes new articles using Gemini (in Korean).
-   **Auto-Update:** Runs in the background every hour to fetch new content.
-   **Manual Refresh:** "Refresh Now" button to trigger an immediate update.
