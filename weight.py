import csv, re, json

orders_file = "hpd.csv"
weight_files = ["post.csv", "cdek.csv"]

MAX_LEN = 6

"""
Главная функция генерации лидерборда
"""
def generate_leaderboard():
    leaderboard = {}
    for search_length in range(MAX_LEN):
        with open(orders_file) as csvfile:
            reader = csv.reader(csvfile)
            leaderboard = search_sequences(reader, search_length, leaderboard)
    for seq in leaderboard:
        for fio in leaderboard[seq]["names"]:
            weight = check_weight(fio)
            if weight != 0:
                leaderboard[seq]["weights"].append(weight)
        if leaderboard[seq]["weights"]:
            leaderboard[seq]["average"] = round(sum(leaderboard[seq]["weights"]) / len(leaderboard[seq]["weights"]), 3)
    save_leaderboard(leaderboard)

"""
Инициализация лидерборда, поиск всех последовательностей в нём

"""
def search_sequences(reader, search_length, leaderboard):
    search_length += 1
    for row in reader:
        link = row[5]
        fio = row[7].strip()
        if link and link != "Link":
            if matches := re.search(r"https://[^ ]+ ([A-Za-z 0-9.\"\']+)", link):
                name = matches.group(1).strip()
                words = name.split()
                if len(words) > search_length:
                    for start in range(len(words) - search_length + 1):
                        sequence = ''
                        for i in range(search_length):
                            word = words[start+i]
                            if len(word) > 2:
                                if word[-1] == "\"":
                                    word = word[:-1]
                                if word[0] == "\"":
                                    word = word[1:]
                            sequence += word + " "
                        sequence = sequence.strip().lower()
                        if sequence in leaderboard:
                            leaderboard[sequence]["count"] += 1
                            leaderboard[sequence]["names"].append(fio)
                        else:
                            leaderboard[sequence] = {
                                "names" : [fio],
                                "count" : 1,
                                "weights" : [],
                                "average" : "none"
                            }
    return leaderboard


"""
Поиск веса из китайских таблиц
"""
def check_weight(fio):
    count = 0
    weight = 0
    for filename in weight_files:
        if filename == "post.csv":
                row_fio = 11
        else:
            row_fio = 12
        with open(filename) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[row_fio].strip() == fio:
                    try:
                        weight = float(row[9])
                        count += 1
                    except:
                        return 0
                if count > 1:
                    return 0
    return weight


"""
Основная вызываемая функция. Ищет в лидерборде нужную нам последовательность.

"""
def find_weight(inp):
    leaderboard = get_leaderboard()
    words = inp.split()
    answers = []
    for i in range(len(words)):
        seq_len = i + 1
        for start in range(len(words) - seq_len + 1):
            sequence = ''
            for j in range(seq_len):
                word = words[start+j]
                if len(word) > 2:
                    if word[-1] == "\"":
                        word = word[:-1]
                    if word[0] == "\"":
                        word = word[1:]
                sequence += word + " "
            sequence = sequence.strip().lower()
            if sequence in leaderboard.keys():
                answers.append([sequence, leaderboard[sequence]["average"], len(leaderboard[sequence]["weights"])])
    i = len(answers)
    best_index = -1
    best_len = 0
    best_trust = 1
    while i > 0:
        i -= 1
        if len(leaderboard[answers[i][0]]["weights"]) > best_trust and len(answers[i][0].split()) >= best_len:
            best_index = i
            best_len = len(answers[i][0].split())
            best_trust = len(leaderboard[answers[i][0]]["weights"])
    if best_index != -1:
        weight = answers[best_index][1]
        ans = f"Вес: {weight}\n"
        if 1.2 < weight < 1.8:
            ans += "Подходящие категории: Кроссовки, Зимние куртки"
        elif weight >= 1.8:
            ans += "Подходящие категории: Ботинки"
        elif 0.8 <= weight <= 1.2:
            ans += "Подходящие категории: Лонгслив/худи, Легкие куртки, Штаны и джинсы, Рюкзаки и сумки"
        elif weight >= 0.4:
            ans += "Подходящие категории: Футболки, Шорты, Маленькие сумки, Часы, Кошелёк"
        else:
            ans += "Подходящие категории: Снуд, Носки (3 пары)"
        ans += f"\n\nЛучшее совпадение: \"{answers[best_index][0]}\"\nДлина выборки: {best_trust}\n"
    else:
        ans = 'Совпадений не найдено'
    return ans


"""
Сохраняет лидерборд в файл
"""
def save_leaderboard(leaderboard):
    with open("leaderboard.json", "w") as file:
        final_dict = {}
        for seq in leaderboard:
            if len(leaderboard[seq]["weights"]) > 0:
                final_dict[seq] = leaderboard[seq].copy()
        file.write(json.dumps(final_dict, indent=2))

"""
Достаёт лидерборд из файла
"""
def get_leaderboard():
    with open("leaderboard.json", "r") as file:
        return json.load(file)




if __name__ == '__main__':
    generate_leaderboard()

