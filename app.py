from flask import Flask, render_template, jsonify, request
import requests
import threading
import time

app = Flask(__name__)

# Global variables
latest_data = []
current_settings = {'interval': '3m', 'std_dev': 2}
lock = threading.Lock()

# Telegram Bot credentials (replace with your own)
TELEGRAM_TOKEN = 'your_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'

def send_message(message):
    """
    Send a message to a Telegram chat.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    response = requests.post(url, data=data)
    return response.json()

@app.route('/toggle_alert', methods=['POST'])
def toggle_alert():
    data = request.json
    symbol = data.get('symbol')
    active = data.get('active')

    if active:
        send_message(f"Alarm has been activated for {symbol}")
    else:
        send_message(f"Alarm has been deactivated for {symbol}")

    return jsonify({'status': 'success', 'symbol': symbol, 'active': active})

def fetch_price_data(pair, interval):
    """
    Fetch historical price data for a given cryptocurrency pair.
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit=100"
    response = requests.get(url)
    prices = [float(kline[4]) for kline in response.json()]  # Closing prices
    return prices



def calculate_bollinger_bands(prices, std_dev_multiplier):
    """
    Calculate Bollinger Bands for a list of prices.
    """
    if not prices:
        return None, None, None
    moving_avg = sum(prices) / len(prices)
    std_dev = (sum([(p - moving_avg) ** 2 for p in prices]) / len(prices)) ** 0.5
    upper_band = moving_avg + std_dev_multiplier * std_dev
    lower_band = moving_avg - std_dev_multiplier * std_dev
    return upper_band, moving_avg, lower_band

def update_data():
    global latest_data
    pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
             'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LTCUSDT']

    while True:
        with lock:
            interval = current_settings['interval']
            std_dev = current_settings['std_dev']

        above_upper_band = []
        below_lower_band = []
        within_bands = []

        for pair in pairs:
            prices = fetch_price_data(pair, interval)
            upper_band, moving_avg, lower_band = calculate_bollinger_bands(prices, std_dev)

            current_price = prices[-1] if prices else None
            status = 'Within Bands'
            color = 'normal'  # Normal color for within the bands
            percentage_diff = 0  # Default percentage difference

            if current_price:
                if current_price > upper_band:
                    status = 'Above Upper Band'
                    color = 'above'
                    percentage_diff = ((current_price - upper_band) / upper_band) * 100
                    above_upper_band.append(
                        (pair, current_price, upper_band, lower_band, status, color, percentage_diff))
                elif current_price < lower_band:
                    status = 'Below Lower Band'
                    color = 'below'
                    percentage_diff = ((lower_band - current_price) / lower_band) * 100
                    below_lower_band.append(
                        (pair, current_price, upper_band, lower_band, status, color, percentage_diff))
                else:
                    status = 'Within Bands'
                    color = 'normal'
                    percentage_diff = 0
                    within_bands.append((pair, current_price, upper_band, lower_band, status, color, percentage_diff))

        # Sort the lists
        above_upper_band.sort(key=lambda x: x[6], reverse=True)  # Descending order for above upper band
        below_lower_band.sort(key=lambda x: x[6])  # Ascending order for below lower band

        # Merge the lists
        latest_data = above_upper_band + within_bands + below_lower_band

        time.sleep(1)  # Update data every minute


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/data')
def data():
    return jsonify(latest_data)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    global current_settings
    data = request.json
    with lock:
        current_settings['interval'] = data.get('interval', current_settings['interval'])
        current_settings['std_dev'] = data.get('std_dev', current_settings['std_dev'])
    return jsonify({'status': 'updated'})



if __name__ == '__main__':
    data_thread = threading.Thread(target=update_data, daemon=True)
    data_thread.start()
    app.run(debug=True)
