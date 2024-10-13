import sys
import os
import json
import time
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont

coins = [
    {"id": "bitcoin", "name": "bitcoin", "display": "BTC", "format": 0},
    {"id": "dogecoin", "name": "dogecoin", "display": "DOGE", "format": 3},
    {"id": "litecoin", "name": "litecoin", "display": "LTC", "format": 2},
    {"id": "verus-coin", "name": "verus-coin", "display": "VRSC", "format": 2}
]

screen_rotate = 180
DAYS_HISTORY = 7

Font = ImageFont.truetype('Font.ttc', 24)
# save to Data folder
data_folder = "Data"
if not os.path.exists(data_folder):
    os.makedirs(data_folder)
    
# Coin information file
coin_info_file = os.path.join(data_folder, "coins.txt")

# Function to get the current time
def get_current_time():
    now = datetime.now()
    day = now.strftime("%A").upper()
    date = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    return f"{day}  {time_str}\n{date}"

# Function to get coin price
def get_coin_price(coin_id, coin_name):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get(coin_name, {}).get("usd")
    except requests.RequestException as e:
        return None

# Function to get historical prices
def get_historical_prices(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={DAYS_HISTORY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        prices = [price[1] for price in data["prices"]]
        return prices
    except requests.RequestException as e:
        return []

# Function to save coin prices to a file
def save_coin_prices(coin_prices):
    with open(coin_info_file, "w") as f:
        json.dump(coin_prices, f)

# Function to load coin prices from a file
def load_coin_prices():
    if os.path.exists(coin_info_file):
        with open(coin_info_file, "r") as f:
            return json.load(f)
    return {}

# Function to check if new coin data should be fetched
def should_fetch_new_coin_data(coin_prices, coin_name):
    if coin_name in coin_prices:
        last_fetch_time = datetime.fromisoformat(coin_prices[coin_name]["timestamp"])
        if datetime.now() - last_fetch_time < timedelta(minutes=5):
            return False
    return True

# Function to fetch and save coin price
def fetch_and_save_coin_price(coin_id, coin_name):
    coin_price = get_coin_price(coin_id, coin_name)
    historical_prices = get_historical_prices(coin_id)
    if coin_price is not None and historical_prices:
        coin_prices = load_coin_prices()
        coin_prices[coin_name] = {
            "price": coin_price,
            "historical_prices": historical_prices,
            "timestamp": datetime.now().isoformat()
        }
        save_coin_prices(coin_prices)
    return coin_price, historical_prices

# Function to get cached coin price
def get_coin_price_cached(coin_id, coin_name):
    coin_prices = load_coin_prices()
    if should_fetch_new_coin_data(coin_prices, coin_name):
        return fetch_and_save_coin_price(coin_id, coin_name)
    return coin_prices[coin_name]["price"], coin_prices[coin_name]["historical_prices"]

# Function to plot prices
def plot_prices(prices, coin_display):
    plt.figure(figsize=(2.8, 0.9))  # Adjust figure size to be wider
    ax = plt.gca()
    ax.plot(prices, color='black')

    # Set the y-axis limits to the range of the prices
    ax.set_ylim([min(prices), max(prices)])

    # Determine y-axis label format based on coin display name
    if coin_display == "BTC":
        # For Bitcoin, show large numbers without decimal places
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    else:
        # For other coins, show two decimal places
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.2f}'))
        
    ax.tick_params(axis='y', labelsize=6)

    # Remove x-axis labels and plot border
    ax.set_xticks([]) 
    ax.grid(False) 
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Save the plot to an image file in the Data folder
    plot_path = os.path.join(data_folder, f"{coin_display}_plot.png")
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    return plot_path
  
def main():
    epd = epd2in13_V3.EPD()
    epd.init()
    epd.Clear(0xFF)

    while True:
        # Display coin prices and graphs
        for coin in coins:
            coin_price, historical_prices = get_coin_price_cached(coin["id"], coin["name"])

            if coin_price is not None and historical_prices:
                plot_path = plot_prices(historical_prices, coin["display"])

                # Load the plot image
                plot_image = Image.open(plot_path).convert('1')
                image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
                draw = ImageDraw.Draw(image)

                # Draw the price at the top
                draw.text((5, 0), f"{coin['display']}: ${coin_price:,.{coin['format']}f}", font=Font, fill=0)

                # Paste the plot image below the price text
                image.paste(plot_image, (-10, 30))
                
                # Rotate the image by 180 degrees
                image = image.rotate(screen_rotate)

                epd.displayPartial(epd.getbuffer(image))
                time.sleep(30)  # Display each coin price and graph for 30 seconds
            else:
                print("Failed to retrieve coin price or historical prices")

if __name__ == "__main__":
    main()
