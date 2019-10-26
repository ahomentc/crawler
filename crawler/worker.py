from threading import Thread

from utils.download import download
from utils import get_logger
from scraper import scraper
import time
from urllib.parse import urlparse

class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        super().__init__(daemon=True)
        self.time_visited = dict()
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            # Politeness. Check if diff is less than 500 miliseconds.
            current_time = int(round(time.time() * 1000))
            parsed = urlparse(tbd_url, allow_fragments=False)
            if parsed.netloc in self.time_visited:
                if current_time - self.time_visited[parsed.netloc] < 500:
                    # print("sleeping for ", (500-(current_time-time_visited[parsed.netloc])-1) * .001)
                    time.sleep(((500-(current_time-self.time_visited[parsed.netloc]))+10) * .001)
            current_time = int(round(time.time() * 1000))
            self.time_visited[parsed.netloc] = current_time

            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)
            time.sleep(self.config.time_delay)
