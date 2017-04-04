import * as _ from 'lodash'
import React from 'react'

export default function Log (props) {
  let { entries } = props
  entries = _.orderBy(entries, 'timestamp', 'desc')
  const fields = ['time', 'event', 'details']
  return <table className='order-table'>
    <tbody>
    <tr><td colSpan={fields.length} style={{textAlign: 'center'}}>Log</td></tr>
    <tr>{fields.map(f => <td key={f}>{f}</td>)}</tr>
    {entries.map((e, i) => <tr key={i}>
      {fields.map(f => <td key={f + i}>{e[f]}</td>)}
    </tr>)}
    </tbody>
  </table>
}
