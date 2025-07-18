# 📊 YouTube Channel Data Scraper

This project is an enhanced Python-based tool to **scrape detailed data from any public YouTube channel** using the **YouTube Data API v3**. It collects comprehensive video metrics (views, likes, comments, duration, etc.), channel info, and saves the results to an Excel file.

---

## 🔧 Features

- 🔗 Accepts multiple YouTube channel URL formats (`@handle`, `/user/`, `/c/`, `/channel/`)
- 🔍 Resolves channel URL to unique Channel ID automatically
- 📥 Fetches:
  - Channel info (name, description, subscribers, views, country, etc.)
  - Up to **50 recent videos** (can be customized)
  - Detailed video metrics (views, likes, comments, duration, etc.)
  - Video classification based on length (`Low`, `Medium`, `Long`)
  - Upload age (in days), upload timestamps
  - Thumbnail URLs
- 📊 Saves all data in an **Excel file** with a neatly formatted `Video Data` sheet
- 🧠 Built-in logging, error handling, and rate limit awareness

---

## 📦 Dependencies

Install the required packages using pip:

```bash
pip install requests pandas openpyxl isodate
```

---

## 🚀 How to Use

1. **Get a YouTube API key** from [Google Cloud Console](https://console.developers.google.com/).
2. Replace the placeholder API key in the script:

```python
API_KEY = "YOUR_API_KEY"
```

3. Run the script:

```bash
python youtube_chanell_scrapper.py
```

4. Follow the prompts:
   - Enter YouTube channel URL
   - Set how many videos to scrape
   - Optionally save to Excel

---

## 📁 Output

If export is enabled, it will generate an Excel file:

```
youtube_data.xlsx
└── Video Data (sheet)
      • title
      • url
      • views
      • likes
      • comments
      • upload_date
      • duration_minutes
      • video_type
      • description
      • thumbnail_high
```

---

## 🛡️ Error Handling & Quota

- Gracefully handles invalid URLs, quota limits, and missing video stats.
- Keeps track of API requests to avoid exceeding YouTube API daily limits.

---

## ✅ Example Use Case

```text
Enter YouTube channel URL: https://www.youtube.com/@veritasium
Enter maximum number of videos to scrape: 25
Save data to Excel? (y/n): y
Enter Excel filename: veritasium_data.xlsx
```

---

## 📌 Notes

- Designed for **educational, analytical, or content monitoring** purposes.
- YouTube Data API has request quotas; excessive use may require quota extension.