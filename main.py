import os
import time
import random
import requests
import openai
from dotenv import load_dotenv

# Load environment variables from .env (only once, at the beginning)
load_dotenv()

# Retrieve API keys from the environment
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Print a truncated version of the API key to confirm loading
print("Using API key:", OPENAI_API_KEY[:4] + "..." + OPENAI_API_KEY[-4:])

# Set your OpenAI API key at the module level (old API style)
openai.api_key = OPENAI_API_KEY

# ----------------------------
# 1) Fetch All US Stock Symbols
# ----------------------------
def get_all_symbols():
    """
    Fetch a list of US stock symbols from Finnhub (exchange=US).
    Returns a list of symbol strings.
    """
    url = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    symbols = [item["symbol"] for item in data if "symbol" in item]
    return symbols

# ----------------------------
# 2) Get Quote for a Symbol
# ----------------------------
def get_quote(symbol):
    """
    Fetch real-time quote data for a single symbol.
    Keys: c (current), h, l, o, pc, t
    """
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

# ----------------------------
# Helper: Truncate text to a max length
# ----------------------------
def truncate_text(text, max_length=200):
    """Truncates the given text to at most max_length characters."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

# ----------------------------
# 3) Analyze a Single Stock using the old OpenAI API
# ----------------------------
def analyze_stock_with_openai(symbol, quote):
    """
    Sends a single stock's data to OpenAI for an in-depth analysis.
    Returns the AI's response (string).
    """
    prompt = f"""
    You are an advanced financial AI. Analyze the following stock in depth:
    Symbol: {symbol}
    Current Price (c): {quote['c']}
    High (h): {quote['h']}
    Low (l): {quote['l']}
    Open (o): {quote['o']}
    Previous Close (pc): {quote['pc']}
    Timestamp (t): {quote['t']}

    Provide a succinct yet thorough analysis describing:
    - Recent performance
    - Notable price changes
    - Short-term prediction
    - Suggested action (buy, hold, or sell), with reasoning
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        # Access the response as a dictionary (old API returns a dict)
        ai_text = response['choices'][0]['message']['content']
        return ai_text.strip()
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed for {symbol}: {e}")
        return "OpenAI call failed"

# ----------------------------
# 4) Compare All Stocks from Past 1 Minute
# ----------------------------
def compare_stocks_with_openai(analyzed_stocks):
    """
    Takes a list of (symbol, quote, analysis, timestamp) from the last minute
    and asks OpenAI to pick the best high-yield option.
    Uses truncated analysis texts to help control token usage.
    Returns the AI's final recommendation (string).
    """
    prompt_list = []
    for item in analyzed_stocks:
        symbol = item["symbol"]
        quote = item["quote"]
        # Truncate the analysis text to reduce token count
        analysis = truncate_text(item["analysis"], max_length=200)
        prompt_list.append(f"Symbol: {symbol}\nPrice: {quote['c']}\nAI Analysis: {analysis}\n")
    
    summary_of_stocks = "\n".join(prompt_list)
    prompt = f"""
    You have the following stock analyses from the last minute:

    {summary_of_stocks}

    Among these, which stock appears to be the best high-yield option 
    in the short- to mid-term? 
    Pick exactly one symbol and provide a brief rationale.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial expert specialized in stock picking."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        ai_text = response['choices'][0]['message']['content']
        return ai_text.strip()
    except Exception as e:
        print(f"[ERROR] OpenAI summary call failed: {e}")
        return "OpenAI summary call failed"

# ----------------------------
# 5) Main Loop
# ----------------------------
def main():
    print("Starting the Stock Analysis Python Script...")
    print("Fetching all US stock symbols from Finnhub...")
    all_symbols = get_all_symbols()
    print(f"Total symbols fetched: {len(all_symbols)}")
    analyzed_stocks = []
    last_comparison_time = time.time()
    comparison_interval = 60  # Change interval to 1 minute (60 seconds)

    while True:
        loop_start = time.time()
        
        # Choose a random stock symbol
        symbol = random.choice(all_symbols)
        
        try:
            quote_data = get_quote(symbol)
        except requests.HTTPError as e:
            print(f"[ERROR] Finnhub quote fetch failed for {symbol}: {e}")
            time.sleep(1)
            continue

        # Analyze the stock
        ai_analysis = analyze_stock_with_openai(symbol, quote_data)
        analyzed_stocks.append({
            "symbol": symbol,
            "quote": quote_data,
            "analysis": ai_analysis,
            "timestamp": time.time()
        })

        now = time.time()
        if now - last_comparison_time >= comparison_interval:
            print("\n[COMPARISON] 1 minute has passed, comparing all analyzed stocks...\n")
            best_pick = compare_stocks_with_openai(analyzed_stocks)
            print("[RESULT] AI's top pick among last 1 minute:\n")
            print(best_pick)
            print("\n===================================================\n")
            # Clear the list for the next minute's analysis
            analyzed_stocks.clear()
            last_comparison_time = now

        elapsed = time.time() - loop_start
        time.sleep(max(0, 1 - elapsed))

if __name__ == "__main__":
    main()
