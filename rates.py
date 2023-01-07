import requests
import json

def get_usdt_rate():
    data = {"proMerchantAds":False,"page":1,"rows":10,"payTypes":["RosBankNew"],"countries":[],"publisherType":"merchant","asset":"USDT","fiat":"RUB","tradeType":"BUY","transAmount":"100000"} 
    r = requests.post('https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', json=data)
    o = r.json()["data"][:3]
    sum = 0
    for result in o:
        sum = sum + float(result["adv"]["price"])
    return (sum / 3) + 1

def get_currency_rate(currency):
    data = {"proMerchantAds":False,"page":1,"rows":10,"payTypes":[],"countries":[],"publisherType":"merchant","asset":"USDT","fiat":currency.upper(),"tradeType":"SELL"} 
    r = requests.post('https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', json=data)
    o = r.json()["data"][:3]
    sum = 0
    for result in o:
        sum += float(result["adv"]["price"])
    return sum / 3

def get_usdt_currency(currency):
    buyer_fee = 1.05
    hidden_fee = 1.03
    return get_usdt_rate()/get_currency_rate(currency) * buyer_fee * hidden_fee
