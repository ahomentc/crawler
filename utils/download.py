import requests
import cbor
import time

from utils.response import Response

def download(url, config, logger=None):
    host, port = config.cache_server
    count = 1
    # changed this
    # got it from Piazza
    while True:
        if count == 3:
            return False
        try:
            resp = requests.get(
                f"http://{host}:{port}/",
                params=[("q", f"{url}"), ("u", f"{config.user_agent}")],
                timeout=(5,30))
            break
        except:
            print("waiting...", count, "(",url,")")
            count += 1
            continue
    if resp:
        return Response(cbor.loads(resp.content))
    logger.error(f"Spacetime Response error {resp} with url {url}.")
    return Response({
        "error": f"Spacetime Response error {resp} with url {url}.",
        "status": resp.status_code,
        "url": url})