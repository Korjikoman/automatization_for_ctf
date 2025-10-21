import requests


class FlagChecker:
    def __init__(self, path, flags):
        self.path = path
        self.flags = flags
        self.session = requests.Session()

    def check_flags(self):
        for flag in self.flags:
            url = self.path + flag
            print(f"Проверяю {flag}")
            if self.session.get(url).text.strip() == 'Верный флаг':
                return 1
        return 0
