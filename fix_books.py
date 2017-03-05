#! /usr/bin/python3

import json
from web3 import Web3, RPCProvider
from operator import itemgetter
import time
import sys
import datetime
import math

precision = 1000000000000000000
dust      = 10000000000000
mkr_addr = "0xc66ea802717bfb9833400264dd12c2bceaa34a6d"
weth_addr = "0xecf8f87f810ecf450940c9f60066b4a7a501d6a7" 
geth_addr = "0xa74476443119A942dE498590Fe1f2454d7D4aC0d"
market_addr = "0xC350eBF34B6d83B64eA0ee4E39b6Ebe18F02aD2F"
#market_addr = "0x454e4f5bb176a54638f727b3314c709cb4f66dae"
acct_owner = "0x6E39564ecFD4B5b0bA36CD944a46bCA6063cACE5"

web3rpc = Web3(RPCProvider())
web3rpc.eth.defaultAccount = acct_owner
web3rpc.eth.defaultBlock = "latest"

logFile = open('maker-matcher.json', 'a+')

def print_log( log_type, entry ):
      ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
      entry = '[{date:' + ts + ',"' + log_type + '":' + entry + '}],\n'
      logFile.write( entry )

def fix_books(precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
      print('"ETH":%f,"MKR":%f}' % (buy_book_amount/precision, sell_book_amount/precision))
      print_log('log','{"ETH":%f,"MKR":%f}' % (buy_book_amount/precision, sell_book_amount/precision))
      try:
        print("Submitting Buy Book order", end='', flush=True )
        try:
          if market_contract.call().buy(bid_id, buy_book_amount):
            try:
              result_bb = market_contract.transact().buy(bid_id, buy_book_amount)
              print_log('log','{"buy_tx":"%s"}' % (result_bb))
              while web3rpc.eth.getTransactionReceipt(result_bb) is None:
                 print(".", end='', flush=True) 
                 time.sleep(2)
              print("")
            except:
              print("")
              print_log('ERR','"Failed Buy Book transaction"')
              return False
          else:
              print("")
              print_log('ERR','"Failed Buy Book transaction"')
              return False
        except:
          print("")
          print("Buy checked failed to check.") 
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

with open('simple_market.abi', 'r') as abi_file:
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
  time.sleep(5)
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
    if valid :
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
  if len(buy_orders) > 0:
    depth = len(buy_orders)
    #find highest non dust bid
    bid_qty = 0
    bid_id = 0
    bid = 0
    current_depth = 0
    buy_orders.sort(key=itemgetter(2), reverse=True)
    while current_depth <= len(buy_orders):
      bid_qty     = float(buy_orders[current_depth][1]) 
      if bid_qty > 0.0001:
        bid    = float(buy_orders[current_depth][2])
        bid_id = int(buy_orders[current_depth][0])
        print ("Highest bid is for %f MKR @ %f ETH/MKR" % (bid_qty,bid))
        break
      else:
        current_depth = current_depth + 1
  else:
    print ("Buy book is empty")
    continue
  
  if len(sell_orders) > 0:
    depth = len(sell_orders)
    sell_orders.sort(key=itemgetter(2), reverse=False)
    #find lowest non dust ask
    ask_qty = 0
    ask_id = 0
    ask = 0
    current_depth = 0
    while current_depth <= len(sell_orders):
      ask_qty  = float(sell_orders[current_depth][1]) 
      if ask_qty > 0.0001:
        ask_id = int(sell_orders[current_depth][0])
        ask = float(sell_orders[current_depth][2])
        print ("Lowest ask is for %f MKR @ %f ETH/MKR" % (ask_qty,ask))
        break
      else:
        current_depth = current_depth + 1
  else:
    print ("Sell book is empty")
    continue

  #Make sure we have enough allowance
  allowance = float(weth_contract.call().allowance(acct_owner, market_addr))/precision
  if allowance < 100:
    print("Out of WETH allowance")
    print_log("ERR", "Out of WETH allowance")
    continue
#    result = weth_contract.transact().approve(acct_owner, int(10000*precision))
#    print ("Update weth allowance: %s -> 10000" % (allowance))
#    while web3rpc.eth.getTransactionReceipt(result) is None:
#      print(".", end='', flush=True) 
#      time.sleep(2)
#    print("")
  
  allowance = float(weth_contract.call().allowance(acct_owner, market_addr))/precision
  if allowance < 100:
    print("Out of wETH allowance")
    print_log("ERR", "Out of MKR allowance")
    continue
#    result = mkr_contract.transact().approve(acct_owner, int(10000*precision))
#    print ("Update mkr allowance: %s -> 10000" % (allowance))
#    while web3rpc.eth.getTransactionReceipt(result) is None:
#      print(".", end='', flush=True) 
#      time.sleep(2)
#    print("")
 
  if math.floor(bid*100000) >= math.floor(ask*100000):
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
    qty = round(qty, 18)
    bid = round(bid, 5)
    ask = round(ask, 5)

    if qty <= 0.001:
      #print_log("ERR", "Order is too small to process")
      print("Order is too small.")
      continue

    buy_book_amount  = math.floor(int(qty*bid*precision)/dust)*dust
    sell_book_amount = math.floor(int(qty*precision)/dust)*dust

    print("buy_book_amount: %s sell_book_amount %s bid_id %s ask_id %s" % (buy_book_amount/precision, sell_book_amount/precision, bid_id, ask_id))
    if not fix_books(precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
      print("Something went wrong, aborting")
      print("buy_book_amount: %s sell_book_amount %s bid_id %s ask_id %s" % (buy_book_amount, sell_book_amount, bid_id, ask_id))
      print_log('ERR','"Something went wrong, aborting"')
      logFile.close()
      sys.exit()
    print("Settled order for %f MKR @ %f ETH/MKR" % (float(qty), float(bid)))
    print_log('log',"Settled order for %0.5f MKR" % (float(qty), float(bid)))
    break
  time.sleep(5)
logFile.close()
time.sleep(30) #Give things a chance to settle out
