from decimal import Decimal

from mm.book import BipolarContainer


class MMParams:
    def __init__(self, config):
        self.price_tolerance = Decimal(config['price_tolerance'])
        self.buried_volume = Decimal(config['buried_volume'])
        self.min_levels = Decimal(config['min_levels'])
        self.liq_behind_exit = Decimal(config['liq_behind_exit'])
        self.liq_behind_entry = BipolarContainer(Decimal(config['liq_behind_entry']['BID']),
                                                 Decimal(config['liq_behind_entry']['ASK']))
        self.order_sizes = BipolarContainer(Decimal(config['order_sizes']['BID']),
                                            Decimal(config['order_sizes']['ASK']))
        self.min_profit = Decimal(config['min_profit'])
        self.min_order_size = Decimal(config['min_order_size'])