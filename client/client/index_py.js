import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay, {toLevel} from './BookDisplay'
import Executions from './Executions'
import KV from './KV'
import Big from 'big.js/big'
import * as _ from 'lodash'

const bookData = {
  bookLevels: [],
  myOrders: [],
}

const state = {
  error: null,
  connected: false,
  executions: [],
  pnl: {},
}

// const socket = new WebSocket('ws://10.115.66.153:5678')
const socket = new WebSocket('ws://127.0.0.1:5678')
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
socket.addEventListener('message', (event) => {
  console.log(event.data)
  const msg = JSON.parse(event.data)
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
  }
  if (msg.e === 'exec') {
    state.executions = state.executions.concat(msg.details)
  }
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
      {!state.connected && !state.error && '...'}
      {state.error && <div className='error'>Error {state.error.code}</div>}
      {!state.connected && '- not connected -'}
      <div>
        <div className='controls'>
          <KV data={state.pnl} />
        </div>
        <div className='controls'>
          <button onClick={sendRMNormal}>Normal</button>
          <button onClick={sendRMCancelAll}>Cancell All</button>
        </div>
        <BookDisplay {...bookData} showOnlySide='ask' />
        <BookDisplay {...bookData} showOnlySide='bid' reverse={true} />
        <Executions executions={state.executions} />
      </div>
    </div>,
    document.getElementById('app')
  )
}
