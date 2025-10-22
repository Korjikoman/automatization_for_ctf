
from FlagSniffer import FlagSniffer
from login import Login
from settings import *
import requests as r
import time


login_url = url + "/auth/signin"
session = r.Session()
headers = r.utils.default_headers()


try:
    while True:
  
        # логинимся
        login_user = Login(email=email, password=password, session=session, headers=headers)
        response = login_user.login(login_url)
        if response != 0:

            headers.update(
                {
                    "User-Agent": user_agent,
                    "Content-Type": response.headers['content-type'],
                    "Origin": url,

                }
            )
            # ищем флаги и отбираем новые
            sniffer = FlagSniffer(session, url, flags_file, headers, last_id_file, url_checker)
            flags = sniffer.sniff()

            
            
            print(f"Посплю {SLEEP_TIME} секунд...😪💤💤💤")    
            time.sleep(SLEEP_TIME)

except KeyboardInterrupt:
    print("\n Ctrl+C")


    
