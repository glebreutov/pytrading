import {OrderedMap, Map} from 'immutable'

/**
 * @typedef {Object} Level
 * @property {Number} price
 * @property {Number} size
 */

/**
 * @typedef {OrderedMap.<Number, Number>} LevelList
 */

function assert (condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

export default class Book {
  static SIDE_BID = 'bid'
  static SIDE_ASK = 'ask'
  static priceComparators = {
    [Book.SIDE_ASK]: (a, b) => a > b ? 1 : a < b ? -1 : 0,
    [Book.SIDE_BID]: (a, b) => a < b ? 1 : a > b ? -1 : 0,
  }
  static priceIsBetter (side, candidate, reference) {
    return Book.priceComparators[side](candidate, reference) < 0
  }

  constructor (baseDigits, quoteDigits) {
    /*
     * best price comes first, numbers are integers (srcVal * 10^digits)
     * bid (desc): {101: 10, 100: 1.5, ... }
     * ask (asc) : {102: 1, 103: 20, ... }
     */
    /** @type {Map.<string, LevelList>} */
    this.levels = Map()
      .set(Book.SIDE_BID, OrderedMap())
      .set(Book.SIDE_ASK, OrderedMap())

    const baseMultiplier = Math.pow(10, baseDigits)
    this.toBaseInt = srcVal => Math.round(srcVal * baseMultiplier)
    this.fromBaseInt = int => int / baseMultiplier
    const quoteMultiplier = Math.pow(10, quoteDigits)
    this.toQuoteInt = srcVal => Math.round(srcVal * quoteMultiplier)
    this.fromQuoteInt = int => int / quoteMultiplier
  }

  _setLevelSize (side, price, size) {
    assert(side === Book.SIDE_BID || side === Book.SIDE_ASK, 'ArgumentException: side')
    assert(size >= 0 && price > 0, `ArgumentException: ${size < 0 ? 'size' : 'price'}`)

    this.levels = this.levels.updateIn([side], levels =>
      size === 0
        ? levels
          .delete(price)
        : levels
          .set(price, size)
          .sortBy((v, k) => k, Book.priceComparators[side])
    )
  }

  setLevelSize (side, price, size) {
    this._setLevelSize(side, this.toBaseInt(price), this.toQuoteInt(size))
  }

  _incrementLevel (side, price, size) {
    const levelSize = this.levels.getIn([side, price])
    if (!levelSize && size <= 0) {
      console.error(`incrementLevel ${price}/${size} failed: level not found`)
      return
    }
    if (size < 0 && (levelSize + size) < 0) {
      console.warn(`incrementLevel ${price}/${size} warning: decremented too much`)
      size = -levelSize
    }
    this._setLevelSize(side, price, levelSize + size)
  }

  incrementLevel (side, price, size) {
    this._incrementLevel(side, this.toBaseInt(price), this.toQuoteInt(size))
  }

  /**
   * Shows the amount of base currency that will be needed so targetPrice is the best price.
   * A newcoming order is considered to be the last one to execute, so existing prices
   * are "better" than targetPrice even if they are equal.
   * @param side
   * @param targetPrice
   * @return {Number|null} base currency amount or null, if the book was empty
   */
  getDistance (side, targetPrice) {
    targetPrice = this.toBaseInt(targetPrice)
    let distance = null
    // default reduce() does not support breaks
    this.levels.get(side).forEach((size, levelPrice) => {
      if (Book.priceIsBetter(side, targetPrice, levelPrice)) {
        if (distance === null) { distance = 0 }
        // break
        return false
      }
      distance += this.fromQuoteInt(size) * this.fromBaseInt(levelPrice)
    })
    return distance
  }

  /**
   *
   * @param side
   * @param amount
   * @return {Number|null} price or null, if the book was empty
   */
  getPriceAtDistance (side, amount) {
    let price = null
    this.levels.get(side).forEach((size, levelPrice) => {
      price = this.fromQuoteInt(levelPrice)
      amount -= this.fromBaseInt(size) * price
      if (amount < 0) {
        // break
        return false
      }
    })
    return price
  }

  /**
   *
   * @param side
   * @param referencePrice
   * @return {Level}
   */
  getNextBetterLevel (side, referencePrice) {
    referencePrice = this.toBaseInt(referencePrice)
    const found = this.levels.get(side)
      .findLastEntry((size, levelPrice) => Book.priceIsBetter(side, levelPrice, referencePrice))
    return found ? {
      price: this.fromBaseInt(found[0]),
      size: this.fromQuoteInt(found[1]),
    } : null
  }

  /**
   *
   * @param side
   * @param referencePrice
   * @return {Level}
   */
  getNextWorseLevel (side, referencePrice) {
    referencePrice = this.toBaseInt(referencePrice)
    const found = this.levels.get(side)
      .findEntry((size, levelPrice) => Book.priceIsBetter(side, referencePrice, levelPrice))
    return found ? {
      price: this.fromBaseInt(found[0]),
      size: this.fromQuoteInt(found[1]),
    } : null
  }
}
