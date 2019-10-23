import re
from urllib.parse import urlparse
from lxml import etree
from io import StringIO, BytesIO
import time
from urllib.parse import urldefrag

# You need to "normalize" the links. Normalization includes making them absolute, and getting rid of the fragment part.

# Holds the longest page in terms of number of words
longest_page = 0
longest_page_url = ""

# Set containing all English stopWords
stop_words = set()

# Dictionary containing frequency of all words found
word_frequency = dict()

# Check to see if the link's been visited before
visited = set()

# Dictionary containing the last time visited of each link
time_visited = dict()

# Inserts all stopWords into a set
def insert_stop_words(file):
    for line in open(file):
        stop_words.add(line.rstrip())

# still need to tweak this!
# Extracts all "valid" words from a page and puts it in a list
def extract_all_words(content):
    html = etree.HTML(content)
    words = html.xpath("//text()")
    stripped_words = [word.rstrip().strip() for word in words]
    word_list = list(filter(None, stripped_words))

    all_words = list()
    for word in word_list:
        if (len(word) > 0):
            pattern = re.findall("[a-zA-Z0-9_]+", word.lower(), re.ASCII)
            all_words.extend(pattern)
    return all_words

# Prints the n most frequent words found in all pages
def print_most_frequent_words(n):
    i = 1
    for k,v in sorted(word_frequency.items(), key=lambda x: (x[1], x[0]), reverse=True):
        print(f"{i}: {k} -> {v}")
        i += 1
        if (i == n+1):
            break

# Inserts all text found in page to word_frequency dictionary
def insert_into_word_freq(content):
    all_words = extract_all_words(content)
    for word in all_words:
        if word not in word_frequency:
            word_frequency[word] = 1
        else:
            word_frequency[word] += 1

# Counts the number of unique links given a list of links
def count_unique_pages(links):
    unique_pages = set()
    for link in links:
        if is_valid(link):
            unique_pages.add(link)
    return len(unique_pages)

# Returns the number of words in a page
def count_words_page(content):
    return len(extract_all_words(content))

def scraper(url, resp):
    status = resp.status
    error = resp.error
    url = resp.url

    # print("--------")
    # print(status)
    # print(error)
    # print(url)
    # print("----")

    # Politeness. Check if diff is less than 500 miliseconds.
    # This is wrong though. It should just have a delay of 500 miliseconds.
    # Where to put this delay though? In this file??
    current_time = int(round(time.time() * 1000))
    if url in time_visited:
        if current_time - time_visited[url] < 500:
            return []
    time_visited[url] = current_time

    if status != 200 or (status == 200 and resp.raw_response.content == ''):
        return []

    content = resp.raw_response.content
    html = etree.HTML(content)
    result = etree.tostring(html, pretty_print=True, method="html")

    links = extract_next_links(url, resp)

    ### REPORT ###
    print("=================================")
    print("url: ", url)
    print("status: ", status)
    print("=================================")

    # 1. Count unique pages
    num_unique_pages = count_unique_pages(links)

    # 2. Longest page in terms of number of words
    global longest_page         # should not be using global??
    global longest_page_url

    num_words_page = count_words_page(content)
    if (num_words_page > longest_page):
        longest_page = num_words_page
        longest_page_url = url

    # 3. 50 most common words in the entire set of pages
    # step 1: add all stopWords to set
    stop_word_file = "./stop_words.txt"
    insert_stop_words(stop_word_file)       # need to fix this... only need to call it once

    # step 2: add all text from content to word_frequency dictionary
    insert_into_word_freq(content)
    # print_most_frequent_words(50)         # prints the n most frequent words in the entire set of pages
    
    # print statements
    print("num words in page: ", num_words_page)
    print("num unique pages found: ", num_unique_pages)
    print("longest page in entire set: ", longest_page)
    print("longest page url in entire set: ", longest_page_url)
    # print_most_frequent_words(50)
    print("---------------------------------\n")
    ### RETURN ###

    return [link for link in links if is_valid(link)]

# this should be working now
def extract_next_links(url, resp):
    # Implementation requred.
    # passed in the url and response from scraper.
    # find all the links in the html and return a list of them

    urls=[]
    content = resp.raw_response.content
    html = etree.HTML(content)
    for href in html.xpath('//a/@href'):
        href = urldefrag(href)[0]
        if href not in visited:
            urls.append(href)
            visited.add(href)
    return urls

def is_valid(url):
    try:
        parsed = urlparse(url, allow_fragments=False)
        if parsed.netloc not in set(["www.informatics.uci.edu", "www.ics.uci.edu", "www.cs.uci.edu", "www.stat.uci.edu", "www.today.uci.edu/department/information_computer_sciences"]):
            return False
        if parsed.scheme not in set(["http", "https"]):
            return False
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
