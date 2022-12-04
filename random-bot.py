#!/usr/bin/env python3
"""ZCrypto 3commas random-bots."""
import argparse
import configparser
import os
import random
import re
import sys
import requests
import time
from pathlib import Path
from py3cw.request import Py3CW
from helpers.logging import Logger, NotificationHandler


def format_pair_three(pair):
    """Convert a binance/tradingview formatted pair to threecommas format."""

    for coin in ["BTC", "USDT", "BUSD"]:
        x = re.search(f"{coin}$", pair)
        if x:
            y = re.split(f"{coin}$", pair)
            pair = f"{coin}_{y[0]}"

            return pair

    return None


binance_pairs = []


def init_threecommas_api(cfg):
    """Init the 3commas API."""

    return Py3CW(
        key=cfg.get("customer", "3c-apikey"),
        secret=cfg.get("customer", "3c-apisecret"),
        request_options={
            "request_timeout": 10,
            "nr_of_retries": 3,
            "retry_status_codes": [502, 429],
            "retry_backoff_factor": 1,
        },
    )


def load_config():
    """Create default or load existing config file."""

    cfg = configparser.ConfigParser()
    if cfg.read(f"{datadir}/{program}.ini"):
        return cfg

    cfg["settings"] = {
        "timezone": "Africa/Cairo",
        "timeinterval": 1800,
        "debug": False,
        "logrotate": 7,
        "notifications": False,
        "notify-urls": ["notify-url1"],
    }

    cfg["customer"] = {
        "3c-account": "Customers 3Commas Account number",
        "3c-apikey": "Customers 3Commas API Key",
        "3c-apisecret": "Customers 3Commas API Secret",
    }

    cfg["bot_settings"] = {
        "market": "USDT",
        "botnameprefix": "ZCrypto RB-",
        "maxdeals": 5,
        "takeprofit": 1.5,
        "bosize": 10,
        "sosize": 20,
        "maxsocount": 10,
        "maxsoactive": 3,
        "maxactivedeals": 1,
        "pricedev": 1.2,
        "sovolumescale": 1.0,
        "sostepscale": 1.01,
        "min24hvolume": 100,
        "trailing": False,
        "trailingdeviation": 0.2
    }

    with open(f"{datadir}/{program}.ini", "w") as cfgfile:
        cfg.write(cfgfile)

    return None


def create_hm_bot(pair):
    """Creates a single bot."""
    botname = config.get(f"bot_settings", "botnameprefix") + f" bot pair '{pair}'"
    strategy_list = [[{"strategy": "nonstop"}],
                     [{"options": {"time": "5m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"}],
                     [{"options": {"time": "15m", "type": "buy_or_strong_buy"}, "strategy": "trading_view"}],
                     [{"options": {"time": "1h", "type": "buy_or_strong_buy"}, "strategy": "trading_view"}],
                     [{"options": {"time": "5m", "points": 30, "trigger_condition": "less", "time_period": 7},
                       "strategy": "rsi"}],
                     [{"options": {"time": "15m", "points": 30, "trigger_condition": "less", "time_period": 7},
                       "strategy": "rsi"}],
                     [{"options": {"time": "1h", "points": 30, "trigger_condition": "less", "time_period": 7},
                       "strategy": "rsi"}],
                     [{"options": {"type": "original", "percent": 3}, "strategy": "qfl"}]]
    logger.info(f"Creating single bot with pair {pair}")
    payload = {
        "name": botname,
        "account_id": config.get("customer", "3c-account"),
        "pairs": pair,
        "max_active_deals": int(config.get("bot_settings", "maxactivedeals")),
        "base_order_volume": float(config.get(f"bot_settings", "bosize")),
        "take_profit": float(config.get(f"bot_settings", "takeprofit")),
        "safety_order_volume": float(config.get(f"bot_settings", "sosize")),
        "martingale_volume_coefficient": float(config.get(f"bot_settings", "sovolumescale")),
        "martingale_step_coefficient": float(config.get(f"bot_settings", "sostepscale")),
        "max_safety_orders": int(config.get(f"bot_settings", "maxsocount")),
        "safety_order_step_percentage": float(config.get(f"bot_settings", "pricedev")),
        "take_profit_type": "total",
        "active_safety_orders_count": float(config.get(f"bot_settings", "maxsoactive")),
        "strategy_list": random.choice(strategy_list),
        "trailing_enabled": bool(config.get(f"bot_settings", "trailing")),
        "trailing_deviation": float(config.get(f"bot_settings", "trailingdeviation")),
        "min_volume_btc_24h": float(config.get(f"bot_settings", "min24hvolume"))
    }

    error, data = api.request(
        entity="bots",
        action="create_bot",
        additional_headers={"Forced-Mode": "paper"},
        payload=payload,
    )

    if error:
        logger.info(str(error))
        print(payload["strategy_list"])
    else:
        logger.info(f"Created a new bot called '{botname}")
        time.sleep(1)


# Start application
program = Path(__file__).stem

# Parse and interpret options.
parser = argparse.ArgumentParser(description="ZCrypto helpers.")
parser.add_argument(
    "-d", "--datadir", help="directory to use for config and logs files", type=str
)
parser.add_argument(
    "-s", "--sharedir", help="directory to use for shared files", type=str
)
parser.add_argument(
    "-b", "--blacklist", help="local blacklist to use instead of 3Commas's", type=str
)

args = parser.parse_args()
if args.datadir:
    datadir = args.datadir
else:
    datadir = os.getcwd()

# pylint: disable-msg=C0103
if args.sharedir:
    sharedir = args.sharedir
else:
    sharedir = None
# pylint: disable-msg=C0103
if args.blacklist:
    blacklistfile = f"{datadir}/{args.blacklist}"
else:
    blacklistfile = None

# Create or load configuration file
config = load_config()
if not config:
    # Initialise temp logging
    logger = Logger(datadir, program, None, 7, False, False)
    logger.info(
        f"Created example config file '{datadir}/{program}.ini', edit it and restart the program"
    )
    sys.exit(0)
else:
    # Handle timezone
    if hasattr(time, "tzset"):
        os.environ["TZ"] = config.get(
            "settings", "timezone", fallback="Africa/Cairo"
        )
        time.tzset()

    # Init notification handler
    notification = NotificationHandler(
        program,
        config.getboolean("settings", "notifications"),
        config.get("settings", "notify-urls"),
    )

    # Initialise logging
    logger = Logger(
        datadir,
        program,
        notification,
        int(config.get("settings", "logrotate", fallback=7)),
        config.getboolean("settings", "debug"),
        config.getboolean("settings", "notifications"),
    )
# Configuration settings
api = init_threecommas_api(config)
config = load_config()
logger.info(f"Reloaded configuration from '{datadir}/{program}.ini'")
timeint = int(config.get("settings", "timeinterval"))


def get_all_symbols():
    """Get a list of all Binance symbols against basecurrency."""

    link = "https://api.binance.com/api/v1/exchangeInfo"
    results = requests.get(link).json()
    for x in range(len(results["symbols"])):
        status = results["symbols"][x]["status"]
        symbol = results["symbols"][x]["symbol"]

        # Get only active pairs for Trading
        if status != "TRADING":
            continue
        if symbol.endswith(config.get("bot_settings", "market")):
            # No future coins
            if (
                    ("UP" in symbol)
                    or ("DOWN" in symbol)
                    or ("BULL" in symbol)
                    or ("BEAR" in symbol)
            ):
                continue

            binance_pairs.append(format_pair_three(symbol))

    return binance_pairs


get_all_symbols()
for coin in binance_pairs:
    create_hm_bot(coin)
