import re
from collections import Counter, deque
from urllib.parse import parse_qs, urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import atexit

visited_urls = set()
word_counts = Counter()
subdomains = {}
longest_page = ("", 0)
recent_links = deque(maxlen=30)

# For extra credit (+2)
seen_exact = set()
seen_near = []

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
    # resp.raw_response: this is where the page actually is.

    # extract all valid outgoing links from webpage
    global visited_urls, word_counts, subdomains, longest_page

    links = []

    # Skip bad responses (if pages are empty or there are failed requests)
    if resp.status != 200 or not resp.raw_response:
        return links

    try:
        html = resp.raw_response.content

        # Skip large pages
        if len(html) > 2_000_000:
            return links

        # parse through any html content
        soup = BeautifulSoup(html, "lxml")

        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        # mark url as visited
        visited_urls.add(url)

        # Text Processing
        # extract text + tokenize the words
        text = soup.get_text()
        words = re.findall(r"[a-zA-Z]{2,}", text.lower())

        # get rid of common stop words
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

        # track the amt of pages in the subdomain
        if subdomain not in subdomains:
            subdomains[subdomain] = 0
        subdomains[subdomain] += 1

        # Link Extraction
        for tag in soup.find_all("a", href=True):
            href = tag["href"]

        # converts relative url -> absolute url
            absolute = urljoin(url, href)
        # remove fragment identifiers
            absolute, _ = urldefrag(absolute)

            links.append(absolute)

    except Exception as e:
        print("Error parsing:", url, e)
    
    #print("Scraping:", url)
    return links


# NEW FUNCTION (extra credit)
def is_duplicate(words):
    word_set = set(words)

    # empty pages would be duplicates
    if not word_set:
        return True

    # exact duplicate using full txt signature to identify
    signature = " ".join(words)
    if signature in seen_exact:
        return True
    seen_exact.add(signature)

    # near duplicate (Jaccard)
    # compare with recent pages
    for prev in seen_near[-300:]:
        union = word_set | prev
        if not union:
            continue
        
        # if similar, treat as duplicate
        similarity = len(word_set & prev) / len(union)
        if similarity > 0.9:
            return True

    # store page to use for future comparisons
    seen_near.append(word_set)

    # retains recent pages
    if len(seen_near) > 300:
        del seen_near[:-300]
    return False

# trap detection
# checks if 2 URLs are diff by 1 query parameter
def is_same_except_one_query_param(url, other):
    parsed = urlparse(url)
    parsed_other = urlparse(other)

    # not comparable if they have diff domains or paths
    if parsed.netloc.lower() != parsed_other.netloc.lower():
        return False
    if parsed.path != parsed_other.path:
        return False

    # parses query parameters as dictionaries
    query_a = parse_qs(parsed.query, keep_blank_values=True)
    query_b = parse_qs(parsed_other.query, keep_blank_values=True)

    # identical queries not needed
    if query_a == query_b:
        return False

    keys_a = set(query_a)
    keys_b = set(query_b)

    # same amt of parameters but only 1 of them is different
    if len(keys_a) == len(keys_b):
        diff_keys = [k for k in keys_a if query_a.get(k) != query_b.get(k)]

        # trap detection
        # if only one of the parameters are different
        # check if it's just a number change/difference
        if len(diff_keys) == 1:
            k = diff_keys[0]

            val_a = query_a.get(k, [""])[0]
            val_b = query_b.get(k, [""])[0]

            # if values are both numbers, treat as trap 
            # # infinite loop
            if val_a.isdigit() and val_b.isdigit():
                return True

            # If not, let it pass b/c it's valid unique page (for ex. text)
            return False

    # # extra or missing parameter
    # if abs(len(keys_a) - len(keys_b)) == 1:
    #     common_keys = keys_a & keys_b
    #     if all(query_a[k] == query_b[k] for k in common_keys):
    #         return True

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

        # Strict domain filter to certain UCI domains
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

        # Disallow paths from robots.txt
        if path.startswith("/people") or path.startswith("/happening"):
            return False

        # Filter unwanted file types (not html)
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
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

        if url.count("-") > 10:
            return False

        # Query trap control
        # if they have same page but with small differences
        if any(is_same_except_one_query_param(url, prev) for prev in recent_links):
            recent_links.append(url)
            return False

        # tracks recent URLs to be used to compare
        recent_links.append(url)

        # trap detection
        # if there are too many query parameters
        if url.count("=") > 2:
            return False

        return True

    # need to handle bad URLs that can't parse
    except TypeError:
        print("TypeError for", url)
        raise

# Prints out the crawl stats when program exits
def print_results():
    print("\n=== RESULTS ===")
    print("Unique pages:", len(visited_urls))
    print("Longest page:", longest_page)
    print("Top 50 words:", word_counts.most_common(50))
    print("Subdomains:", subdomains)

atexit.register(print_results)