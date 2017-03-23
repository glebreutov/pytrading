import React from 'react'
import * as _ from 'lodash'

export default function KV (props) {
  const { data } = props
  const fields = _.keys(data)
  return <table className='kv'>
    <tbody>
    <tr>{fields.map(f => <td key={f}>{f}</td>)}</tr>
    <tr>{fields.map(f => <td key={f + 'v'}>{data[f]}</td>)}</tr>
    </tbody>
  </table>
}
