import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay, {toLevel} from './BookDisplay'
import Executions from './Executions'
import Log from './Log'
import KV from './KV'
import Big from 'big.js/big'
import * as _ from 'lodash'

const bookData = {
  bookLevels: [],
  myOrders: [],
}
const lsKey = '__state_v01'
const state = localStorage.getItem(lsKey) ? JSON.parse(localStorage.getItem(lsKey)) : {
  error: null,
  connected: false,
  executions: [],
  log: [],
  pnl: {},
}
const url = `ws://${window.location.hash.replace('#', '') || '127.0.0.1:5678'}`
const socket = new WebSocket(url)
const send = obj => socket.send(JSON.stringify(obj))
const wsBookToBookEntry = side => wsEntry => toLevel(side, Big(wsEntry[0]), Big(wsEntry[1]))
const wsOrderToBookEntry = wsEntry => toLevel(wsEntry[2] === 'B' ? 'bid' : 'ask', Big(wsEntry[0]), Big(wsEntry[1]))
const sendRMNormal = () => send({'e': 'rm', 'new_status': 'NORMAL'})
const sendRMCancelAll = () => send({'e': 'rm', 'new_status': 'CANCELL_ALL'})

// Connection opened
socket.addEventListener('open', () => {
  state.connected = true
  state.error = null
  render()
})
socket.addEventListener('message', function processEvent (event) {
  console.log(event.data)
  let msg
  try {
    msg = JSON.parse(event.data)
  } catch (e) {
    debugger;
    return
  }
  if (msg.e === 'book') {
    bookData.bookLevels = [].concat(
      msg.details['B'].map(wsBookToBookEntry('bid')),
      msg.details['S'].map(wsBookToBookEntry('ask')),
    )
    render(bookData)
  }
  if (msg.e === 'orders') {
    bookData.myOrders = msg.details.map(wsOrderToBookEntry)
    render()
  }
  if (msg.e === 'pnl') {
    state.pnl = msg.details
    document.title = (msg.details['closed PNL'] || '') + ' (╯°□°）╯︵ ┻━┻'
  }
  if (msg.e === 'exec') {
    state.executions = state.executions.concat(msg.details)
  }

  if (msg.e === 'important_events') {
    msg.details.forEach((t) => processEvent({data: t}))
  }
  if (msg.e === 'warning') {
    // time, event, details
    state.log = state.log.concat(msg)
  }

  localStorage.setItem(lsKey, JSON.stringify(state))
})
socket.addEventListener('error', (err) => {
  state.error = err
  state.connected = false
  render()
})
socket.addEventListener('close', (event) => {
  state.connected = false
  console.log('ws connection closed', event)
  if (!event.wasClean) {
    state.error = event
  }
  render()
})

render()

function render () {
  ReactDOM.render(
    <div>
      <h1>(╯°□°）╯︵ ┻━┻</h1>
      <div className='controls'>
        {!state.connected && !state.error && <div>connecting...</div>}
        {state.error && <div className='error'>Error {state.error.code}</div>}
        {state.connected ? `- connected to ${url} -` : `- not connected to ${url} -`}
      </div>
      <div>
        <div className='controls'>
          <KV data={state.pnl} />
        </div>
        <div className='controls'>
          <button onClick={sendRMNormal}>Normal</button>
          <button onClick={sendRMCancelAll}>Cancell All</button>
        </div>
        <table className='tables'>
          <tbody>
            <tr>
              <td><BookDisplay {...bookData} showOnlySide='ask' /></td>
              <td><BookDisplay {...bookData} showOnlySide='bid' reverse={true} /></td>
              <td><Executions executions={state.executions} /></td>
              <td><Log entries={state.log} /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>,
    document.getElementById('app')
  )
}
