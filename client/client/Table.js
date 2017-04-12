import * as _ from 'lodash'
import React from 'react'

export default function Table (props) {
  let { items, orderBy, title } = props
  const order = orderBy.startsWith('-') ?
    [orderBy.replace('-', ''), 'desc'] :
    [orderBy, 'asc']
  items = _.orderBy(items, order[0], order[1])

  let keys = [];
  items.forEach(row => keys = _.union(keys, _.keys(row)));

  return <table className='table'>
    <tbody>
    <tr><td colSpan={keys.length} style={{textAlign: 'center'}}>{title}</td></tr>
    <tr>{keys.map(k => <td key={k}>{k}</td>)}</tr>
    {items.map((row, rowIndex) => <tr key={rowIndex}>
      {keys.map(k => <td key={k + rowIndex}>{row[k]}</td>)}
    </tr>)}
    </tbody>
  </table>
}
