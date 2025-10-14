QUICK START

1) Install Python 3.9+ if you haven't already.
2) Open a terminal and cd into this folder.
3) Create a virtual environment:
   - Windows (PowerShell):
       python -m venv .venv
       .\.venv\Scripts\Activate.ps1
   - macOS/Linux:
       python3 -m venv .venv
       source .venv/bin/activate

4) Install dependencies:
       pip install -r requirements.txt

5) Put your files in the data folder:
       - data/daily_metrics.csv
       - data/weekly_metrics.csv (optional but recommended)
       - data/reports/*.pdf  (your daily/weekly PDF reports)

6) Run the site locally:
       python webapp/app.py

   Then open http://127.0.0.1:5000 in your browser.

NOTES
- The home page shows the latest daily & weekly rows and simple tables of recent history.
- If a CSV is missing or empty, the page will show a gentle message.
- To share with a client, don't expose the dev server directly to the internet.
  We'll add authentication and hosting next if you want (Render/Fly/NGINX).
