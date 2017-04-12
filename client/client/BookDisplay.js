import React from 'react'
import * as _ from 'lodash'

// indexes
const price = 0
const size = 1
const side = 2
export const toLevel = (side, price, size) => [price, size, side]

export default function BookDisplay (props) {
  const { bookLevels, myOrders, reverse, showOnlySide } = props

  const consolidated = _.chain(bookLevels)
    .map(level => {
      const my = _.find(myOrders, order => order[price].eq(level[price]))
      return {
        side: level[side],
        price: level[price],
        size: level[size],
        mySize: my ? my[size] : null,
      }
    })
    .concat(myOrders.map(myLevel => ({
      side: myLevel[side],
      price: myLevel[price],
      size: null,
      mySize: myLevel[size],
    })))
    .filter(c => showOnlySide ? c.side === showOnlySide : true)
    .sortBy(c => reverse ? -Number(c.price) : Number(c.price))
    .sortedUniqBy(c => c.price.valueOf())
    .value()
  // console.log(consolidated)
  return <table className='book table'>
      <tbody>
      {consolidated.map((level, index) => [
        ((index === 0) || (index > 0 && (consolidated[index - 1].side !== level.side))) &&
        <tr><td colSpan='3' style={{textAlign: 'center'}}>{level.side}</td></tr>,
        <tr key={level.price}>
          <td>{level.price.toFixed(4)}</td>
          <td>{(level.size && level.size.toFixed(8)) || ' '}</td>
          <td>{(level.mySize && level.mySize.toFixed(8)) || ' '}</td>
        </tr>,
      ])}
      </tbody>
    </table>
}
