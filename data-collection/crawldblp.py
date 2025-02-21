import json
import os
import re
import requests
import sys
import time
import xml.etree.ElementTree as ET


def call_api(url: str, tries: int = 0) -> str | None:
    print(f"{conf_id}: retrieving {url}, {len(titles)} titles left")

    try:
        res = requests.get(url)
    except Exception as e:
        print("ERROR:", e)
        if tries < 3:
            return call_api(url, tries+1)
        else:
            return None

    if res.status_code == 429:
        try:
            sleep_sec = int(json.loads(res.headers["Retry-After"]))
            print(f"{conf_id}: Sleeping for {sleep_sec} seconds")
            time.sleep(sleep_sec)
            return call_api(url, tries+1)
        except Exception as e:
            print("ERROR:", e)
            if tries < 3:
                return call_api(url, tries+1)
            else:
                return None
    elif not res.ok:
        print(f"{conf_id}: ERROR: could not retrieve {url}")
        return None

    return res.text


if __name__ == "__main__":
    dblp_conference_url = sys.argv[1]
    if dblp_conference_url == "https://dblp.org/db/journals/pacmse/pacmse1.html#nrFSE":
        conf_id = "pacmse/pacmse1"
        file_conf_id = "fse-fse2024"
        api_url = f"https://dblp.org/search/publ/api?q=toc%3Adb/journals/{conf_id}.bht%3A&h=1000&format=xml"
    else:
        conf_id = dblp_conference_url.split("/conf/")[1].removesuffix(".html")
        file_conf_id = conf_id.replace("/", "-")
        api_url = f"https://dblp.org/search/publ/api?q=toc%3Adb/conf/{conf_id}.bht%3A&h=1000&format=xml"

    with open(f"./paper-lists/{file_conf_id}.txt", "r") as f:
        titles = f.read().strip().split("\n")
        titles = [re.sub(r"[^a-zA-Z0-9]", "", title).lower() for title in titles]

    # Get dblp conference page
    res = call_api(api_url)
    if res is None:
        print(f"{conf_id}: Could not access conference url via API: {api_url}")
        exit()

    # Extract bibtex citations for selected titles
    bibtex = ""
    conf_elem = ET.fromstring(res)
    hits = conf_elem.find("hits")
    for child in hits:
        if len(titles) == 0:
            break
        info = child.find("info")
        title = re.sub(r"[^a-zA-Z0-9]", "", info.find("title").text).lower()
        if title in titles:
            doi = info.find("doi")
            doi_url = f"https://dblp.org/doi/{doi.text}.bib"
            doi_res = call_api(doi_url)
            if doi_res is not None:
                bibtex += doi_res
                titles.remove(title)

    if len(titles) > 0:
        missing_str = f"{conf_id}: Could not find {len(titles)} titles:\n"
        for title in titles:
            missing_str += f"{conf_id} MISSING: {title}\n"
    else:
        missing_str = "Found all (NO MISSING)\n"

    if not os.path.exists("missing-bibs"):
        os.mkdir("missing-bibs")
    with open(f"missing-bibs/{file_conf_id}.txt", "w+") as f:
        f.write(missing_str)

    if not os.path.exists("bibs-automatic"):
        os.mkdir("bibs-automatic")
    with open("bibs-automatic/" + file_conf_id + ".bib", "w+") as f:
        f.write(bibtex)
