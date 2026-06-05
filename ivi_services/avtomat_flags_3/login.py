import requests

class Login:
    def __init__(self, email, password, session, headers):
        self.email = email
        self.password = password
        self.session = session
        self.headers = headers

    def login(self, login_url):
        g = self.session.get(login_url)
        if g.status_code == 200:
            data = {"email" : self.email,
                    "password" : self.password}
            request = self.session.post(login_url, data)
            if request.status_code == 200:
                print("Залогинились!")
                return request
            
            else:
                return 0
        else:
            print(f"Error with get-request {g.text}")
            return 0
            
        
