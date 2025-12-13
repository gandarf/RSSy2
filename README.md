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

## Production Deployment (Raspberry Pi)

To run RSSy2 continuously on a Raspberry Pi (or any Linux server), it is recommended to run it as a system service.

### 1. Prerequisites
Ensure your Raspberry Pi is set up and updated:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git python3-venv -y
```

### 2. Installation
Clone the repository and set up the environment:
```bash
# Navigate to your desired directory
cd /home/pi

# Clone repo (replace with your repo URL or copy files)
git clone <your-repo-url> rssy2
cd rssy2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create the `.env` file with your API key:
```bash
nano .env
# Add: GEMINI_API_KEY=your_key_here
```

### 4. Create Systemd Service
Create a service file to handle auto-start and restarts:

```bash
sudo nano /etc/systemd/system/rssy2.service
```

Add the following content (adjust paths if your user is not `pi` or path is different):

```ini
[Unit]
Description=RSSy2 AI News Aggregator
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/rssy2
Environment="PATH=/home/pi/rssy2/venv/bin"
ExecStart=/home/pi/rssy2/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. Start and Enable Service
```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Start the service
sudo systemctl start rssy2

# Enable auto-start on boot
sudo systemctl enable rssy2

# Check status
sudo systemctl status rssy2
```

Now RSSy2 will run in the background and start automatically on boot. Access it at `http://<raspberry-pi-ip>:8000`.
