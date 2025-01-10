import os
import logging
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# --- Load Configuration ---
load_dotenv()  # Load environment variables from a .env file

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler("trade_bot.log", mode='a')  # Logs to file
    ]
)

# --- Account and API Configuration ---
ACCOUNT_NUMBER = os.getenv("ACCOUNT_NUMBER")
PASSWORD = os.getenv("PASSWORD")
SERVER = os.getenv("SERVER")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# --- Trading Parameters ---
RISK_PERCENTAGE = float(os.getenv("RISK_PERCENTAGE", 2.0))
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", 10.0))
ENTRY_DISCOUNT_PERCENT = float(os.getenv("ENTRY_DISCOUNT_PERCENT", 2.0))
TIMEFRAME = mt5.TIMEFRAME_M1

# --- Initialization ---
def initialize_mt5():
    """
    Initialize MetaTrader 5 and login to the account.
    """
    if not mt5.initialize():
        logging.error("MetaTrader 5 initialization failed")
        raise RuntimeError("MetaTrader 5 initialization failed")
    if not mt5.login(account=int(ACCOUNT_NUMBER), password=PASSWORD, server=SERVER):
        logging.error(f"Login failed: {mt5.last_error()}")
        raise RuntimeError("MetaTrader 5 login failed")
    logging.info(f"Logged in to account {ACCOUNT_NUMBER} successfully.")

# --- Email Notification ---
def send_email(subject, body):
    """
    Send an email notification.
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info(f"Email sent to {RECIPIENT_EMAIL}: {subject}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

# --- News Analysis ---
def fetch_news(api_key, query):
    """
    Placeholder function to fetch news articles.
    """
    return [{"title": f"{query} stock is performing well"}]

def analyze_sentiment(text):
    """
    Analyze the sentiment of a given text.
    """
    positive_words = ["gain", "up", "positive", "bullish"]
    negative_words = ["down", "loss", "negative", "bearish"]

    if any(word in text.lower() for word in positive_words):
        return 1
    elif any(word in text.lower() for word in negative_words):
        return -1
    else:
        return 0

def make_trade_decision(polarity, threshold=0.1):
    """
    Make a trade decision based on sentiment polarity.
    """
    if polarity > threshold:
        return "Buy"
    elif polarity < -threshold:
        return "Sell"
    else:
        return "Hold"

def analyze_news_and_make_decision(stock_symbol):
    """
    Analyze news for a specific stock and make a trade decision.
    """
    query = f"{stock_symbol} stock"
    articles = fetch_news(NEWS_API_KEY, query)

    positive_count, negative_count = 0, 0
    for article in articles:
        sentiment = analyze_sentiment(article['title'])
        if sentiment > 0:
            positive_count += 1
        elif sentiment < 0:
            negative_count += 1

    trade_decision = make_trade_decision(positive_count - negative_count)
    logging.info(f"Trade Decision: {trade_decision}")
    return trade_decision

# --- Trading Logic ---
def place_trade(decision, symbol, lot_size=0.1):
    """
    Place a trade based on the given decision.
    """
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, 1)
    if not rates:
        logging.error(f"Failed to retrieve rates for {symbol}")
        return

    current_price = rates[0]["close"]
    take_profit = current_price * (1 + TAKE_PROFIT_PERCENT / 100)
    entry_price = current_price * (1 - ENTRY_DISCOUNT_PERCENT / 100)

    if decision == "Buy":
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_BUY,
            "price": entry_price,
            "tp": take_profit,
        })
    elif decision == "Sell":
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_SELL,
            "price": entry_price,
            "tp": take_profit,
        })
    else:
        logging.info("No trade action needed.")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Trade failed: {result.retcode}")
    else:
        logging.info(f"Trade successful: {decision} at {entry_price}, TP={take_profit}")

# --- Main Function ---
def main():
    try:
        initialize_mt5()
        stock_symbol = "AAPL"
        trade_decision = analyze_news_and_make_decision(stock_symbol)
        place_trade(trade_decision, stock_symbol)
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        send_email("Trade Bot Error", str(e))

# --- Run the Bot ---
if __name__ == "__main__":
    main()
