# File: api.py
# This runs on your GCP server.

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import re
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Import our existing scraper function
from scraper import scrape_reviews

# --- Initialization ---
app = Flask(__name__)
# Enable CORS to allow requests from your Hostinger domain
CORS(app) 

# Download VADER lexicon once on startup
nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()

# --- Helper Functions ---
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+|https\S+", "", text )
    text = re.sub(r"[^a-zA-Z0-9\s\u0600-\u06FF]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def analyze_sentiments(df):
    if df.empty:
        return df
    df['Cleaned Text'] = df['Review Text'].apply(clean_text)
    df['Compound'] = df['Cleaned Text'].apply(lambda text: sia.polarity_scores(text)['compound'])
    df['Sentiment'] = df['Compound'].apply(
        lambda score: "Positive" if score > 0.05 else ("Negative" if score < -0.05 else "Neutral")
    )
    return df

# --- API Endpoint ---
@app.route('/analyze', methods=['POST'])
def analyze_url():
    # Get the URL from the incoming request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "URL not provided"}), 400

    url = data['url']
    
    # A dummy placeholder for the scraper to report status (not visible to user)
    class DummyStatus:
        def text(self, message):
            print(message) # Log status to the server console
        def error(self, message):
            print(f"ERROR: {message}")

    try:
        # Run the scraper
        # We no longer need the screenshot path, so we use _
        reviews_df, _ = scrape_reviews(url, DummyStatus())

        if reviews_df.empty:
            return jsonify({"error": "Failed to scrape reviews. The product may have no reviews or the site blocked the request."}), 500

        # Analyze the data
        analyzed_df = analyze_sentiments(reviews_df)

        # Prepare the data for the frontend
        sentiment_counts = analyzed_df['Sentiment'].value_counts().to_dict()
        
        # Convert dataframe to a list of dictionaries for JSON
        reviews_list = analyzed_df.to_dict(orient='records')

        response_data = {
            "sentiment_summary": {
                "positive": sentiment_counts.get("Positive", 0),
                "negative": sentiment_counts.get("Negative", 0),
                "neutral": sentiment_counts.get("Neutral", 0),
            },
            "reviews": reviews_list
        }
        
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

# --- Main entry point to run the server ---
if __name__ == '__main__':
    # Listens on all network interfaces on port 5000
    app.run(host='0.0.0.0', port=5000)

