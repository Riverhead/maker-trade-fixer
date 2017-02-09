#! /usr/bin/python3

import json
from web3 import Web3, RPCProvider
from operator import itemgetter
import time
import sys

precision = 1000000000000000000
cleanup_rounding = 1000 #Clean up the very insignificant digits that collect due to rounding errors.
mkr_addr = "0xc66ea802717bfb9833400264dd12c2bceaa34a6d"
weth_addr = "0xecf8f87f810ecf450940c9f60066b4a7a501d6a7" 
geth_addr = "0xa74476443119A942dE498590Fe1f2454d7D4aC0d"
market_addr = "0xa1B5eEdc73a978d181d1eA322ba20f0474Bb2A25"
acct_owner = "0x6E39564ecFD4B5b0bA36CD944a46bCA6063cACE5"

web3rpc = Web3(RPCProvider())
web3rpc.eth.defaultAccount = acct_owner
web3rpc.eth.defaultBlock = "latest"

logFile = open('maker-matcher.json', 'a+')

def print_log( log_type, entry ):
      entry = '[{epoch:' + str(round(time.time(), 4)) + ',"' + log_type + '":' + entry + '}],\n'
      logFile.write( entry )

def fix_books(precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
      print_log('log','{"ETH":%f,"MKR":%f}' % (buy_book_amount/precision, sell_book_amount/precision))
      try:
        print("Submitting Buy Book order", end='', flush=True )
        if market_contract.call().buy(bid_id, buy_book_amount):
            try:
              result_bb = market_contract.transact().buy(bid_id, buy_book_amount)
              print_log('log','{"buy_tx":"%s"}' % (result_bb))
              while web3rpc.eth.getTransactionReceipt(result_bb) is None:
                 print(".", end='', flush=True) 
                 time.sleep(2)
              print("")
            except:
              print_log('ERR','"Failed Buy Book transaction"')
              return False
        else:
              print_log('ERR','"Failed Buy Book transaction"')
              return False
      except:
        print_log('ERR','"Failed pre Buy Book check, trying Sell Book"')
        return False

      try:
        print("Submitting Sell Book Order", end='', flush=True)
        if market_contract.call().buy(ask_id, sell_book_amount):
            try: 
              result_sb = market_contract.transact().buy(ask_id, sell_book_amount)
              print_log('log','{"sell_tx":"%s"}' % (result_sb))
              while web3rpc.eth.getTransactionReceipt(result_sb) is None:
                 print(".", end='', flush=True) 
                 time.sleep(2)
              print("")
              return True
            except:
              print_log('ERR','"Failed Sell Book transaction"')
              return False
        else:
              print_log('ERR','"Failed Sell Book transaction"')
              return False
      except:
        print_log('ERR','"Failed Sell Book order"')
        return False

with open('market.abi', 'r') as abi_file:
  abi_json = abi_file.read().replace('\n','')
abi = json.loads(abi_json)
market_contract = web3rpc.eth.contract(abi, address=market_addr)


with open('erc20.abi', 'r') as abi_file:
  abi_json = abi_file.read().replace('\n','')
abi = json.loads(abi_json)
weth_contract = web3rpc.eth.contract(abi, address=weth_addr)
mkr_contract = web3rpc.eth.contract(abi, address=mkr_addr)

match_found = False

while [ not match_found ]:
  weth_balance = float(weth_contract.call().balanceOf(acct_owner))/precision
  mkr_balance  = float(mkr_contract.call().balanceOf(acct_owner))/precision

  last_offer_id = market_contract.call().last_offer_id()
  
  id = 0
  offers = []
  
  while id <  last_offer_id + 1:
    offers.append(market_contract.call().offers(id))
    id = id + 1
  
  print("\nBalances: %0.5f WETH - %0.5f MKR\n" % (weth_balance, mkr_balance))
  #print("There are %i offers" % last_offer_id)
  
  id=0
  
  buy_orders = []
  sell_orders = []
  
  for offer in offers:
    valid = offer[5]
    if valid:
      sell_how_much = float(offer[0]) / precision
      sell_which_token = offer[1]
      buy_how_much = float(offer[2]) / precision
      buy_which_token = offer[3]
      owner = offer[4][2:8]
  
      if sell_which_token == mkr_addr and buy_which_token == weth_addr:
        sell_orders.append([id, sell_how_much, buy_how_much/sell_how_much, buy_how_much, owner])
  
      if sell_which_token == weth_addr and buy_which_token == mkr_addr:
        buy_orders.append([id, buy_how_much, sell_how_much/buy_how_much, buy_how_much, owner])
    id = id + 1
  
  #Sort the order books
  buy_orders.sort(key=itemgetter(2), reverse=True)
  bid_id = int(buy_orders[0][0])
  bid    = float(buy_orders[0][2])
  bid_qty     = float(buy_orders[0][1]) 
  print ("Highest bid is for %0.5f MKR @ %0.5f ETH/MKR" % (bid_qty,bid))
  
  sell_orders.sort(key=itemgetter(2), reverse=False)
  ask_id = int(sell_orders[0][0])
  ask = float(sell_orders[0][2])
  ask_qty  = float(sell_orders[0][1]) 
  print ("Lowest ask is for %0.5f MKR @ %0.5f ETH/MKR" % (ask_qty,ask))
  
  #Make sure we have enough allowance
  if float(weth_contract.call().allowance(acct_owner, market_addr)) < 1:
    result = weth_contract.call().approve(acct_owner, int(10000*precision))
    #print ("Update allowance: %s" % result)
    while weth_contract.call().allowance(weth_addr, market_addr) < 0.1:
      print("Waiting for allowance to be applied")
      time.sleep(3)
  
  if float(mkr_contract.call().allowance(acct_owner, market_addr)) < 1:
    result = mkr_contract.call().approve(acct_owner, int(10000*precision))
    #print ("Update allowance: %s" % result)
    while mkr_contract.call().allowance(mkr_addr, market_addr) < 0.1:
      print("Waiting for allowance to be applied")
      time.sleep(3)
  
  if round(bid,5) >= round(ask,5):
    match_found = True
    print("Match found")
    #print("\nAction needed!")
    if weth_balance < ask_qty:
      ask_qty = weth_balance
    if mkr_balance < bid_qty:
      bid_qty = mkr_balance
    if bid_qty < ask_qty:
      qty = bid_qty
    else:
      qty = ask_qty
    qty = round(qty, 5)
    bid = round(bid, 5)
    ask = round(ask, 5)

    buy_book_amount  = int(qty*bid*precision/cleanup_rounding)*cleanup_rounding
    sell_book_amount = int(qty*precision/cleanup_rounding)*cleanup_rounding
    if not fix_books(precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
      print("Something went wrong, aborting")
      print("Last Values: precision: %s buy_book_amount: %s sell_book_amount %s bid_id %s ask_id %s" % (precision, buy_book_amount, sell_book_amount, bid_id, ask_id))
      print_log('ERR','"Something went wrong, aborting"')
      logFile.close()
      sys.exit()
    print("Settled order for %0.5f MKR @ %f ETH/MKR" % (float(qty), float(bid)))
    #print_log('log',"Settled order for %0.5f MKR" % (float(qty), float(bid)))
    break

logFile.close()
time.sleep(30) #Give things a chance to settle out
