import React from 'react'
import * as _ from 'lodash'

export default function BookDisplay (props) {
  const { book, myOrders } = props

  const consolidated = _.chain(book)
    .map(level => {
      const my = _.find(myOrders, {price: level.price})
      return {
        ...level,
        mySize: my ? my.size : null,
      }
    })
    .concat(myOrders.map(myLevel => ({
      ...myLevel,
      size: null,
      mySize: myLevel.size,
    })))
    .uniqBy('price')
    .sortBy('price')
    .value()
  // console.log(consolidated)
  return <table className='order-table'>
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
