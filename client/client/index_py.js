import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay, {toLevel} from './BookDisplay'
import Big from 'big.js/big'

const bookData = {
  bookLevels: [],
  myOrders: [],
}

const socket = new WebSocket('ws://10.115.66.134:5678')
const send = obj => socket.send(JSON.stringify(obj))
const wsBookToBookEntry = side => wsEntry => toLevel(side, Big(wsEntry[0]), Big(wsEntry[1]))
const wsOrderToBookEntry = wsEntry => toLevel(wsEntry[2] === 'B' ? 'bid' : 'ask', Big(wsEntry[0]), Big(wsEntry[1]))
const sendRMNormal = () => send({'e': 'rm', 'new_status': 'NORMAL'})
const sendRMCancelAll = () => send({'e': 'rm', 'new_status': 'CANCELL_ALL'})

// Connection opened
socket.addEventListener('open', () => console.log('socket open'))
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
    render(bookData)
  }
})
socket.addEventListener('error', (error) => console.error(error))
socket.addEventListener('close', (event) => console.log('ws connection closed', event))

render(bookData)

function render (data) {
  ReactDOM.render(
    <div>
      <h1>(╯°□°）╯︵ ┻━┻</h1>
      <BookDisplay {...data} />
      <div className='controls'>
        <button onClick={sendRMNormal}>Normal</button>
        <button onClick={sendRMCancelAll}>Cancell All</button>
      </div>
    </div>,
    document.getElementById('app')
  )
}
