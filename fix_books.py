#! /usr/bin/python3

import json
from web3 import Web3, RPCProvider
from operator import itemgetter
import time


precision = 1000000000000000000
mkr_addr = "0xc66ea802717bfb9833400264dd12c2bceaa34a6d"
weth_addr = "0xecf8f87f810ecf450940c9f60066b4a7a501d6a7" 
geth_addr = "0xa74476443119A942dE498590Fe1f2454d7D4aC0d"
market_addr = "0xa1B5eEdc73a978d181d1eA322ba20f0474Bb2A25"
acct_owner = "0x6E39564ecFD4B5b0bA36CD944a46bCA6063cACE5"

web3rpc = Web3(RPCProvider())
web3rpc.eth.defaultAccount = acct_owner
web3rpc.eth.defaultBlock = "latest"

def fix_books(market_contract, precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
      print("Fixing order: %f %f" % (buy_book_amount/precision, sell_book_amount/precision))
      print("Pre-check...")
      try:
        if market_contract.call().buy(bid_id, buy_book_amount) and market_contract.call().buy(ask_id, sell_book_amount):
        #if market_contract.call().buy(ask_id, sell_book_amount):
          print("Passed pre-check")
          try: 
            result_bb = market_contract.transact().buy(bid_id, buy_book_amount)
            result_sb = market_contract.transact().buy(ask_id, sell_book_amount)
            print("Orders submitted\n%s\n%s" % (result_bb, result_sb))
            time.sleep(300)
            return True
          except:
            print("Transaction timed out.") 
            return False
      except:
        print("Failed pre-buy check\n")
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

weth_balance = float(weth_contract.call().balanceOf(acct_owner))/precision
mkr_balance  = float(mkr_contract.call().balanceOf(acct_owner))/precision


last_offer_id = market_contract.call().last_offer_id()

id = 0
offers = []

while id <  last_offer_id + 1:
  offers.append(market_contract.call().offers(id))
  id = id + 1

print("\nBalances: %0.5f WETH - %0.5f MKR\n" % (weth_balance, mkr_balance))
print("There are %i offers" % last_offer_id)

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
if float(weth_contract.call().allowance(acct_owner, market_addr)) < 0.1:
  result = weth_contract.call().approve(acct_owner, int(0.1*precision))
  #print ("Update allowance: %s" % result)
  while weth_contract.call().allowance(weth_addr, market_addr) < 0.1:
    print("Waiting for allowance to be applied")
    time.sleep(3)
print("WETH Allowance: %f" % (weth_contract.call().allowance(acct_owner, market_addr)/precision))

if float(mkr_contract.call().allowance(acct_owner, market_addr)) < 0.1:
  result = mkr_contract.call().approve(acct_owner, int(0.1*precision))
  #print ("Update allowance: %s" % result)
  while mkr_contract.call().allowance(mkr_addr, market_addr) < 0.1:
    print("Waiting for allowance to be applied")
    time.sleep(3)
print("MKR Allowance: %f" % (mkr_contract.call().allowance(acct_owner, market_addr)/precision))

if round(bid,5) >= round(ask,5):
  print("\nAction needed!")
  if bid_qty > ask_qty:
    qty = ask_qty
    if weth_balance < ask_qty:
      qty = weth_balance
  else:
    qty = bid_qty
    if mkr_balance < bid_qty:
      qty = mkr_balance
  buy_book_amount  = int(qty*bid*precision)
  sell_book_amount = int(qty*precision)
  while not fix_books(market_contract, precision, buy_book_amount, sell_book_amount, bid_id, ask_id):
    print("Something went wrong, trying again")
    time.sleep(5)
  print("Settled order for %0.5f MKR" % (float(qty)/float(bid)))
else:
 print ("All is well")

