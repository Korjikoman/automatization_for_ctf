from flagChecker import FlagChecker
from FlagSniffer import FlagSniffer
from login import Login
from settings import *
import requests as r
import time


login_url = url + "/auth/signin"
session = r.Session()
headers = r.utils.default_headers()

headers.update(
    {
        'User-Agent': 'My User Agent 1.0',
    }
)

try:
    while True:
  
        # логинимся
        login_user = Login(email=email, password=password, session=session, headers=headers)
        if login_user.login(login_url):
            # ищем флаги и отбираем новые
            sniffer = FlagSniffer(session, url, flags_file, headers)
            flags = sniffer.sniff()

            # проверяем новые флаги
            checker = FlagChecker(url_checker, flags)
            if checker.check_flags():
                print(f"✅Найден верный флаг!✅")
            
            print(f"Посплю {SLEEP_TIME} секунд...😪💤💤💤")    
            time.sleep(SLEEP_TIME)

except KeyboardInterrupt:
    print("\n Ctrl+C")


    