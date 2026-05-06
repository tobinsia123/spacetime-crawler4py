import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import Counter
import atexit

visited_urls = set()
word_counts = Counter()
subdomains = {}
longest_page = ("", 0)

# For extra credit (+2)
seen_exact = set()
seen_near = []

STOP_WORDS = {
    "a","about","above","after","again","against","all","am","an","and",
    "any","are","aren't","as","at","be","because","been","before","being",
    "below","between","both","but","by","can't","cannot","could","couldn't",
    "did","didn't","do","does","doesn't","doing","don't","down","during",
    "each","few","for","from","further","had","hadn't","has","hasn't",
    "have","haven't","having","he","he'd","he'll","he's","her","here",
    "here's","hers","herself","him","himself","his","how","how's","i",
    "i'd","i'll","i'm","i've","if","in","into","is","isn't","it","it's",
    "its","itself","let's","me","more","most","mustn't","my","myself",
    "no","nor","not","of","off","on","once","only","or","other","ought",
    "our","ours","ourselves","out","over","own","same","shan't","she",
    "she'd","she'll","she's","should","shouldn't","so","some","such",
    "than","that","that's","the","their","theirs","them","themselves",
    "then","there","there's","these","they","they'd","they'll","they're",
    "they've","this","those","through","to","too","under","until","up",
    "very","was","wasn't","we","we'd","we'll","we're","we've","were",
    "weren't","what","what's","when","when's","where","where's","which",
    "while","who","who's","whom","why","why's","with","won't","would",
    "wouldn't","you","you'd","you'll","you're","you've","your","yours",
    "yourself","yourselves"
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
    # resp.raw_response: this is where the page actually is.
    global visited_urls, word_counts, subdomains, longest_page

    links = []

    # Skip bad responses
    if resp.status != 200 or not resp.raw_response:
        return links

    try:
        html = resp.raw_response.content

        # Skip large pages
        if len(html) > 2_000_000:
            return links

        soup = BeautifulSoup(html, "lxml")

        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        visited_urls.add(url)

        # Text Processing
        text = soup.get_text()
        words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())

        words = [w for w in words if w not in STOP_WORDS]

        # Skip low info pages
        if len(words) < 30:
            return links

        # Dupicate detection (extra credit)
        if is_duplicate(words):
            return links

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


# NEW FUNCTION (extra credit)
def is_duplicate(words):
    word_set = set(words)

    if not word_set:
        return True

    # exact duplicate
    signature = " ".join(words)
    if signature in seen_exact:
        return True
    seen_exact.add(signature)

    # near duplicate (Jaccard)
    for prev in seen_near[-300:]:
        union = word_set | prev
        if not union:
            continue

        similarity = len(word_set & prev) / len(union)
        if similarity > 0.9:
            return True

    seen_near.append(word_set)
    return False


def is_valid(url):
    # Decide whether to crawl this url or not. 
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        # Only http/https
        if parsed.scheme not in {"http", "https"}:
            return False

        # Strict domain filter
        allowed = (
            netloc.endswith(".ics.uci.edu") or
            netloc.endswith(".cs.uci.edu") or
            netloc.endswith(".informatics.uci.edu") or
            netloc.endswith(".stat.uci.edu")
        )
        if not allowed:
            return False

        # Avoid swiki spam
        if "swiki" in parsed.netloc:
            return False
        
        if path.startswith("/people") or path.startswith("/happening/"):
            return False

        # Filter unwanted file types
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ipynb"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1"
            r"|thmx|mso|arff|rtf|jar|csv"
            r"|rm|smil|wmv|swf|wma|zip|rar|gz|sql|cpp|c|jar|war)$",
            parsed.path.lower()
        ):
            return False

        # Trap detection
        if len(url) > 200:
            return False

        if url.count("/") > 10:
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