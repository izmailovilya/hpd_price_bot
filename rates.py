import requests
import json

def get_usdt_rate():
    data = {"proMerchantAds":False,"page":1,"rows":10,"payTypes":["RosBankNew"],"countries":[],"publisherType":"merchant","asset":"USDT","fiat":"RUB","tradeType":"BUY","transAmount":"200000"} 
    r = requests.post('https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', json=data)
    o = r.json()
    sum = 0
    for result in o["data"]:
        sum = sum + float(result["adv"]["price"])
    return (sum / 10) + 1

def get_currency_rate(currency):
    data = {"proMerchantAds":False,"page":1,"rows":10,"payTypes":[],"countries":[],"publisherType":"merchant","asset":"USDT","fiat":currency.upper(),"tradeType":"SELL"} 
    r = requests.post('https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search', json=data)
    o = r.json()
    sum = 0
    for result in o["data"]:
        sum += float(result["adv"]["price"])
    return sum / 10

def get_usdt_currency(currency):
    return get_usdt_rate()/get_currency_rate(currency) * 1.05
