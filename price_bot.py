from telebot import types
import telebot, re, rates, json, os, sys
from requests.exceptions import ConnectionError, ReadTimeout
from weight import find_weight
from datetime import datetime
import traceback

blocked_shops = ["asos", "tradeinn", "stockx", "sneakersnstuff", "stadiumgoods"]


bot = telebot.TeleBot(os.environ["TG_PRICE_API"])
total_price_requests = 0
today_price_requests = 0
now = datetime.now().timestamp()

@bot.message_handler(commands=['requests'])
def requests(message):
    hours = round((datetime.now().timestamp() - now) / 60 / 60)
    bot.send_message(217931504, f"Запросов цены с перезапуска: {total_price_requests}\n\
Запросов цены за последние {hours} часов: {today_price_requests}")

@bot.message_handler(commands=['start'])
def start(message):
    write_stages(message.chat.id, 0)
    orders = {message.chat.id: {
        "region": "none",
        "shop": "none",
        "currency": "none",
        "shop_delivery": "none",
        "net_value": 0,
        "net_shop_delivery": 0,
        "ru_delivery": 0,
        "items": []
    }}
    write_order(message.chat.id, orders)
    markup = types.ReplyKeyboardMarkup()
    calculate = types.KeyboardButton("Рассчитать стоимость")
    markup.add(calculate)
    bot.send_message(message.chat.id, 'Привет!', reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop(message):
    markup = types.ReplyKeyboardRemove(selective=False)
    write_stages(message.chat.id, -1)
    bot.send_message(message.chat.id, 'Хорошо, убираю эти кнопки', reply_markup=markup)

@bot.message_handler(commands=['chatid'])
def chatid(message):
    bot.send_message(message.chat.id, f'{message.chat.id}')

@bot.message_handler(commands=['usdt'])
def usdt(message):
    words = message.text.split()
    if len(words) >= 2:
        symbol = message.text.split()[1]
        rate = rates.get_usdt_rate()/rates.get_currency_rate(symbol)
        if len(words) == 2:
            bot.send_message(
                message.chat.id, f'Курс {symbol.upper()} в рублях через P2P: {rate:.4f}')
        if len(words) == 3:
            value = message.text.split()[2]
            bot.send_message(
                message.chat.id, f'{value} {symbol.upper()} = {round(float(value) * rate)} RUB')
    if len(words) == 1:
        bot.send_message(
            message.chat.id, f'Курс USDT на Binance: {rates.get_usdt_rate() - 1:.2f}') 


@bot.message_handler(commands=['cny'])
def cny(message):
    bot.send_message(message.chat.id, f'Курс юаня через Binance: {rates.get_currency_rate("CNY"):.2f}\n\
Минимально допустимый курс китайца: {rates.get_currency_rate("CNY")*0.98:.2f}')


@bot.message_handler(commands=['checker'])
def checker(message):
    bot.send_message(
        message.chat.id, 'Пришлите мне 2 сообщения со списком переводов')
    write_stages(message.chat.id, 10)


@bot.message_handler(content_types=["text"])
def text(message):
    id = str(message.chat.id)
    text_message = message.text.strip()
    try:
        stage = read_stages(id)
    except:
        stage = -1
        bot.send_message(id, "Для старта используй команду")
    if stage >= 10:
        compare_mode(id, stage, text_message)
    if 0 <= stage < 10:
        price_mode(id, stage, text_message)


def price_mode(id, stage, text_message):
    try:
        orders = read_order(id)
        if stage == 6:
            bot.send_message(id, find_weight(text_message))
            write_stages(id, 3)
            pick_category(id)
        if stage == 5:
            if re.search(r"\d+", text_message):
                write_stages(id, 0)
                i = len(orders[id]["items"]) - 1
                orders[id]["items"][i]["quantity"] = int(text_message)
                calc_total(orders, id)
                print_short(id, orders)
            else:
                raise ValueError

        if stage == 4:
            write_stages(id, 0)
            calc_item(text_message, orders, id)
            calc_total(orders, id)
            print_short(id, orders)

        if stage == 3:
            category = check_category(text_message)
            if category == "none":
                write_stages(id, 6)
                markup = types.ReplyKeyboardRemove(selective=False)
                bot.send_message(
                    id, f"Введи название товара, чтобы определить примерный вес по нашей истории заказов Poizon за последние пару месяцев", reply_markup=markup)
            else:
                orders[id]["items"].append({
                    "value": 0,
                    "delivery": 0,
                    "category": category,
                    "quantity": 1
                })
                write_order(id, orders)
                write_stages(id, 4)
                markup = types.ReplyKeyboardRemove(selective=False)
                bot.send_message(
                    id, f"Введи стоимость товара. Выбранная валюта: {orders[id]['currency']}", reply_markup=markup)

        if stage == 2:
            tmp = check_currency(text_message)
            if tmp != "none" and orders[id]["currency"] == "none":
                orders[id]["currency"] = tmp
                write_order(id, orders)
                pick_region(id)
            tmp = check_region(text_message)
            if tmp != "none" and orders[id]["region"] == "none":
                orders[id]["region"] = tmp
                write_order(id, orders)
                pick_shop_delivery(id)
            if re.search(r"\d+", text_message) and orders[id]["shop_delivery"] == "none":
                orders[id]["shop_delivery"] = float(
                    text_message) * rates.get_usdt_currency(orders[id]["currency"])
                write_order(id, orders)
            if orders[id]["shop_delivery"] != "none" and orders[id]["region"] != "none" and orders[id]["currency"] != "none":
                write_stages(id, 3)
                write_order(id, orders)
                pick_category(id)

        if stage == 1:
            text_message = text_message.lower()
            if matches := re.search(r"(?:https://)?(?:www\.)?([^\.]+)\..+", text_message):
                text_message = matches.group(1)
            orders[id] = check_shop(text_message)
            if orders[id]["region"] == "blocked":
                bot.send_message(id, f"К сожалениию, с {orders[id]['shop'].upper()} мы на данный момент не работаем. Нужно выбрать другой магазин.")
            else:
                write_order(id, orders)
                if orders[id]["currency"] == 'none':
                    write_stages(id, 2)
                    pick_currency(id)
                else:
                    write_stages(id, 3)
                    pick_category(id)

        if stage == 0:
            if text_message == "Добавить ещё одну вещь":
                write_order(id, orders)
                write_stages(id, 3)
                pick_category(id)
            if text_message == "Рассчитать стоимость" or text_message == "Создать новый заказ":
                orders = {id: {
                    "region": "none",
                    "shop": "none",
                    "currency": "none",
                    "shop_delivery": "none",
                    "net_value": 0,
                    "net_shop_delivery": 0,
                    "ru_delivery": 0,
                    "items": []
                }}
                write_order(id, orders)
                pick_shop(id)
                write_stages(id, 1)
            if text_message == "Изменить количество последнего товара":
                markup = types.ReplyKeyboardRemove(selective=False)
                bot.send_message(
                    id, f"Сколько таких товаров в заказе?", reply_markup=markup)
                write_stages(id, 5)
            if text_message == "Изменить цену последнего товара":
                write_stages(id, 4)
                markup = types.ReplyKeyboardRemove(selective=False)
                bot.send_message(
                    id, f"Введи стоимость товара. Выбранная валюта: {orders[id]['currency']}", reply_markup=markup)
            if text_message == "Показать весь заказ":
                print_result(id, orders)
    except:
        write_stages(id, 0)
        markup = types.ReplyKeyboardMarkup()
        calculate = types.KeyboardButton("Рассчитать стоимость")
        markup.add(calculate)
        bot.send_message(
            id, 'Давай попробуем снова', reply_markup=markup)


def compare_mode(id, stage, message):
    if stage == 10:
        write_order(id, {"1": message, "2": "none"})
        write_stages(id, 11)
        bot.send_message(id, 'Первый список принят.')
    if stage == 11:
        order = read_order(id)
        order["2"] = message
        write_order(id, order)
        write_stages(id, -1)
        bot.send_message(id, 'Второй список принят.')
        compare(id, read_order(id))
        write_stages(id, -1)


def compare(id, dict):
    payments1 = dict["1"].split()
    payments2 = dict["2"].split()
    missing = []
    good = '<b>Совпали:</b>\n'
    bad1 = '<b>Не совпали из первого списка:</b>\n'
    bad2 = '<b>Не совпали из второго списка:</b>\n'
    for payment in payments1:
        if payment in payments2:
            payments2.remove(payment)
            good = good + payment + "\n"
        else:
            missing.append(payment)
            bad1 = bad1 + payment + "\n"
    for payment in payments2:
        print(payment)
        bad2 = bad2 + payment + "\n"
    bad = bad1 + '\n' + bad2
    bot.send_message(id, good, parse_mode="HTML")
    bot.send_message(id, bad, parse_mode="HTML")


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
    bot.send_message(id, "Выбери магазин либо введи ссылку",
                     reply_markup=markup)


def pick_category(id):
    markup = types.ReplyKeyboardMarkup()
    search = types.KeyboardButton("Не уверен что выбрать?")
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
    markup.row(search)
    markup.row(boots, sneakers)
    markup.row(jackets, hoodie, light_jacket)
    markup.row(t_shirts, shorts, pants)
    markup.row(bandage, snood, socks)
    markup.row(wallet, watches, bags, small_bags)
    bot.send_message(
        id, 'Выбери категорию. Если подходящей категории нет, то выбери что-то похожее по весу', reply_markup=markup)


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
    orders = read_order(id)
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(
        id, f"Введи стоимость доставки из магазина. Выбранная валюта: {orders[id]['currency']}.", reply_markup=markup)


def check_category(text_message):
    if text_message == "Ботинки/высокие кроссовки":
        item_type = "boots"
    elif text_message == "Кроссовки":
        item_type = "sneakers"
    elif text_message == "Зимние куртки":
        item_type = "jackets"
    elif text_message == "Штаны и джинсы":
        item_type = "pants"
    elif text_message == "Рюкзаки/сумки":
        item_type = "bags"
    elif text_message == "Легкие куртки":
        item_type = "light_jacket"
    elif text_message == "Лонгслив/худи":
        item_type = "hoodie"
    elif text_message == "Шорты":
        item_type = "shorts"
    elif text_message == "Маленькие сумки":
        item_type = "small_bags"
    elif text_message == "Футболки":
        item_type = "t_shirts"
    elif text_message == "Часы":
        item_type = "watches"
    elif text_message == "Кошелёк":
        item_type = "wallet"
    elif text_message == "Носки (3 пары)":
        item_type = "socks"
    elif text_message == "Снуд":
        item_type = "snood"
    elif text_message == "Повязка на голову":
        item_type = "bandage"
    elif text_message == "Не уверен что выбрать?":
        item_type = "none"
    else:
        item_type = "none"
    return item_type


def check_region(text_message):
    if text_message == "США":
        region = "usa"
    elif text_message == "Китай":
        region = "china"
    elif text_message == "Великобритания":
        region = "uk"
    elif text_message == "Польша":
        region = "poland"
    else:
        region = "none"
    return region


def check_currency(text_message):
    if text_message == "Евро €":
        currency = "eur"
    elif text_message == "Доллар $":
        currency = "usd"
    elif text_message == "Юань ¥":
        currency = "cny"
    elif text_message == "Фунт £":
        currency = "gbp"
    elif text_message == "Злотый zł":
        currency = "pln"
    else:
        currency = "none"
    return currency


def check_shop(text_message):
    if text_message == "poizon":
        shop = "poizon"
        region = "china"
        currency = "cny"
        shop_delivery = 20 * rates.get_usdt_currency('cny')
    elif text_message == "zalando":
        shop = "zalando"
        region = "poland"
        currency = "pln"
        shop_delivery = 0
    elif text_message == "endclothing":
        shop = "endclothing"
        region = "uk"
        currency = "gbp"
        shop_delivery = 9 * rates.get_usdt_currency('gbp')
    elif text_message == "asphaltgold":
        shop = "asphaltgold"
        region = "poland"
        currency = "eur"
        shop_delivery = 5 * rates.get_usdt_currency('eur')
    elif text_message == "louisaviaroma":
        shop = "louisaviaroma"
        region = "poland"
        currency = "pln"
        shop_delivery = 76 * rates.get_usdt_currency('pln')
    elif text_message == "nbsklep":
        shop = "nbsklep"
        region = "poland"
        currency = "pln"
        shop_delivery = 0
    elif text_message == "adidas (poland)":
        shop = "adidas"
        region = "poland"
        currency = "pln"
        shop_delivery = 0
    elif text_message == "nike":
        shop = "nike"
        region = "poland"
        currency = "pln"
        shop_delivery = 8 * rates.get_usdt_currency('usd')
    elif text_message == "osirisshoes":
        shop = "osirisshoes"
        region = "usa"
        currency = "usd"
        shop_delivery = 19 * rates.get_usdt_currency('usd')
    elif text_message == "farfetch":
        shop = "farfetch"
        region = "usa"
        currency = "usd"
        shop_delivery = 24 * rates.get_usdt_currency('usd')
    elif text_message == "goat":
        shop = "goat"
        region = "usa"
        currency = "usd"
        shop_delivery = 14.5 * rates.get_usdt_currency('usd')
    elif text_message == "eobuwie":
        shop = "eobuwie"
        region = "poland"
        currency = "pln"
        shop_delivery = 0
    elif text_message == "itkkit":
        shop = "itkkit"
        region = "poland"
        currency = "eur"
        shop_delivery = 5 * rates.get_usdt_currency('eur')
    elif text_message == "mrporter":
        shop = "mrporter"
        region = "poland"
        currency = "eur"
        shop_delivery = 5 * rates.get_usdt_currency('eur')
    elif text_message == "solebox":
        shop = "solebox"
        region = "poland"
        currency = "eur"
        shop_delivery = 11 * rates.get_usdt_currency('eur')
    elif text_message == "footpatrol":
        shop = "footpatrol"
        region = "uk"
        currency = "gbp"
        shop_delivery = 1 * rates.get_usdt_currency('gbp')
    elif text_message == "matchesfashion":
        shop = "matchefashion"
        region = "usa"
        currency = "usd"
        shop_delivery = 20 * rates.get_usdt_currency('usd')
    elif text_message == "bdgastore":
        shop = "bdgastore"
        region = "usa"
        currency = "usd"
        shop_delivery = 11 * rates.get_usdt_currency('usd')
    elif text_message == "lapstoneandhammer":
        shop = "lapstoneandhammer"
        region = "usa"
        currency = "usd"
        shop_delivery = 11 * rates.get_usdt_currency('usd')
    elif text_message == "sneakerpolitics":
        shop = "sneakerpolitics"
        region = "usa"
        currency = "usd"
        shop_delivery = 15 * rates.get_usdt_currency('usd')
    elif text_message in blocked_shops:
        shop = text_message
        region = "blocked"
        currency = "none"
        shop_delivery = "none"
    else:
        shop = "other"
        return {
            "region": "none",
            "shop": "none",
            "currency": "none",
            "shop_delivery": "none",
            "net_value": 0,
            "net_shop_delivery": 0,
            "net_delivery": 0,
            "ru_delivery": 0,
            "items": []
        }
    return {
        "region": region,
        "shop": shop,
        "currency": currency,
        "shop_delivery": shop_delivery,
        "net_value": 0,
        "net_shop_delivery": 0,
        "net_delivery": 0,
        "ru_delivery": 0,
        "items": []
    }


def calc_total(orders, id):
    order = orders[id]
    items_count = 0
    order["net_value"] = 0
    order["net_delivery"] = 0
    order["net_shop_delivery"] = order["shop_delivery"]
    for item in order["items"]:
        order["net_value"] += item["value"] * item["quantity"]
        items_count += item["quantity"]
        order["net_delivery"] += item["delivery"] * item["quantity"]
    if order["region"] == "china":
        order["ru_delivery"] = 350
        order["net_shop_delivery"] *= items_count
    order["net_value"] = round(order["net_value"])
    order["net_delivery"] = round(order["net_delivery"])
    order["net_shop_delivery"] = round(order["net_shop_delivery"])
    write_order(id, {id: order})


def calc_item(text_message, orders, id):
    if re.search(r"\d+", text_message):
        usdt = rates.get_usdt_rate()
        i = len(orders[id]["items"]) - 1
        order = orders[id]
        order["items"][i]["value"] = float(
            text_message) * rates.get_usdt_currency(order["currency"])
        if order["region"] == "china":
            if order["items"][i]["category"] == "bandage":
                delivery = 1.45
            elif order["items"][i]["category"] == "snood":
                delivery = 14.5 * 0.2
            elif order["items"][i]["category"] == "socks":
                delivery = 14.5 * 0.25
            elif order["items"][i]["category"] == "wallet":
                delivery = 14.5 * 0.4
            elif order["items"][i]["category"] == "watches":
                delivery = 14.5 * 0.4
            elif order["items"][i]["category"] == "t_shirts":
                delivery = 14.5 * 0.4
            elif order["items"][i]["category"] == "small_bags":
                delivery = 14.5 * 0.5
            elif order["items"][i]["category"] == "shorts":
                delivery = 14.5 * 0.5
            elif order["items"][i]["category"] == "hoodie":
                delivery = 14.5 * 0.8
            elif order["items"][i]["category"] == "light_jacket":
                delivery = 14.5 * 0.8
            elif order["items"][i]["category"] == "bags":
                delivery = 14.5 * 0.9
            elif order["items"][i]["category"] == "pants":
                delivery = 14.5 * 0.9
            elif order["items"][i]["category"] == "jackets":
                delivery = 14.5 * 1.5
            elif order["items"][i]["category"] == "sneakers":
                delivery = 14.5 * 1.5
            elif order["items"][i]["category"] == "boots":
                delivery = 14.5 * 2.2
            delivery = delivery * usdt * 1.02 * 1.15
        elif order["region"] == "poland":
            if order["items"][i]["category"] == "bandage":
                delivery = 563
            elif order["items"][i]["category"] == "snood":
                delivery = 563
            elif order["items"][i]["category"] == "socks":
                delivery = 563
            elif order["items"][i]["category"] == "wallet":
                delivery = 563
            elif order["items"][i]["category"] == "watches":
                delivery = 563
            elif order["items"][i]["category"] == "t_shirts":
                delivery = 563
            elif order["items"][i]["category"] == "small_bags":
                delivery = 563
            elif order["items"][i]["category"] == "shorts":
                delivery = 563
            elif order["items"][i]["category"] == "hoodie":
                delivery = 844
            elif order["items"][i]["category"] == "light_jacket":
                delivery = 844
            elif order["items"][i]["category"] == "bags":
                delivery = 844
            elif order["items"][i]["category"] == "pants":
                delivery = 844
            elif order["items"][i]["category"] == "jackets":
                delivery = 1126
            elif order["items"][i]["category"] == "sneakers":
                delivery = 1126
            elif order["items"][i]["category"] == "boots":
                delivery = 1688
        elif order["region"] == "uk":
            if order["items"][i]["category"] == "bandage":
                delivery = 991
            elif order["items"][i]["category"] == "snood":
                delivery = 991
            elif order["items"][i]["category"] == "socks":
                delivery = 991
            elif order["items"][i]["category"] == "wallet":
                delivery = 991
            elif order["items"][i]["category"] == "watches":
                delivery = 991
            elif order["items"][i]["category"] == "t_shirts":
                delivery = 991
            elif order["items"][i]["category"] == "small_bags":
                delivery = 991
            elif order["items"][i]["category"] == "shorts":
                delivery = 991
            elif order["items"][i]["category"] == "hoodie":
                delivery = 1524
            elif order["items"][i]["category"] == "light_jacket":
                delivery = 1524
            elif order["items"][i]["category"] == "bags":
                delivery = 1524
            elif order["items"][i]["category"] == "pants":
                delivery = 1524
            elif order["items"][i]["category"] == "jackets":
                delivery = 1981
            elif order["items"][i]["category"] == "sneakers":
                delivery = 1981
            elif order["items"][i]["category"] == "boots":
                delivery = 3048
        elif order["region"] == "usa":
            if order["items"][i]["category"] == "bandage":
                delivery = 14
            elif order["items"][i]["category"] == "snood":
                delivery = 14
            elif order["items"][i]["category"] == "socks":
                delivery = 14
            elif order["items"][i]["category"] == "wallet":
                delivery = 14
            elif order["items"][i]["category"] == "watches":
                delivery = 14
            elif order["items"][i]["category"] == "t_shirts":
                delivery = 14
            elif order["items"][i]["category"] == "small_bags":
                delivery = 18
            elif order["items"][i]["category"] == "shorts":
                delivery = 18
            elif order["items"][i]["category"] == "hoodie":
                delivery = 18
            elif order["items"][i]["category"] == "light_jacket":
                delivery = 18
            elif order["items"][i]["category"] == "bags":
                delivery = 18
            elif order["items"][i]["category"] == "pants":
                delivery = 18
            elif order["items"][i]["category"] == "jackets":
                delivery = 34
            elif order["items"][i]["category"] == "sneakers":
                delivery = 34
            elif order["items"][i]["category"] == "boots":
                delivery = 44.5
            delivery = delivery * 1.2 * 1.05 * usdt
        order["items"][i]["delivery"] = delivery
        order = {id: order}
        write_order(id, order)
    else:
        bot.send_message(id, 'Не распознал сумму')

def calc_subvalues(id, orders):
    order = orders[id]
    fixed_expenses = 180
    hidden_fees = 1.02
    lost_insurance = round(order["net_value"] * 0.03)
    defect_insurance = round(order["net_value"] * 0.02)
    return_no_reason = round(order["net_value"] * 0.05)
    rate = round(rates.get_usdt_currency(order["currency"]) * hidden_fees, 2)
    comission = round(order["net_value"] * 0.13 + 1800 - 750 - 750)
    result = round(order["net_delivery"] * hidden_fees + order["ru_delivery"] + order["net_value"] +
                   fixed_expenses + lost_insurance + order["net_shop_delivery"] + comission + defect_insurance + return_no_reason)
    return {
        "fixed_expenses" : fixed_expenses,
        "rate" : rate,
        "lost_insurance" : lost_insurance,
        "defect_insurance" : defect_insurance,
        "return_no_reason" : return_no_reason,
        "comission" : comission,
        "result" : result
    }

def print_result(id, orders):
    order = orders[id]
    subvalues = calc_subvalues(id, orders)
    markup = types.ReplyKeyboardMarkup()
    retry = types.KeyboardButton("Создать новый заказ")
    add = types.KeyboardButton("Добавить ещё одну вещь")
    multiply = types.KeyboardButton("Изменить количество последнего товара")
    change_price = types.KeyboardButton("Изменить цену последнего товара")
    markup.row(retry, add)
    markup.row(multiply)
    markup.row(change_price)
    reply = '\n==========================\n\nТовары в заказе:\n'
    index = 1
    for item in order["items"]:
        reply += f'\n--Товар {index}--\n\
Категория: {item["category"]}\n\
Стоимость: {round(item["value"])} руб.\n\
Доставка до РФ: {round(item["delivery"])} руб.\n\
Количество: {item["quantity"]}\n'
        index += 1
    bot.send_message(id, f'<b>Сумма заказа: {subvalues["result"]} руб.</b>\n\n\
Стоимость товаров: {order["net_value"]} руб.\n\
Стоимость доставки магазина: {order["net_shop_delivery"]} руб.\n\
Стоимость доставки до РФ: {order["net_delivery"]} руб.\n\
Стоимость доставки по РФ: {order["ru_delivery"]} руб.\n\
Расходы на оформление: {subvalues["fixed_expenses"]} руб.\n\n\
Страховка от утери: {subvalues["lost_insurance"]} руб.\n\
Страховка от брака: {subvalues["defect_insurance"]} руб.\n\
Возможность возврата: {subvalues["return_no_reason"]} руб.\n\n\
Комиссия сервиса: {subvalues["comission"]} руб.\n\
<i>В комиссию входит стоимость всей работы по подбору, выкупу, контролю доставки, уведомлению об изменении статуса и регулированию возможных проблем с заказом</i>\n\n\
Курс: {subvalues["rate"]} руб.\n\
            {reply}', reply_markup=markup, parse_mode='HTML')


def print_short(id, orders):
    global total_price_requests, today_price_requests, now
    total_price_requests += 1
    if datetime.now().timestamp() - 86400 >= datetime.now().timestamp():
        now = datetime.now().timestamp()
        today_price_requests = 0
    today_price_requests += 1
    subvalues = calc_subvalues(id, orders)
    markup = types.ReplyKeyboardMarkup()
    retry = types.KeyboardButton("Создать новый заказ")
    add = types.KeyboardButton("Добавить ещё одну вещь")
    full = types.KeyboardButton("Показать весь заказ")
    multiply = types.KeyboardButton("Изменить количество последнего товара")
    change_price = types.KeyboardButton("Изменить цену последнего товара")
    markup.row(retry, add)
    markup.row(multiply)
    markup.row(change_price)
    markup.row(full)
    bot.send_message(id, f'Сумма заказа: {subvalues["result"]} руб.', reply_markup=markup)


def write_stages(id, stage):
    with open(f'./data/stage_{id}.txt', 'w') as convert_file:
        convert_file.write(json.dumps({id: stage}))


def read_stages(id):
    with open(f'./data/stage_{id}.txt') as convert_file:
        dict = json.load(convert_file)
    return dict[str(id)]


def write_order(id, order):
    with open(f'./data/order_{id}.txt', 'w') as convert_file:
        convert_file.write(json.dumps(order))


def read_order(id):
    with open(f'./data/order_{id}.txt') as convert_file:
        dict = json.load(convert_file)
    return dict


try:
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
except (ConnectionError, ReadTimeout) as e:
    sys.stdout.flush()
    os.execv(sys.argv[0], sys.argv)
else:
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
