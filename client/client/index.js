import React from 'react'
import ReactDOM from 'react-dom'
import BookDisplay from './BookDisplay'
import crypto from 'crypto'
import Book from './Book'

function createSignature (timestamp, apiKey, apiSecret) {
  const hmac = crypto.createHmac('sha256', apiSecret)
  hmac.update(timestamp + apiKey)
  return hmac.digest('hex')
}

function createAuthRequest (apiKey, apiSecret) {
  const timestamp = Math.floor(Date.now() / 1000)
  const args = {
    e: 'auth',
    auth: {
      key: apiKey,
      signature: createSignature(timestamp, apiKey, apiSecret),
      timestamp: timestamp,
    },
  }
  return JSON.stringify(args)
}

const apiKey = 'LCnB7YgzC5qEyGeyULOCsjBzqHA'
const apiSecret = 'Tvr8j6heHcb3ixDMsxNCKzmkIHA'

const bookData = {
  book: [],
  myOrders: [],
}

const bookSubscription = {
  'e': 'order-book-subscribe',
  'data': {
    'pair': [
      'BTC',
      'USD',
    ],
    'subscribe': true,
    'depth': 0,
  },
  'oid': '1435927928274_3_order-book-subscribe',
}

const archivedOrders = {
  'e': 'archived-orders',
  'data': {
    'pair': [
      'BTC',
      'USD',
    ],
    'limit': 100,
  },
  'oid': '1435927928274_15_archived-orders',
}

const openOrders = {
  'e': 'open-orders',
  'data': {
    'pair': [
      'BTC',
      'USD',
    ],
  },
  'oid': '1435927928274_6_open-orders',
}

const socket = new WebSocket('wss://ws.cex.io/ws')
const send = (obj) => socket.send(JSON.stringify(obj))
const book = new Book(4, 8)

const updateBook = (bids, asks) => {
  var t0 = performance.now()
  bids.forEach(bid => book.setLevelSize(Book.SIDE_BID, bid[0], bid[1]))
  asks.forEach(ask => book.setLevelSize(Book.SIDE_ASK, ask[0], ask[1]))

  var t1 = performance.now()
  console.warn(`${bids.length + asks.length} book.setLevel() calls took ${(t1 - t0).toFixed(3)} ms`)
  bookData.book = []
  const push = (side) => (size, price) => {
    bookData.book.push({
      side,
      price: book.fromBaseInt(price),
      size: book.fromQuoteInt(size),
    })
  }
  book.levels.get(Book.SIDE_BID).take(10).forEach(push(Book.SIDE_BID))
  book.levels.get(Book.SIDE_ASK).take(10).forEach(push(Book.SIDE_ASK))

  var t2 = performance.now()
  console.warn(`book -> bookData took ${(t2 - t1).toFixed(3)} ms`)

  render(bookData)
}

// Connection opened
socket.addEventListener('open', () => socket.send(createAuthRequest(apiKey, apiSecret)))
socket.addEventListener('message', (event) => {
  console.log(event.data)
  const msg = JSON.parse(event.data)
  if (msg.e === 'auth' && msg.ok === 'ok') {
    send(bookSubscription)
    // send(archivedOrders)
  }
  if (msg.e === 'ping') {
    send({e: 'pong'})
  }
  if ((
    msg.e === 'order-book-subscribe' && msg.ok === 'ok') ||
    msg.e === 'md_update'
  ) {
    updateBook(msg.data.bids, msg.data.asks)
  }
})
socket.addEventListener('error', (error) => console.error(error))
socket.addEventListener('close', (event) => console.log('ws connection closed', event))

function render (data) {
  ReactDOM.render(
    <div>
      <h1>(╯°□°）╯︵ ┻━┻</h1>
      <BookDisplay {...data} />
    </div>,
    document.getElementById('app')
  )
}

render(bookData)
