from decimal import Decimal

from mm.book import Book, Level
from mm.mmparams import MMParams
from mm.pnl import PNL
from posmath.position import Position
from posmath.side import Side


def price_not_better_than(calc_price, ema_price, side):
    sign = (calc_price - ema_price) / abs(calc_price - ema_price)
    if sign == Side.sign(side):
        return ema_price
    else:
        return calc_price


def price_on_a_depth(top_quote, liq_behind, size, min_step=Decimal('0.0001')):
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
        return last_quote[0] + Side.sign(side) * min_step
    else:
        return last_quote[0]


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


def stop_loss_exit_strategy(book: Book, pnl: PNL, config: MMParams, loss=False):
    def volume_behind_order(min_pos: Position):
        sign = Side.sign(min_pos.side())
        return sum([level.volume() for level in book.quote(min_pos.side())
                    if sign * level.price > sign * min_pos.price()])

    pos = pnl.pos
    exit_side = Side.opposite(pos.side())
    depth = config.liq_behind_entry.side(exit_side)
    price = price_on_a_depth(book.quote(exit_side), depth, pos.abs_position())
    # price = calc_price_between_levels(book.quote(Side.opposite(pos.side())), config.liq_behind_exit, )
    add_pos = pos.oppoiste_with_price(price)
    min_margin = pos.opposite_with_margin(config.min_profit)
    remove_pos = pos.oppoiste_with_price(book.quote(pos.side()).price)
    # if (pos + remove_pos + remove_pos.fee_pos(pnl.fee)).balance > pnl.closed_pnl:
    #     return remove_pos, "REMOVE"
    if (pos + add_pos).balance > 0 or loss:
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


def calc_price_between_levels(quote, liq_behind, min_step, place_to_spread=False):
    quote_liq = quote.size
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


def test_calc_price2():
    ask_book_update = [
        [Decimal('1199.9999'),
         Decimal('9.2702250')],
        [Decimal('1200.0000'),
         Decimal('0.1941047')],
        [Decimal('1200.9400'),
         Decimal('0.3393702')],
        [Decimal('1201.8405'),
         Decimal('0.1700418')],
        [Decimal('1202.4201'),
         Decimal('0.3193892')],
        [Decimal('1203.9999'),
         Decimal('0.6336792')],
        [Decimal('1204.2331'),
         Decimal('3.3000000')],
        [Decimal('1204.9268'),
         Decimal('0.7686713')],
        [Decimal('1204.9269'),
         Decimal('0.8288905')],
        [Decimal('1205.0948'),
         Decimal('0.4286218')]
    ]

    book = Book()
    # print(book_update)
    for price, size in ask_book_update:
        book.increment_level(Side.ASK, price, size)

    price = price_on_a_depth(top_quote=book.quote(Side.ASK), liq_behind=Decimal('10'),
                             size=Decimal('0.06'), min_step=Decimal('0.0001'))
    assert price == Decimal('1201.8404')
    print(price)
    price = price_on_a_depth(top_quote=book.quote(Side.ASK), liq_behind=Decimal('0.3'),
                             size=Decimal('0.06'), min_step=Decimal('0.0001'))
    assert price == Decimal('1199.9998')
    print(price)

    price = price_on_a_depth(top_quote=book.quote(Side.ASK), liq_behind=Decimal('10.0337417'),
                             size=Decimal('0.06'), min_step=Decimal('0.0001'))
    assert price == Decimal('1201.8405')
    print(price)

    ask_book_update = [
        [Decimal('1198.9997'),
         Decimal('0.2000000')],
        [Decimal('1199.9899'),
         Decimal('0.1783976')],
        [Decimal('1200.9999'),
         Decimal('0.3191456')],
        [Decimal('1201.1110'),
         Decimal('0.2000000')],
        [Decimal('1201.9999'),
         Decimal('0.6322451')],
        [Decimal('1202.9999'),
         Decimal('0.7686713')],
        [Decimal('1203.9999'),
         Decimal('0.5269789')],
        [Decimal('1204.9999'),
         Decimal('0.6328429')],
        [Decimal('1205.3113'),
         Decimal('0.4665010')],
        [Decimal('1205.4414'),
         Decimal('0.4774178')],
        [Decimal('1205.5296'),
         Decimal('3.3000000')],
        [Decimal('1205.5955'),
         Decimal('0.2916925')],
        [Decimal('1205.5969'),
         Decimal('5.4693747')]]

    book = Book()
    for price, size in ask_book_update:
        book.increment_level(Side.ASK, price, size)

    price = price_on_a_depth(top_quote=book.quote(Side.ASK), liq_behind=Decimal('0.89'),
                             size=Decimal('0.06'), min_step=Decimal('0.0001'))
    print(price)

    bid_book_update = [
        [Decimal('1196.9317'),
         Decimal('0.0600000')],
        [Decimal('1196.9316'),
         Decimal('0.0100000')],
        [Decimal('1196.9301'),
         Decimal('2.2102000')],
        [Decimal('1196.7188'),
         Decimal('5.1313376')],
        [Decimal('1196.7187'),
         Decimal('23.440256')]
    ]
    for price, size in bid_book_update:
        book.increment_level(Side.BID, price, size)

    price = price_on_a_depth(top_quote=book.quote(Side.BID), liq_behind=Decimal('0.89'),
                             size=Decimal('0.06'), min_step=Decimal('0.0001'))
    print(price)

# test_calc_price2()
