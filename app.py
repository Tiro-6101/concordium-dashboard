import os
from pathlib import Path
from flask import Flask, render_template, send_from_directory, abort
import pandas as pd
from datetime import datetime

# -------------------------------
# Basic Authentication (login gate)
# -------------------------------
from functools import wraps
from flask import request, Response

# Credentials are taken from environment variables so you can change them on Render
USER = os.getenv("DASH_USER", "calmac01")      # default username
PASS = os.getenv("DASH_PASS", "cicero61")  # default password

def check_auth(username, password):
    """Check if a username/password pair is valid."""
    return username == USER and password == PASS

def authenticate():
    """Send 401 response that enables basic auth"""
    return Response(
        "Access denied.\n", 401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    """Decorator that forces authentication on routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


app = Flask(__name__, template_folder="templates", static_folder="static")


# =============================
# Configuration (edit if needed)
# =============================
# Your CSVs remain in Downloads. Adjust if your username/path changes.
DATA_SRC_DIR = Path(os.getenv("CCD_DATA_DIR", r"C:\Users\Callum\Downloads")).resolve()
CHARTS_SRC_DIR = Path(os.getenv("CCD_CHARTS_DIR", r"C:\Users\Callum\Downloads\daily_charts")).resolve()

# The PDFs can live inside the project (safe to move)
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = (BASE_DIR / "data" / "reports").resolve()


# Filenames we expect in DATA_SRC_DIR
DAILY_SUMMARY_NAME = "ccd_daily_summary.csv"
EVENTS_NAME = "ccd_events.csv"

# Chart filename patterns inside CHARTS_SRC_DIR (newest wins)
CHART_PATTERNS = {
    "price_over_time": "price_over_time_*.png",
    "buyer_seller_trend": "buyer_seller_trend_*.png",
    "event_counts": "event_counts_*.png",
    "price_vs_buyers": "price_vs_buyers_*.png",
    "price_vs_buyers_trend": "price_vs_buyers_trend_*.png",
    # Placeholder for future chart you'll add later:
    "ccd_vs_btx": "ccd_vs_btx_*.png",
}

# ---------- Helpers ----------
def read_csv_optional(path: Path):
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception as e:
        print(f"[!] Failed to read CSV {path}: {e}")
    return None

def latest_row_by_date(df: pd.DataFrame, date_col: str = "date"):
    try:
        if date_col in df.columns:
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.sort_values(date_col)
            return df.iloc[-1].to_dict()
        return df.iloc[-1].to_dict()
    except Exception:
        return None

def latest_events(n=10):
    events_path = DATA_SRC_DIR / EVENTS_NAME
    df = read_csv_optional(events_path)
    if df is None or df.empty:
        return []
    # Normalize and sort by timestamp
    if "timestamp_utc" in df.columns:
        df = df.copy()
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce")
        df = df.sort_values("timestamp_utc", ascending=False)
    else:
        df = df.iloc[::-1]  # reverse if no timestamp column
    return df.head(n).to_dict(orient="records")

def latest_chart_filename(pattern_key: str):
    """Return the filename (not full path) of the newest chart matching the pattern key."""
    pattern = CHART_PATTERNS.get(pattern_key)
    if not pattern:
        return None
    files = sorted(CHARTS_SRC_DIR.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files[0].name if files else None

# ---------- Routes ----------
@app.route("/")
@requires_auth
def index():
    # Load daily summary
    daily_path = DATA_SRC_DIR / DAILY_SUMMARY_NAME
    daily_df = read_csv_optional(daily_path)
    daily_latest = latest_row_by_date(daily_df, "date") if (daily_df is not None and not daily_df.empty) else None

    # Extract cards (robust to missing keys)
    def get(d, key, default=None):
        return None if d is None else d.get(key, default)

    cards = {
        "price_avg_usd": get(daily_latest, "price_avg_usd"),
        "price_close_usd": get(daily_latest, "price_close_usd"),
        "price_change_pct": get(daily_latest, "price_change_pct"),
        "price_std_usd": get(daily_latest, "price_std_usd"),
        "volatility_index": get(daily_latest, "volatility_index"),
        "avg_buyers_pct": get(daily_latest, "avg_buyers_pct"),
        "avg_sellers_pct": get(daily_latest, "avg_sellers_pct"),
        "dominant_sentiment": get(daily_latest, "dominant_sentiment"),
        "total_volume_notional": get(daily_latest, "total_volume_notional"),
        "date": get(daily_latest, "date"),
    }

    # Events
    events = latest_events(10)

    # Charts (newest by pattern)
    charts = {
        "price_over_time": latest_chart_filename("price_over_time"),
        "buyer_seller_trend": latest_chart_filename("buyer_seller_trend"),
        "event_counts": latest_chart_filename("event_counts"),
        "price_vs_buyers": latest_chart_filename("price_vs_buyers"),
        "price_vs_buyers_trend": latest_chart_filename("price_vs_buyers_trend"),
        "ccd_vs_btx": latest_chart_filename("ccd_vs_btx"),  # may be None for now
    }

    return render_template("index.html", cards=cards, events=events, charts=charts)

@app.route("/charts/<path:filename>")
def external_chart(filename):
    # Serve chart images from the external charts directory in Downloads
    target = (CHARTS_SRC_DIR / filename).resolve()
    if not target.exists() or not target.is_file():
        abort(404)
    # basic path safety
    if CHARTS_SRC_DIR not in target.parents:
        abort(403)
    return send_from_directory(CHARTS_SRC_DIR, filename)

@app.route("/reports")
def reports_home():
    """Redirect to the main reports overview."""
    return render_template("reports_home.html")
@app.route("/reports/daily")
def daily_reports():
    from pathlib import Path
    reports_dir = Path("data/reports")
    daily_reports = sorted(
        [f.name for f in reports_dir.glob("daily_report_*.pdf")],
        reverse=True
    )
    return render_template("reports_daily.html", pdfs=daily_reports)

@app.route("/reports/weekly")
def reports_weekly():
    """List all weekly report PDFs."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(
        [f.name for f in REPORTS_DIR.glob("weekly_report_*.pdf")],
        reverse=True
    )
    return render_template("reports_weekly.html", pdfs=pdfs)

@app.route("/reports/<path:filename>")
def download_report(filename):
    target = (REPORTS_DIR / filename).resolve()
    if not target.exists() or not target.is_file() or target.suffix.lower() != ".pdf":
        abort(404)
    if REPORTS_DIR not in target.parents:
        abort(403)
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
