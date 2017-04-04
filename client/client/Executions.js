import * as _ from 'lodash'
import React from 'react'

export default function Executions (props) {
  let { executions } = props
  executions = _.orderBy(executions, 'timestamp', 'desc')
  const fields = ['time', 'order_id', 'side', 'price', 'size']
  return <table className='order-table'>
    <tbody>
    <tr><td colSpan={fields.length} style={{textAlign: 'center'}}>Executions</td></tr>
    <tr>{fields.map(f => <td key={f}>{f}</td>)}</tr>
    {executions.map((e, i) => <tr key={i}>
      {fields.map(f => <td key={f + i}>{e[f]}</td>)}
    </tr>)}
    </tbody>
  </table>
}
