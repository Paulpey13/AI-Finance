from binance.client import Client
from binance.exceptions import BinanceAPIException

import time
import logging
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.CONFIG import bi_api_key, bi_sec_key
# Initialize Binance Client
client = Client(bi_api_key, bi_sec_key)

# List of selected cryptos
cryptos = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT',
    'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'AVAXUSDT', 'LTCUSDT', 'LINKUSDT'
]

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.StreamHandler(),  # Display in console
    logging.FileHandler('trading_bot.log', mode='a')  # Save logs to file
])

def get_top_loss_crypto(cryptos):
    """
    Get the crypto with the largest negative 24h price change.
    """
    best_loss = None
    best_crypto = None

    for crypto in cryptos:
        try:
            ticker = client.get_ticker(symbol=crypto)
            percent_change = float(ticker['priceChangePercent'])

            if best_loss is None or percent_change < best_loss:
                best_loss = percent_change
                best_crypto = crypto
        except BinanceAPIException as e:
            logging.error(f"Error fetching ticker data for {crypto}: {e}")

    logging.info(f"Crypto with the largest loss: {best_crypto} ({best_loss}% change)")
    return best_crypto

def invest_in_crypto(crypto, usdt_balance, percent=0.5):
    """
    Invest a percentage of available USDT into the chosen crypto.
    Adjust the quantity to meet Binance's LOT_SIZE filter and precision requirements.
    """
    amount_to_invest = usdt_balance * percent
    current_price = float(client.get_symbol_ticker(symbol=crypto)['price'])
    amount_to_buy = amount_to_invest / current_price

    # Fetch trading rules for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next(item for item in exchange_info['symbols'] if item['symbol'] == crypto)
    
    # Extract LOT_SIZE and PRECISION filters
    lot_size_filter = next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE')
    precision_filter = next(filter for filter in symbol_info['filters'] if filter['filterType'] == 'PRICE_FILTER')

    # Extract LOT_SIZE parameters
    min_qty = float(lot_size_filter['minQty'])
    step_size = float(lot_size_filter['stepSize'])

    # Extract price precision (decimal places allowed for price)
    price_precision = int(precision_filter['tickSize'].find('1') - 1)

    # Adjust the quantity to comply with the LOT_SIZE filter
    amount_to_buy = max(min_qty, (amount_to_buy // step_size) * step_size)

    # Round the amount_to_buy to match the precision required
    quantity_precision = int(lot_size_filter['stepSize'].find('1') - 1)
    amount_to_buy = round(amount_to_buy, quantity_precision)

    try:
        order = client.order_market_buy(
            symbol=crypto,
            quantity=amount_to_buy  # Ensure precision for crypto orders
        )
        logging.info(f"Bought {amount_to_buy} {crypto} for {amount_to_invest} USDT at {current_price} USDT each.")
        return order, current_price
    except BinanceAPIException as e:
        logging.error(f"Error executing buy order for {crypto}: {e}")
        return None, None



def wait_for_pump(crypto, buy_price, target_gain=1.003):
    """
    Wait for the price of the crypto to increase by a target percentage.
    """
    while True:
        try:
            current_price = float(client.get_symbol_ticker(symbol=crypto)['price'])
            if current_price >= buy_price * target_gain:
                return current_price
            time.sleep(1)  # Check every 10 seconds
        except BinanceAPIException as e:
            logging.error(f"Error fetching price for {crypto}: {e}")
            time.sleep(1)  # Retry after a delay

def sell_crypto(crypto, amount):
    """
    Sell the crypto back to USDT.
    """
    try:
        order = client.order_market_sell(
            symbol=crypto,
            quantity=round(amount, 6)  # Ensure precision for crypto orders
        )
        sell_price = float(order['fills'][0]['price'])
        logging.info(f"Sold {round(amount, 6)} {crypto} at {sell_price} USDT each.")
        return order
    except BinanceAPIException as e:
        logging.error(f"Error executing sell order for {crypto}: {e}")
        return None

def run_trading_bot():
    """
    Run the trading bot in an infinite loop, ensuring only one trade at a time.
    """
    active_trade = None  # Track the current active trade

    while True:
        try:
            if active_trade:
                # If a trade is active, monitor the price for selling
                crypto, buy_price, amount_bought = active_trade
                target_price = wait_for_pump(crypto, buy_price)

                # Attempt to sell the crypto
                sell_order = sell_crypto(crypto, amount_bought)
                if sell_order:
                    logging.info(f"Trade completed for {crypto}. Profit achieved.")
                    active_trade = None  # Clear the active trade after completion
                else:
                    logging.error(f"Failed to sell {crypto}. Holding the position for retry.")
                time.sleep(1)  # Avoid frequent checking
                
            else:
                # Fetch USDT balance
                usdt_balance = float(client.get_asset_balance(asset='USDT')['free'])
                if usdt_balance < 10:  # Minimum USDT required for a trade
                    logging.warning("Insufficient USDT balance to trade. Waiting...")
                    time.sleep(1)
                    continue

                # Find the top loss crypto
                top_loss_crypto = get_top_loss_crypto(cryptos)

                # Invest in the top loss crypto
                order, buy_price = invest_in_crypto(top_loss_crypto, usdt_balance)
                if order is None:
                    continue  # Skip this cycle if buy failed

                # Amount of crypto bought
                amount_bought = float(order['fills'][0]['qty'])

                # Set the active trade
                active_trade = (top_loss_crypto, buy_price, amount_bought)
                logging.info(f"Active trade started: {active_trade}")

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            time.sleep(1)  # Retry after a delay

        time.sleep(1)  # Delay between trading cycles

if __name__ == "__main__":
    run_trading_bot()

