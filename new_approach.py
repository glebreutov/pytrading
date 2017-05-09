from decimal import Decimal

from mm.app_config import VenueConfig
from mm.book import BipolarContainer, Level
from mm.pnl import PNL
from posmath.position import Position
from posmath.side import Side


class HedgeConfig:
    def __init__(self, d):
        self.max_pos = Decimal(d['max_pos'])
        self.liq_behind = BipolarContainer(bid=Decimal(d['liq_behind']['BID']),
                                           ask=Decimal(d['liq_behind']['ASK']))
        self.order_size = BipolarContainer(bid=Decimal(d['order_size']['BID']),
                                           ask=Decimal(d['order_size']['ASK']))
        self.ema_work_perc = Decimal(d['ema_work_perc'])
        self.hedge_perc = Decimal(d['hedge_perc'])
        self.refresh_timeout = Decimal(d['refresh_timeout'])
        self.price_tolerance = Decimal(d['price_tolerance'])
        self.min_levels = Decimal(d['min_levels'])


def price_on_a_depth(top_quote, size, liq_behind, vc: VenueConfig):
    quote_array = []
    quote_liq = Decimal('0')
    side = top_quote.side
    liq_adj = liq_behind - size
    prev_price = Decimal('0')

    for quote in top_quote:
        quote_liq += quote.size
        quote_array.append((quote.price, quote.size, quote_liq, abs(prev_price - quote.price)))
        prev_price = quote.price
        if quote_liq >= liq_adj:
            break

    last_quote = quote_array[-1]
    if last_quote[2] > liq_adj:
        return last_quote[0] + Side.sign(side) * vc.tick_size
    else:
        return last_quote[0]


def enter_ema(quote: Level, ema: Decimal, ema_work_perc, vc: VenueConfig):

    sign = Decimal(Side.sign(quote.side))

    def calc_ema_price():
        return round(Decimal(ema - sign * (ema / 100 * ema_work_perc)), 4)

    def stick_to_quote(price):
        try:
            under_price = next((x.price for x in quote if sign * x.price - sign * price <= 0))
            return under_price + sign * vc.tick_size if under_price != price else under_price
        except StopIteration:
            return price

    return stick_to_quote(calc_ema_price())


def ema_constraint(depth_price, ema_price, side):
    sign = Side.sign(side)

    # ema 100 price 101 side bid
    delta = sign * ema_price - sign * depth_price
    return (ema_price, "EMA") if delta < 0 else (depth_price, "ENTER")


# def exit_order(quote, pos: Position, exit_depth, vc: VenueConfig):
#     price = price_on_a_depth(quote, pos.abs_position(), exit_depth, vc)
#
#     add_pos = pos.oppoiste_with_price(price)
#     min_margin = bound_price_to_lower_quote(quote, pos.opposite_with_margin(vc.tick_size), vc.tick_size)
#
#     if (pos + add_pos).balance > 0:
#         return add_pos, "QUOTE"
#     else:
#         return min_margin, "ZERO PROFIT"


def hedge_position(prior_pos, target_price, enter_price):
    x = (target_price * prior_pos.position() - prior_pos.balance) / (enter_price - target_price)
    return Position(price=enter_price, pos=x)


def hedge_positon_size(prior_pos, target_price, hedge_size):
    x = (target_price * (prior_pos.abs_position() + hedge_size) - prior_pos.price() * prior_pos.abs_position()) / hedge_size
    return Position(price=x, pos=hedge_size, side=prior_pos.side())


def bound_pos_to_lower_quote(quote: Level, pos: Position, tick_size):
    lower_quote_price = bound_price_to_lower_quote(quote, pos.price(), tick_size)
    return Position(side=pos.side(), price=lower_quote_price, pos=pos.abs_position())


def bound_price_to_lower_quote(quote: Level, price: Decimal, tick_size):
    def price_equlas_quote():
        for x in quote:
            if x.price == price:
                return True
        return False
    if price_equlas_quote():
        return price
    try:
        if quote.side == Side.BID:
            stick_price = max([x.price for x in quote if x.price < price]) + tick_size
        else:
            stick_price = min([x.price for x in quote if x.price > price]) - tick_size
        return stick_price
    except ValueError:
        return price

    # return max_quote - tick_size if pos


def adjusted_size(order_size, order_side, pos):
    pos_side = Side.side(pos)
    if pos_side == order_side:
        return order_size - abs(pos)
    else:
        return order_size + abs(pos)


def enter_hedge(pnl: PNL, quote: Level, cfg: HedgeConfig, vc: VenueConfig):
    side = quote.side
    pos = pnl.pos
    order_size = cfg.order_size.side(side)
    if pos.abs_position() < vc.min_order_size:
        # depth or ema
        order_size = adjusted_size(order_size, side, pos.abs_position())
        method, price = depth_ema_price(cfg, order_size, pnl, quote, side, vc)
        return Position(pos=order_size, side=side, price=price), method
    elif Side.opposite(pos.side()) == side and pos.abs_position() >= vc.min_order_size:
        # exit order
        # depth or zero
        method, price = depth_ema_price(cfg, order_size, pnl, quote, side, vc)

        add_pos = pos.oppoiste_with_price(price)
        min_margin = pos.opposite_with_margin(vc.tick_size)
        min_margin = bound_pos_to_lower_quote(quote, min_margin, vc.tick_size)

        if (pos + add_pos).balance > 0:
            return add_pos, "QUOTE"
        else:
            return min_margin, "MIN PROFIT"
    elif pos.side() == side and cfg.max_pos - pos.abs_position() >= vc.min_order_size:
        #depth
        #hedge
        #order_size = adjusted_size(order_size, side, pos.abs_position())
        method, price = depth_ema_price(cfg, order_size, pnl, quote, side, vc)

        order_size = min(order_size, cfg.max_pos - pos.abs_position())
        depth_pos = Position(pos=order_size, side=side, price=price)
        hedge_pos = hedge_positon_size(pos, pos.price() * (1 + cfg.hedge_perc), order_size)
        hedge_pos = bound_pos_to_lower_quote(quote, hedge_pos, vc.tick_size)
        if (side == Side.BID and hedge_pos.price() < depth_pos.price()) \
                or (side == Side.ASK and hedge_pos.price() > depth_pos.price()):
            return hedge_pos, "HEDGE HEDGE"
        else:
            return depth_pos, "HEDGE DEPTH"

    else:
        #zero
        return Position(side=side, pos=0, balance=0), "CANCEL"


def depth_ema_price(cfg, order_size, pnl, quote, side, vc):
    depth_price = price_on_a_depth(quote, order_size, cfg.liq_behind.side(side), vc)
    ema_price = enter_ema(quote=quote, ema=pnl.ema.calc_ema(), ema_work_perc=cfg.ema_work_perc, vc=vc)
    ema_price = bound_price_to_lower_quote(quote, ema_price, vc.tick_size)
    price, method = ema_constraint(depth_price, ema_price, side)
    return method, price
