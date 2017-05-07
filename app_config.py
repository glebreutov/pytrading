import json
from collections import namedtuple

from decimal import Decimal

from mm.book import BipolarContainer


class VenueConfig:
    def __init__(self, dict):
        self.url = dict['url']
        self.key = dict['key']
        self.secret = dict['secret']
        self.taker_comission_percent = dict['taker_comission_percent']
        self.tick_size = Decimal(dict['tick_size'])
        self.min_order_size = Decimal(dict['min_order_size'])
        self.start_pos = Decimal(dict['start_pos'])
        self.start_balance = Decimal(dict['start_balance'])


class LoggingConfig:
    def __init__(self, dict):
        self.dir = dict['dir']
        self.level = dict['level']


class ClientConfig:
    def __init__(self, dict):
        self.enabled = dict['enabled']
        self.port = dict['port']


class AssetConfig:
    def __init__(self, dict):
        self.currency = dict['currency']
        self.crypto = dict['crypto']


class MarketmakerConfig:
    def __init__(self, dict):
        self.ema_work_perc = Decimal(dict['ema_work_perc'])
        self.min_levels = Decimal(dict['min_levels'])
        self.liq_behind = BipolarContainer(bid=Decimal(dict['liq_behind']['BID']),
                                           ask=Decimal(dict['liq_behind']['ASK']))
        self.order_size = BipolarContainer(bid=Decimal(dict['order_size']['BID']),
                                           ask=Decimal(dict['order_size']['ASK']))
        self.min_profit = Decimal(dict['min_profit'])
        self.price_tolerance = Decimal(dict['price_tolerance'])
        self.refresh_timout = int(dict['refresh_timout'])


class AppConfig:
    venue: VenueConfig = None
    logging: LoggingConfig = None
    client: ClientConfig = None
    asset: AssetConfig = None
    algo: MarketmakerConfig = None
    accounts: dict = None

    def __init__(self, dict):
        self.venue = VenueConfig(dict['venue'])
        self.logging = LoggingConfig(dict['logging'])
        self.client = ClientConfig(dict['client'])
        self.asset = AssetConfig(dict['asset'])
        algo_config_str: str = dict['algo']['config_class']
        split = algo_config_str.split(".")

        module = __import__(split[1], globals(), locals(), ['object'], 1)
        class_ = getattr(module, split[-1])
        instance = class_(dict['algo'])
        self.algo = instance
        self.accounts = dict['accounts']



def load_config(config_file):
    with open(config_file, 'r') as f:
        dict = json.load(f)
        return AppConfig(dict)

