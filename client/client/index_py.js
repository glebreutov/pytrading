import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay from './BookDisplay'

const bookData = {
  book: [],
  myOrders: [],
}

const socket = new WebSocket('ws://10.115.66.134:5678')
const send = obj => socket.send(JSON.stringify(obj))
const wsBookToBookEntry = side => wsEntry => ({side, price: wsEntry[0], size: wsEntry[1]})
const wsOrderToBookEntry = wsEntry => ({side: wsEntry[2] === 'B' ? 'bid' : 'ask', price: wsEntry[0], size: wsEntry[1]})

// Connection opened
socket.addEventListener('open', () => console.log('socket open'))
socket.addEventListener('message', (event) => {
  console.log(event.data)
  const msg = JSON.parse(event.data)
  if (msg.e === 'book') {
    bookData.book = [].concat(
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

const sendRMNormal = () => send({'e': 'rm', 'new_status': 'NORMAL'})
const sendRMCancelAll = () => send({'e': 'rm', 'new_status': 'CANCELL_ALL'})

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
