import os
import random
import requests
import sys
import time
from bs4 import BeautifulSoup


def get_papers(url: str, track: str, tries: int = 0) -> list[str] | None:
    res = requests.get(url)
    if not res.ok:
        if tries < 10:
            sleep_sec = random.randint(5, 60*5)
            print(f"{conf_id}: Sleeping for {sleep_sec} seconds")
            time.sleep(sleep_sec)
            return get_papers(url, track, tries+1)
        else:
            print(f"{conf_id}: ERROR: could not retrieve {url}, {res.status_code}, {res.text}, {res.headers}")
            return None

    with open("test.html", "w+") as f:
        f.write(res.text)

    soup = BeautifulSoup(res.text, features="html.parser")
    a_elems = soup.find_all("a", attrs={"href": "#", "data-event-modal": True})
    if a_elems is None:
        print(f"{conf_id}: ERROR: could not find papers for {url}")
        return None

    titles = set()
    for elem in a_elems:
        track_div = elem.find_next("div", attrs={"class": "prog-track"})
        if track_div.text == track:
            titles.add(elem.next_element.strip().strip(".").lower())

    return sorted(list(titles))


if __name__ == "__main__":
    dblp_conference_url = sys.argv[1]
    conf_research_url = sys.argv[2]
    if len(sys.argv) > 2:
        conf_research_track = sys.argv[3]
    else:
        conf_research_track = "Research Track"

    if dblp_conference_url == "https://dblp.org/db/journals/pacmse/pacmse1.html#nrFSE":
        conf_id = "pacmse/pacmse1"
        file_conf_id = "fse-fse2024"
    else:
        conf_id = dblp_conference_url.split("/conf/")[1].removesuffix(".html")
        file_conf_id = conf_id.replace("/", "-")

    # Get list of allowed titles
    print(f"{conf_id}: Getting list of allowed titles from {conf_research_url} with track={conf_research_track}")
    titles = get_papers(conf_research_url, conf_research_track)
    if titles is None:
        print(f"{conf_id}: ERROR: could not get list of allowed titles from {dblp_conference_url}")
        exit()

    print(f"{conf_id}: Got list of {len(titles)} papers from {conf_research_url}, writing to file...")
    if not os.path.exists("./paper-lists-automatic"):
        os.mkdir("./paper-lists-automatic")
    with open(f"./paper-lists-automatic/{file_conf_id}.txt", "w+") as f:
        f.write("\n".join(titles))
