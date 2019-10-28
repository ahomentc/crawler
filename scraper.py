import re
import os
import time
import hashlib
import tldextract
import operator
from lxml import etree
from io import StringIO, BytesIO
from bs4 import BeautifulSoup
from bs4.element import Comment
from urllib.parse import urlparse, urldefrag, urljoin, urlunsplit

# Holds the count for total number of pages scraped
num_unique_pages = 0

# Check to see if the link's been visited before
visited = set()

# Dictionary containing the last time visited of each link
time_visited = dict()

# Dictionary containing the hash objects of certain pages
hashed_content = dict()

# Holds all the stop words
stop_words = set()

# Holds all the subdomains found from scraping
ics_sub_domains = dict()

# Holds the word count
word_count = dict()

longest_word_count = 0
longest_word_count_url = ""

# Inserts all stop words into a set
for line in open("stop_words.txt"):
    stop_words.add(line.rstrip())

# Finds the number of subdomains and the number of unique pages
def find_sub_domains(valid_links):
    for link in valid_links:
        extracted_url = tldextract.extract(link)
        subdomain = extracted_url[0]
        if (subdomain.find(".ics") >= 0 and subdomain != "www.ics"):
            parsed = urlparse(link, allow_fragments=False)
            parsed_sd = parsed[1]
            if parsed_sd not in ics_sub_domains:
                ics_sub_domains[parsed_sd] = 1
                isd = open("ics_subdomains.txt", "a")
                isd.write(parsed_sd+"\n")
                isd.close()
            else:
                ics_sub_domains[parsed_sd] += 1
    # print(ics_sub_domains)

# Gets all visible text from html
def get_text(element):
    if element.parent.name in ["[document]", "noscript", "header", "html", "meta", "head", "input", "script", "style"]:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(result, url):
    soup = BeautifulSoup(result, features="html.parser")
    all_text = soup.findAll(text=True)
    visible_texts = filter(get_text, all_text)
    text = u" ".join(t.strip() for t in visible_texts)
    num_words = 0

    for t in text.split():
        num_words+=1
        pattern = re.findall('[a-zA-Z0-9_]+', t.lower(), re.ASCII)
        if len(pattern) > 0:
            if pattern[0] not in stop_words:
                if pattern[0] not in word_count:
                    word_count[pattern[0]] = 1
                else:
                    word_count[pattern[0]] += 1

    if num_words > longest_word_count:
        longest_word_count = num_words
        longest_word_count_url = url

def print_word_count():
    count = 1
    for k,v in sorted(word_count.items(), key=lambda x: (-x[1], x[0])):
        if count == 11:
            break
        print(count, k, v)
        count += 1

def scraper(url, resp):
    status = resp.status
    error  = resp.error
    url    = resp.url

    # Ignore urls that don't have a status code of 200 or have no content
    if status != 200 or (status == 200 and resp.raw_response.content == ''):
        return []
    
    try:
        content = resp.raw_response.content
        html = etree.HTML(content)
        result = etree.tostring(html, pretty_print=True, method="html")
    except:
        return []

    # Extract only valid links from url
    valid_links = check_for_duplicates(url, resp, result)

    # Extract only valid text from url
    text_from_html(result, url)

    ### REPORT ###
    global num_unique_pages
    num_unique_pages += 1

    # Finds all subdomains in ics.uci.edu
    find_sub_domains(valid_links)

    print("============================")
    print("status: ", status)
    print("url: ", url)
    print("most common ics subdomain: ", max(ics_sub_domains.items(), key=operator.itemgetter(1))[0], max(ics_sub_domains.items(), key=operator.itemgetter(1))[1])
    print("total unique pages found: ", num_unique_pages)
    print("Adding: {} urls".format(len(valid_links)))
    print("Longest Word Count URL: ", longest_word_count_url, " with count ", longest_word_count)
    print("Word Count: ")
    print_word_count()
    print("============================\n")
    ### END REPORT ###

    return valid_links

# Scrapes link for text and other links:
#   if the current page is similar to another page that has already been scraped,
#   that page is useless so don't do anything
def check_for_duplicates(url, resp, result):
    # Initialize bs4 and get data from these tags
    soup = BeautifulSoup(result, features="lxml")
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title', 'paragraph', 'p'])]

    # Get text from the specified tags
    visible_text = soup.getText().replace("\n","").replace(" ","").replace("/","")
    re.sub(r'[^\w]', '',visible_text)

    # Hashing function to find duplicate sites
    hash_object = hashlib.md5(str(visible_text).encode('utf-8')).hexdigest()
    if hash_object in hashed_content:
        print("\nFOUND DUPLICATE: url(", url, ")")
        print("SISTER: url(", hashed_content[hash_object],")")
        return []
    else:
        hashed_content[hash_object] = url

    links = extract_next_links(url, resp)
    return links


def extract_next_links(url, resp):
    urls=[]
    content = resp.raw_response.content
    html = etree.HTML(content)
    for href in html.xpath('//a/@href'):
        href = urldefrag(href)[0]
        href_normalized = urljoin(url, href, allow_fragments=False) # normalizes URL and converts relative -> absolute
        href_normalized_no_extension = os.path.splitext(href_normalized)[0] # removes extension
        if href_normalized_no_extension not in visited:
            if (is_valid(href_normalized) and is_valid(href_normalized_no_extension)):
                urls.append(href_normalized_no_extension)
                visited.add(href_normalized_no_extension)
    return urls


def is_valid(url):
    try:
        parsed = urlparse(url, allow_fragments=False)

        extracted_url = tldextract.extract(url)
        subdomain = extracted_url[0]
        domain = extracted_url[1]
        suffix = extracted_url[2]

        allowed_subdomains = [".ics", ".cs", ".stat", "informatics"]
        for sd in allowed_subdomains:
            if (subdomain.find("archive.ics") >= 0):
                return False
            if ((subdomain.find(sd) >= 0) and (domain == "uci") and (suffix == "edu")):
                if parsed.scheme not in set(["http", "https"]):
                    return False
                else:
                    return not re.match(
                        r".*\.(css|js|bmp|gif|jpe?g|ico"
                        + r"|png|tiff?|mid|mp2|mp3|mp4"
                        + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                        + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                        + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                        + r"|epub|dll|cnf|tgz|sha1"
                        + r"|thmx|mso|arff|rtf|jar|csv"
                        + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", url)
        return False

    except TypeError:
        print ("TypeError for ", parsed)
        raise