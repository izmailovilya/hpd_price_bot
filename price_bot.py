import telebot
from telebot import types
import re
import rates
import json


bot = telebot.TeleBot("5855546110:AAF5A-S0zNj2Qx9P7osHUJ816CwoFY_xRWo")
@bot.message_handler(commands=['start'])
def start(message):
    write_stages(message.chat.id, 0)
    orders = {message.chat.id : {
            "region" : "none",
            "shop" : "none",
            "currency" : "none",
            "shop_delivery" : "none",
            "net_value" : 0,
            "ru_delivery" : 0,
            "items" : []
            }}
    write_order(message.chat.id, orders)
    markup = types.ReplyKeyboardMarkup()
    calculate = types.KeyboardButton("Рассчитать стоимость")
    markup.add(calculate)
    bot.send_message(message.chat.id, 'Привет!', reply_markup=markup)

@bot.message_handler(content_types=["text"])
def text(message):
    id = str(message.chat.id)
    text_message = message.text.strip()
    try:
        orders = read_order(id)
        if read_stages(id) == 4:
            calc(text_message, orders, id)
            write_stages(message.chat.id, 0)

        if read_stages(id) == 3:
            category = check_category(text_message)
            orders[id]["items"].append({
                "value" : 0,
                "delivery" : 0,
                "category" : category
            })
            write_order(id, orders)
            write_stages(id, 4)
            markup = types.ReplyKeyboardRemove(selective=False)
            bot.send_message(message.chat.id, f"Введи стоимость товара. Выбранная валюта: {orders[id]['currency']}", reply_markup=markup)

        if read_stages(id) == 2:
            tmp = check_currency(text_message)
            if tmp != "none" and orders[id]["currency"] == "none":
                orders[id]["currency"] = tmp
                pick_region(id)
            tmp = check_region(text_message)
            if tmp != "none" and orders[id]["region"] == "none":
                orders[id]["region"] = tmp
                pick_shop_delivery(id)
            if re.search(r"\d+", text_message) and orders[id]["shop_delivery"] == "none":
                orders[id]["shop_delivery"] = float(text_message) * rates.get_currency_rate(orders[id]["currency"])
            if orders[id]["shop_delivery"] != "none" and orders[id]["region"] != "none" and orders[id]["currency"] != "none":
                write_stages(id, 3)
                write_order(id, orders)
                pick_category(id)

        if read_stages(id) == 1:
            text_message = text_message.lower()
            if matches := re.search(r"(?:https://)?(?:www\.)?([^\.]+)\..+", text_message):
                text_message = matches.group(1)
            orders[id] = check_shop(text_message)
            write_order(id, orders)
            if orders[id]["currency"] == 'none':
                write_stages(id, 2)
                pick_currency(id)
            else:
                write_stages(id, 3)
                pick_category(id)

        if  read_stages(id) == 0:
            if text_message == "Добавить ещё одну вещь":
                if orders[id]["region"] == "china":
                    orders[id]["shop_delivery"] *= 2
                write_order(id, orders)
                write_stages(id, 3)
                pick_category(id)
            if text_message == "Рассчитать стоимость" or text_message == "Создать новый заказ":
                orders = {message.chat.id : {
                "region" : "none",
                "shop" : "none",
                "currency" : "none",
                "shop_delivery" : "none",
                "net_value" : 0,
                "ru_delivery" : 0,
                "items" : []
                }}
                write_order(id, orders)
                pick_shop(id)
                write_stages(id, 1)
    except:
        write_stages(id, 0)
        markup = types.ReplyKeyboardMarkup()
        calculate = types.KeyboardButton("Рассчитать стоимость")
        markup.add(calculate)
        bot.send_message(message.chat.id, 'Давай попробуем снова', reply_markup=markup)

def pick_shop(id):
    markup = types.ReplyKeyboardMarkup()
    poizon = types.KeyboardButton("POIZON")
    zalando = types.KeyboardButton("zalando")
    endclothing = types.KeyboardButton("endclothing")
    nbsklep = types.KeyboardButton("nbsklep")
    adidas = types.KeyboardButton("adidas (poland)")
    louisaviaroma = types.KeyboardButton("louisaviaroma")
    nike = types.KeyboardButton("nike")
    asphaltgold = types.KeyboardButton("asphaltgold")
    asos = types.KeyboardButton("asos")
    markup.row(poizon)
    markup.row(zalando, asos)
    markup.row(endclothing, asphaltgold, louisaviaroma)
    markup.row(nbsklep, adidas, nike)
    bot.send_message(id, "Выбери магазин либо введи ссылку", reply_markup=markup)

def pick_category(id):
    markup = types.ReplyKeyboardMarkup()
    boots = types.KeyboardButton("Ботинки/высокие кроссовки")
    sneakers = types.KeyboardButton("Кроссовки")
    jackets = types.KeyboardButton("Зимние куртки")
    pants = types.KeyboardButton("Штаны и джинсы")
    bags = types.KeyboardButton("Рюкзаки/сумки")
    light_jacket = types.KeyboardButton("Легкие куртки")
    hoodie = types.KeyboardButton("Лонгслив/худи")
    shorts = types.KeyboardButton("Шорты")
    small_bags = types.KeyboardButton("Маленькие сумки")
    t_shirts = types.KeyboardButton("Футболки")
    watches = types.KeyboardButton("Часы")
    wallet = types.KeyboardButton("Кошелёк")
    socks = types.KeyboardButton("Носки (3 пары)")
    snood = types.KeyboardButton("Снуд")
    bandage = types.KeyboardButton("Повязка на голову")
    markup.row(boots, sneakers)
    markup.row(jackets, hoodie, light_jacket)
    markup.row(t_shirts, shorts, pants)
    markup.row(bandage, snood, socks)
    markup.row(wallet, watches, bags, small_bags)
    bot.send_message(id, 'Выбери категорию. Если подходящей категории нет, то выбери что-то похожее по весу', reply_markup=markup)

def pick_currency(id):
    markup = types.ReplyKeyboardMarkup()
    euro = types.KeyboardButton("Евро €")
    dollar = types.KeyboardButton("Доллар $")
    yuan = types.KeyboardButton("Юань ¥")
    pound = types.KeyboardButton("Фунт £")
    zlot = types.KeyboardButton("Злотый zł")
    markup.row(yuan, dollar)
    markup.row(euro, pound, zlot)
    bot.send_message(id, "Выбери валюту", reply_markup=markup)

def pick_region(id):
    markup = types.ReplyKeyboardMarkup()
    china = types.KeyboardButton("Китай")
    usa = types.KeyboardButton("США")
    uk = types.KeyboardButton("Великобритания")
    poland = types.KeyboardButton("Польша")
    markup.row(usa, china)
    markup.row(uk, poland)
    bot.send_message(id, "Выбери страну", reply_markup=markup)

def pick_shop_delivery(id):
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(id, f"Введи стоимость доставки из магазина. Выбранная валюта: {orders[id]['currency']}.", reply_markup=markup)

def check_category(text_message):
    match text_message:
            case "Ботинки/высокие кроссовки":
                item_type = "boots"
            case "Кроссовки":
                item_type = "sneakers"
            case "Зимние куртки":
                item_type = "jackets"
            case "Штаны и джинсы":
                item_type = "pants"
            case "Рюкзаки/сумки":
                item_type = "bags"
            case "Легкие куртки":
                item_type = "light_jacket"
            case "Лонгслив/худи":
                item_type = "hoodie"
            case "Шорты":
                item_type = "shorts"
            case "Маленькие сумки":
                item_type = "small_bags"
            case "Футболки":
                item_type = "t_shirts"
            case "Часы":
                item_type = "watches"
            case "Кошелёк":
                item_type = "wallet"
            case "Носки (3 пары)":
                item_type = "socks"
            case "Снуд":
                item_type = "snood"
            case "Повязка на голову":
                item_type = "bandage"
            case _:
                item_type = "none"
    return item_type

def check_region(text_message):
    match text_message:
            case "США":
                region = "usa"
            case "Китай":
                region = "china"
            case "Великобритания":
                region = "uk"
            case "Польша":
                region = "poland"
            case _:
                region = "none"
    return region

def check_currency(text_message):
    match text_message:
            case "Евро €":
                currency = "eur"
            case "Доллар $":
                currency = "usd"
            case "Юань ¥":
                currency = "cny"
            case "Фунт £":
                currency = "gbp"
            case "Злотый zł":
                currency = "pln"
            case _:
                currency = "none"
    return currency

def check_shop(text_message):
    match text_message:
        case "poizon":
            shop = "poizon"
            region = "china"
            currency = "cny"
            shop_delivery = 20 * rates.get_usdt_currency('cny')
        case "zalando":
            shop = "zalando"
            region = "poland"
            currency = "pln"
            shop_delivery = 0
        case "endclothing":
            shop = "endclothing"
            region = "uk"
            currency = "gbp"
            shop_delivery = 5 * rates.get_usdt_currency('gbp')
        case "asphaltgold":
            shop = "asphaltgold"
            region = "poland"
            currency = "eur"
            shop_delivery = 5 * rates.get_usdt_currency('eur')
        case "louisaviaroma":
            shop = "louisaviaroma"
            region = "poland"
            currency = "pln"
            shop_delivery = 76 * rates.get_usdt_currency('pln')
        case "nbsklep":
            shop = "nbsklep"
            region = "poland"
            currency = "pln"
            shop_delivery = 0
        case "adidas (poland)":
            shop = "adidas"
            region = "poland"
            currency = "pln"
            shop_delivery = 0
        case "nike":
            shop = "nike"
            region = "usa"
            currency = "usd"
            shop_delivery = 8 * rates.get_usdt_currency('usd')
        case "asos":
            shop = "asos"
            region = "usa"
            currency = "usd"
            shop_delivery = 0
        case "osirisshoes":
            shop = "osirisshoes"
            region = "usa"
            currency = "usd"
            shop_delivery = 19 * rates.get_usdt_currency('usd')
        case "farfetch":
            shop = "farfetch"
            region = "usa"
            currency = "usd"
            shop_delivery = 24 * rates.get_usdt_currency('usd')
        case "goat":
            shop = "goat"
            region = "usa"
            currency = "usd"
            shop_delivery = 14.5 * rates.get_usdt_currency('usd')
        case "eobuwie":
            shop = "eobuwie"
            region = "poland"
            currency = "pln"
            shop_delivery = 0
        case "itkkit":
            shop = "itkkit"
            region = "poland"
            currency = "eur"
            shop_delivery = 5 * rates.get_usdt_currency('eur')
        case "mrporter":
            shop = "mrporter"
            region = "poland"
            currency = "eur"
            shop_delivery = 5 * rates.get_usdt_currency('eur')
        case "solebox":
            shop = "solebox"
            region = "poland"
            currency = "eur"
            shop_delivery = 11 * rates.get_usdt_currency('eur')
        case "footpatrol":
            shop = "footpatrol"
            region = "uk"
            currency = "gbp"
            shop_delivery = 1 * rates.get_usdt_currency('gbp')  
        case "matchesfashion":
            shop = "matchefashion"
            region = "usa"
            currency = "usd"
            shop_delivery = 20 * rates.get_usdt_currency('usd')     
        case "bdgastore":
            shop = "bdgastore"
            region = "usa"
            currency = "usd"
            shop_delivery = 11 * rates.get_usdt_currency('usd') 
        case "lapstoneandhammer":
            shop = "lapstoneandhammer"
            region = "usa"
            currency = "usd"
            shop_delivery = 11 * rates.get_usdt_currency('usd')  
        case "sneakerpolitics":
            shop = "sneakerpolitics"
            region = "usa"
            currency = "usd"
            shop_delivery = 15 * rates.get_usdt_currency('usd')           
        case _:
            shop = "other"
            return {
            "region" : "none",
            "shop" : "none",
            "currency" : "none",
            "shop_delivery" : "none",
            "net_value" : 0,
            "net_delivery" : 0,
            "ru_delivery" : 0,
            "items" : []
            }
    return {
            "region" : region,
            "shop" : shop,
            "currency" : currency,
            "shop_delivery" : shop_delivery,
            "net_value" : 0,
            "net_delivery" : 0,
            "ru_delivery" : 0,
            "items" : []
            }

def calc(text_message, orders, id):
    usdt = rates.get_usdt_rate()
    i = len(orders[id]["items"]) - 1
    order = orders[id]
    fixed_expenses = 180
    order["ru_delivery"] = 0
    hidden_fees = 1.02
    order["net_value"] += float(text_message) * rates.get_usdt_currency(order["currency"]) * hidden_fees
    insurance = order["net_value"] * 0.03
    comission = order["net_value"] * 0.2 + 1500
    if re.search(r"\d+", text_message):
        match order["region"]:
            case "china":
                order["ru_delivery"] = 350
                match order["items"][i]["category"]:
                    case "bandage":
                        delivery = 1.45
                    case "snood": 
                        delivery = 14.5 * 0.2
                    case "socks":
                        delivery = 14.5 * 0.25
                    case "wallet":
                        delivery = 14.5 * 0.4
                    case "watches":
                        delivery = 14.5 * 0.4
                    case "t_shirts":
                        delivery = 14.5 * 0.4
                    case "small_bags":
                        delivery = 14.5 * 0.5
                    case "shorts":
                        delivery = 14.5 * 0.5
                    case "hoodie":
                        delivery = 14.5 * 0.8
                    case "light_jacket":
                        delivery = 14.5 * 0.8
                    case "bags":
                        delivery = 14.5 * 0.9
                    case "pants":
                        delivery = 14.5 * 0.9
                    case "jackets":
                        delivery = 14.5 * 1.5
                    case "sneakers":
                        delivery = 14.5 * 1.5
                    case "boots":
                        delivery = 14.5 * 2.2
                delivery = delivery * usdt * 1.02 * 1.15
            case "poland":
                match order["items"][i]["category"]:
                    case "bandage":
                        delivery = 563
                    case "snood": 
                        delivery = 563
                    case "socks":
                        delivery = 563
                    case "wallet":
                        delivery = 563
                    case "watches":
                        delivery = 563
                    case "t_shirts":
                        delivery = 563
                    case "small_bags":
                        delivery = 563
                    case "shorts":
                        delivery = 563
                    case "hoodie":
                        delivery = 844
                    case "light_jacket":
                        delivery = 844
                    case "bags":
                        delivery = 844
                    case "pants":
                        delivery = 844
                    case "jackets":
                        delivery = 1126
                    case "sneakers":
                        delivery = 1126
                    case "boots":
                        delivery = 1688
            case "uk":
                match order["items"][i]["category"]:
                    case "bandage":
                        delivery = 991
                    case "snood": 
                        delivery = 991
                    case "socks":
                        delivery = 991
                    case "wallet":
                        delivery = 991
                    case "watches":
                        delivery = 991
                    case "t_shirts":
                        delivery = 991
                    case "small_bags":
                        delivery = 991
                    case "shorts":
                        delivery = 991
                    case "hoodie":
                        delivery = 1524
                    case "light_jacket":
                        delivery = 1524
                    case "bags":
                        delivery = 1524
                    case "pants":
                        delivery = 1524
                    case "jackets":
                        delivery = 1981
                    case "sneakers":
                        delivery = 1981
                    case "boots":
                        delivery = 3048
            case "usa":
                match order["items"][i]["category"]:
                    case "bandage":
                        delivery = 14
                    case "snood": 
                        delivery = 14
                    case "socks":
                        delivery = 14
                    case "wallet":
                        delivery = 14
                    case "watches":
                        delivery = 14
                    case "t_shirts":
                        delivery = 14
                    case "small_bags":
                        delivery = 18
                    case "shorts":
                        delivery = 18
                    case "hoodie":
                        delivery = 18
                    case "light_jacket":
                        delivery = 18
                    case "bags":
                        delivery = 18
                    case "pants":
                        delivery = 18
                    case "jackets":
                        delivery = 34
                    case "sneakers":
                        delivery = 34
                    case "boots":
                        delivery = 44.5
                delivery = delivery * 1.2 * 1.05 * usdt
        order["net_delivery"] += delivery
        order["net_value"] = round(order["net_value"])
        order["net_delivery"] = round(order["net_delivery"])
        comission = round(comission)
        insurance = round(insurance)
        order["shop_delivery"] = round(order["shop_delivery"])
        result = round(order["net_delivery"] + order["ru_delivery"] + order["net_value"] + fixed_expenses + insurance + order["shop_delivery"] + comission)
        markup = types.ReplyKeyboardMarkup()
        retry = types.KeyboardButton("Создать новый заказ")
        add = types.KeyboardButton("Добавить ещё одну вещь")
        markup.add(retry, add)
        bot.send_message(id, f'Сумма заказа: {result} руб.\n\n\
Стоимость товаров: {order["net_value"]} руб.\n\
Стоимость доставки магазина: {order["shop_delivery"]} руб.\n\
Стоимость доставки до РФ: {order["net_delivery"]} руб.\n\
Стоимость доставки по РФ: {order["ru_delivery"]} руб.\n\
Расходы на оформление: {fixed_expenses} руб.\n\
Страховка: {insurance} руб.\n\
Комиссия: {comission} руб.\n\n\
Курс: {rates.get_usdt_currency(order["currency"]) * hidden_fees:.2f} руб.\n\
                ', reply_markup=markup)
        order = {id:order}
        write_order(id, order)
    else:
        bot.send_message(id, 'Не распознал сумму')

def write_stages(id, stage):
    with open(f'stage_{id}.txt', 'w') as convert_file:
        convert_file.write(json.dumps({id : stage}))

def read_stages(id):
    with open(f'stage_{id}.txt') as convert_file:
        dict = json.load(convert_file)
    return dict[str(id)]
    

def write_order(id, order):
    with open(f'order_{id}.txt', 'w') as convert_file:
        convert_file.write(json.dumps(order))

def read_order(id):
    with open(f'order_{id}.txt') as convert_file:
        dict = json.load(convert_file)
    return dict


bot.polling(none_stop=True)