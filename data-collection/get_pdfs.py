import bibtexparser
import os
import random
import requests
import sys
import time

PDFS_DIR = "pdfs-automatic"

ACM_PROXY = ""  # TODO: put your ACM proxy link here
IEEE_PROXY = ""  # TODO: put your IEEE proxy link here

# Get the following by visiting an IEEE pdf via your proxy e.g. https://<IEEE_PROXY>/stamp/stamp.jsp?tp=&arnumber=10628495 and copying them from your browser.
IEEE_HEADERS = {}  # TODO: put headers here.
PROXY_COOKIES = {}  # TODO: put cookies here.

DOI_HEADERS = {"Host": "doi.org", "User-Agent": "curl/7.81.0", "Accept": "*/*"}


def get_acm(doi: str, tries: int = 0):
    s = requests.Session()
    for n, v in PROXY_COOKIES.items():
        s.cookies.set(name=n, value=v)

    url = f"https://{ACM_PROXY}/doi/pdf/{doi}"
    print(f"getting {url}")

    res = s.get(url)
    if not res.ok or "html" in str(res.text).strip().split("\n")[0]:
        print(f"got {res}: {str(res.text)}")
        if res.status_code == 404:  # NOt Found
            return None

        if tries < 5:
            sec = random.randint(5, 60*30)  # Between 5 seconds and 30 minutes
            print(f"sleeping for {sec/60} minutes ({sec} seconds)")
            time.sleep(sec)
            return get_acm(url, tries+1)
        else:
            return None
    else:
        return res


def get_ieee(url: str, tries: int = 0):
    s = requests.Session()

    print(f"getting {url}")

    try:
        redirect_res = s.get(url, headers=DOI_HEADERS, allow_redirects=False)
    except requests.exceptions.ConnectionError as e:
        print(e)
        return get_ieee(url, tries+1)

    if not redirect_res.status_code == 302:
        if tries < 5:
            sec = random.randint(5, 60*30)  # Between 5 seconds and 30 minutes
            print(f"sleeping for {sec/60} minutes ({sec} seconds)")
            time.sleep(sec)
            return get_ieee(url, tries+1)
        else:
            return None
    if redirect_res.headers.get("Location") is None:
        print(f"did not get redirects for {redirect_res}")
        return None

    for n, v in PROXY_COOKIES.items():
        s.cookies.set(name=n, value=v)

    ieee_num = redirect_res.headers["Location"].strip("/").split("/")[-1]
    ieee_url = f"https://{IEEE_PROXY}/stampPDF/getPDF.jsp?tp=&arnumber={ieee_num}"
    print(f"getting {ieee_url}")
    ieee_res = s.get(ieee_url, headers=IEEE_HEADERS)
    if not ieee_res.ok:
        print(ieee_res, ieee_res.text[:100])
        if tries < 5:
            sec = random.randint(5, 60*30)  # Between 5 seconds and 30 minutes
            print(f"sleeping for {sec/60} minutes ({sec} seconds)")
            time.sleep(sec)
            return get_ieee(url, tries+1)
        else:
            return None
    else:
        return ieee_res


if __name__ == "__main__":
    if not os.path.exists(PDFS_DIR):
        os.mkdir(PDFS_DIR)

    conf_id = sys.argv[1]
    with open(f"bibs-manual/{conf_id}.bib", "r") as f:
        bibs = bibtexparser.loads(f.read())

    for ent in bibs.entries:
        doi = ent["doi"].replace("\_", "_")

        file_doi = doi.replace("/", "--").replace(".", "__")
        path = f"{PDFS_DIR}/{conf_id}/"
        file_path = f"{path}{file_doi}.pdf"
        # Do not overwrite PDFs that already exist
        if os.path.exists(file_path):
            print(f"skipping {doi}, already has pdf")
            continue

        publisher = ent.get("publisher", "ACM").strip("\{\}")
        if publisher == "ACM":
            res = get_acm(doi)
        elif publisher == "IEEE":
            res = get_ieee(ent["url"])
        else:
            print(f"cannot do publisher {publisher} for {doi}")
            with open(f"{PDFS_DIR}/missed.txt", "a+") as f:
                f.write(f"{conf_id},{doi},PUBLISHER\n")
            continue

        if res is None:
            with open(f"{PDFS_DIR}/missed.txt", "a+") as f:
                f.write(f"{conf_id},{doi},PDF\n")
        else:
            if not os.path.exists(path):
                os.mkdir(path)
            with open(file_path, "wb+") as f:
                f.write(res.content)
