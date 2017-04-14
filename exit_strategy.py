from decimal import Decimal

from mm.book import Book, Level
from mm.mmparams import MMParams
from mm.pnl import PNL
from posmath.position import Position
from posmath.side import Side


def calc_price_for_depth(quote: Level, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price + Side.side(quote.side) * Decimal('0.0001')

# pos is B
# we wanna S
# passsive - place order to S list
# agressive order is to place on B


def stop_loss_exit_strategy(book: Book, pos: Position, config: MMParams):
    def volume_behind_order(min_pos: Position):
        sign = Side.sign(min_pos.side())
        return sum([level.volume() for level in book.quote(min_pos.side())
                    if sign * level.price > sign * min_pos.price()])

    price = calc_price_between_levels(book.quote(Side.opposite(pos.side())), config.liq_behind_exit, Decimal('0.0001'))
    add_pos = pos.oppoiste_with_price(price)
    min_margin = pos.opposite_with_margin(config.min_profit)
    remove_pos = pos.oppoiste_with_price(book.quote(pos.side()).price)
    if (pos + remove_pos).balance > abs((remove_pos.balance / 100) * Decimal('0.19')):
        return remove_pos, "REMOVE"
    if (pos + add_pos).balance > 0:
        return add_pos, "QUOTE"
    # elif volume_behind_order(min_margin) >= config.buried_volume:
    #     return add_pos, "STOP LOSS"
    else:
        return min_margin, "MIN PROFIT"


def remove_exit_price_strategy(book: Book, pos: Position, config: MMParams, fee=Decimal(0.3)):
    # pos, last_price = remove_price(book.quote(pos.side()), pos)
    # if pos.balance > 0:
    #     remove_pos = pos.oppoiste_with_price(last_price)
    # print("fee " + str(pos * Decimal('0.3')))
    remove_pos = pos.oppoiste_with_price(book.quote(pos.side()).price)
    remove_pos_wfee = Position(pos=remove_pos.position(), balance=remove_pos.balance + (remove_pos.balance / 100) * fee)
    add_pos = pos.oppoiste_with_price(book.quote(Side.opposite(pos.side())).price)
    fee_ = remove_pos * Decimal(fee / 100)
    fin_pos = pos + remove_pos
    if (pos + remove_pos_wfee).balance > 0:
        return remove_pos
    elif (pos + add_pos).balance > 0:
        return add_pos
    else:
        return pos.opposite_with_margin(config.min_profit)


def specific_margin_price(entry_price, entry_side, margin, entry_commisiion=0, exit_commision=0):
    return entry_price \
           + Side.sign(entry_side) * (margin + entry_commisiion) \
           - Side.sign(entry_side) * exit_commision


def cost_of_remove_order(book: Book, side, amount, fee):
    added_vol = 0
    cost = 0
    last_price = 0
    quote = book.quote(side)
    while added_vol < amount:
        added_vol += quote.size
        cost += quote.price * quote.size
        last_price = quote.price
        if quote.next_level is not None:
            quote = quote.next_level
        elif added_vol < amount:
            return Decimal('99999999999999'), -1

    return cost + (cost / 100) * fee, last_price


def calc_price_between_levels(quote, liq_behind, min_step, place_to_spread=False):
    quote_liq = quote.size

    # dt = abs(0 - quote.price)
    dt = abs(0 - quote.price) if place_to_spread else 0
    while quote_liq < liq_behind:
        dt = abs(quote.price - quote.next_level.price)
        quote = quote.next_level
        quote_liq += quote.size

    if dt > min_step:
        return quote.price + Side.sign(quote.side) * min_step
    else:
        return quote.price


def calc_price(quote, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price
