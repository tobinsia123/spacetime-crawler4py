import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import Counter
import atexit

visited_urls = set()
word_counts = Counter()
subdomains = {}
longest_page = ("", 0)

STOP_WORDS = {
    "the","a","and","of","to","in","is","for","on","with",
    "that","by","this","it","from","as","at","be","are","was","were"
}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    global visited_urls, word_counts, subdomains, longest_page

    links = []

    # Skip bad responses
    if resp.status != 200 or not resp.raw_response:
        return links

    visited_urls.add(url)

    try:
        html = resp.raw_response.content
        soup = BeautifulSoup(html, "lxml")

        visited_urls.add(url)

        # Text Processing
        text = soup.get_text()
        words = re.findall(r"[a-zA-Z]{2,}", text.lower())

        words = [w for w in words if w not in STOP_WORDS]

        # Update global word counts
        word_counts.update(words)

        # Update longest page
        if len(words) > longest_page[1]:
            longest_page = (url, len(words))

        # Subdomain Tracking
        parsed = urlparse(url)
        subdomain = parsed.netloc

        if subdomain not in subdomains:
            subdomains[subdomain] = 0
        subdomains[subdomain] += 1

        # Link Extraction
        for tag in soup.find_all("a", href=True):
            href = tag["href"]

            absolute = urljoin(url, href)
            absolute, _ = urldefrag(absolute)

            links.append(absolute)

    except Exception as e:
        print("Error parsing:", url, e)
    
    print("Scraping:", url)
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        # Only http/https
        if parsed.scheme not in {"http", "https"}:
            return False

        # Stay in UCI domains
        if not parsed.netloc.endswith(".uci.edu"):
            return False

        # Avoid query traps
        if parsed.query:
            return False

        # Avoid swiki spam
        if "swiki" in parsed.netloc:
            return False

        # Filter unwanted file types
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1"
            r"|thmx|mso|arff|rtf|jar|csv"
            r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower()
        ):
            return False
    
        # Trap detection, might need to change this!!!
        if len(url) > 200:
            return False

        if url.count("/") > 10:
            return False

        if url.count("-") > 10:
            return False

        return True

    except TypeError:
        print("TypeError for", url)
        raise

def print_results():
    print("\n=== RESULTS ===")
    print("Unique pages:", len(visited_urls))
    print("Longest page:", longest_page)
    print("Top 50 words:", word_counts.most_common(50))
    print("Subdomains:", subdomains)

atexit.register(print_results)