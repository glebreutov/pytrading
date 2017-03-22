import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay, {toLevel} from './BookDisplay'
import Big from 'big.js/big'

const bookData = {
  bookLevels: [],
  myOrders: [],
}

const state = {
  error: null,
  connected: false,
}

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
  render(state, bookData)
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
    render(state, bookData)
  }
})
socket.addEventListener('error', (err) => {
  state.error = err
  state.connected = false
  render(state, bookData)
})
socket.addEventListener('close', (event) => {
  state.connected = false
  console.log('ws connection closed', event)
  if (!event.wasClean) {
    state.error = event
  }
  render(state, bookData)
})

render(bookData)

function render (state, data) {
  ReactDOM.render(
    <div>
      <h1>(╯°□°）╯︵ ┻━┻</h1>
      {!state.connected && !state.error && '...'}
      {state.error && <div className='error'>Error {state.error.code}</div>}
      {state.connected && <div>
        <BookDisplay {...data} />
          <div className='controls'>
            <button onClick={sendRMNormal}>Normal</button>
            <button onClick={sendRMCancelAll}>Cancell All</button>
          </div>
      </div>}
    </div>,
    document.getElementById('app')
  )
}
