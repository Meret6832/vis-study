import json
import os
import pandas as pd
import pymupdf
import re
from operator import itemgetter


# --- IDENTIFY HEADINGS --- source: https://github.com/EthanJWright/pdfparse/blob/main/parse.py (slightly modified)
def fonts(doc, granularity=False):
    """Extracts fonts and their usage in PDF documents.
    :param doc: PDF document to iterate through
    :type doc: <class 'pymupdf.pymupdf.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    styles = {}
    font_counts = {}

    for page in doc:
        rect = page.rect
        height = 75
        clip_top = pymupdf.Rect(0, height, rect.width, rect.height)
        blocks = page.get_text("dict", clip=clip_top)["blocks"]  # get all text blocks
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if granularity:
                            identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                            styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                                  'color': s['color']}  # store style information
                        else:
                            identifier = "{0}".format(s['size'])  # store font size
                            styles[identifier] = {'size': s['size'], 'font': s['font']}  # store style information

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1   # count the fonts usage

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)  # sort by count

    if len(font_counts) < 1:  # no fonts found
        raise ValueError("Zero discriminating fonts found!")  # check if there are any discriminating fonts

    return font_counts, styles


def font_tags(font_counts, styles):
    """Returns dictionary with font sizes as keys and tags as value.
    :param font_counts: (font_size, count) for all fonts occuring in document
    :type font_counts: list
    :param styles: all styles found in the document
    :type styles: dict
    :rtype: dict
    :return: all element tags based on font-sizes
    """
    p_style = styles[font_counts[0][0]]  # get style for most used font by count (paragraph)
    p_size = p_style['size']  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag
    font_sizes = []
    for (font_size, _) in font_counts:  # iterate through the font counts
        font_sizes.append(float(font_size))  # append font size to list
    font_sizes.sort(reverse=True)  # sort the list in descending order

    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:  # iterate through the font sizes
        idx += 1
        if size == p_size:  # if the font size is the same as the paragraph's size
            idx = 0  # reset the index
            size_tag[size] = '<p>'  # append paragraph tag
        if size > p_size:  # if the font size is bigger than the paragraph's size
            size_tag[size] = '<h{0}>'.format(idx)  # append header tag
        elif size < p_size:  # if the font size is smaller than the paragraph's size
            size_tag[size] = '<s{0}>'.format(idx)  # append subheader tag

    return size_tag  # return header_para


def headers_para(doc, size_tag):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :type size_tag: dict
    :rtype: list
    :return: texts with pre-prended element tags
    """
    header_para = []  # list with headers and paragraphs
    first = True  # boolean operator for first header
    previous_s = {}  # previous span

    for page in doc:
        rect = page.rect
        height = 75
        clip_top = pymupdf.Rect(0, height, rect.width, rect.height)
        blocks = page.get_text("dict", clip=clip_top)["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # this block contains text

                # REMEMBER: multiple fonts and sizes are possible IN one block

                block_string = ""  # text found in block
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        # if the last two characters in bockstring are spaces,
                        # remove one
                        if s['text'].strip():  # removing whitespaces:
                            if first:
                                previous_s = s
                                first = False
                                block_string = size_tag[s['size']] + s['text']
                            else:
                                if s['size'] == previous_s['size']:

                                    if block_string and all((c == "|") for c in block_string):
                                        # block_string only contains pipes
                                        block_string = size_tag[s['size']] + s['text']
                                    if block_string == "":
                                        # new block has started, so append size tag
                                        block_string = size_tag[s['size']] + s['text']
                                    else:  # in the same block, so concatenate strings
                                        block_string += " " + s['text']

                                else:
                                    header_para.append(block_string)
                                    block_string = size_tag[s['size']] + s['text']

                                previous_s = s

                    # new block started, indicating with a pipe
                    # block_string += "|"

                # remove any double spaces
                block_string = block_string.replace("  ", " ")
                # only append if block_string is not empty
                if block_string:
                    header_para.append(block_string)

    max_header_depth = 5
    header_para_cleaned = []
    cur_elem = ""
    for elem in header_para:
        if elem.startswith("<h"):
            header_num_match = re.match(r"<h([0-9]+)>", elem)
            try:
                header_num = int(header_num_match[1])
            except ValueError or IndexError:
                print("skipping", elem[:50])
                continue

            if header_num <= max_header_depth:
                if cur_elem != "":
                    header_para_cleaned.append(cur_elem.strip())
                    cur_elem = ""
                header_para_cleaned.append(elem.strip())

                continue

        cur_elem += re.sub(r"<[a-z][0-9]*>", " ", elem)

    if cur_elem != "":
        header_para_cleaned.append(re.sub(r"<[a-z][0-9]*>", "", cur_elem))

    return header_para_cleaned


# --- IDENTIFY HEADING OF FIRST FIGURE REFERENCE ----


def get_mention_heading(pdf_path: str, fig_num: str, caption: str) -> tuple[int, str | None] | None:
    """
    Returns index of page of first figure mention, and the most high-level heading the mention was under.
    """
    doc = pymupdf.open(pdf_path)

    # Remove figure X from caption, remove non-letters/numbers and make lower.
    caption = re.sub(r"f\s*i\s*g\s*(u\s*r\s*e)?s?[^a-zA-Z0-9]*[0-9]+", "", caption, flags=re.IGNORECASE)
    caption = re.sub(r"[^a-zA-Z0-9]", "", caption).lower()

    # Check for first mention
    mention_page_num = None
    mention = None
    backup_page_num = None
    backup = None
    for page in doc:
        if page.number == 0:
            continue
        rect = page.rect
        height = 75
        clip_top = pymupdf.Rect(0, height, rect.width, rect.height)
        page_text = page.get_text(clip=clip_top)
        res = re.finditer(f"(f\s*i\s*g\s*(u\s*r\s*e)?s?[^a-zA-Z0-9]*{fig_num})[^0-9]+", page_text, flags=re.IGNORECASE)
        if res is None:
            continue
        for x in res:
            raw_x = re.sub(r"f\s*i\s*g\s*(u\s*r\s*e)?s?[^a-zA-Z0-9]*[0-9]+", "", x[0], flags=re.IGNORECASE)
            raw_x = re.sub(r"[^a-zA-Z0-9]", "", raw_x).lower()
            if caption in raw_x and backup_page_num is None:  # Assume that Caption was found
                print(f"Fig {fig_num} found caption on page", page.number)
                backup_page_num = page.number
                backup = x[0]
            else:
                print(f"Fig {fig_num} found mention on page {page.number}: {x[1][:50]}")
                mention_page_num = page.number
                mention = x[1]
                break
        if mention_page_num is not None:
            break

    # No mention found, but something that was possibly the caption, so take that.
    if mention_page_num is None and backup_page_num is not None:
        print(f"Fig {fig_num} did not find mention, using caption as backup")
        mention_page_num = backup_page_num
        mention = backup

    # No mention could be found, return None
    if mention_page_num is None:
        return None

    font_counts, font_styles = fonts(doc, granularity=False)
    size_tag = font_tags(font_counts, font_styles)
    raw_mention = re.sub(r"[^a-zA-Z0-9]", "", mention).lower()
    headings = []
    next_heading = None
    for page_num in range(mention_page_num, -1, -1):
        elems = headers_para([doc[page_num]], size_tag)

        if page_num == mention_page_num:
            mention_i = None
            for i in range(len(elems)):
                raw_elem = re.sub(r"[^a-zA-Z0-9]", "", elems[i]).lower()
                if raw_mention in raw_elem:
                    mention_i = i
                    break
            if mention_i is None:
                return (mention_page_num, None)
            elems = elems[:mention_i]

        for elem in reversed(elems):
            h_num_re = r"((?:[0-9]+(?:\.[0-9]+)*)|(?:[IVXLCDM]+\.)|(?:[A-Z]+\.))"  # e.g. 3, IV., B.
            heading_match = re.match(f"<h([0-9]+)>\s*({h_num_re}.*)", elem)  # Heading must start with a number/I/captial letter.
            if heading_match is not None:
                depth = int(heading_match[1])
                if depth == 1:  # Skip the title
                    continue
                h_text = heading_match[2]
                h_text_split = [p for p in re.split(f"{h_num_re}\s+", h_text) if p is not None and p.strip() != ""]
                if len(h_text_split) > 2:
                    sub_headings = [" ".join(h_text_split[i:i+2]) for i in range(0, len(h_text_split) - (len(h_text_split) % 2), 2)]
                else:
                    sub_headings = [h_text]

                for heading in sub_headings:
                    h_num_match = re.match(f"{h_num_re}\s*", heading)
                    if h_num_match is None:
                        continue
                    h_num = h_num_match[1].strip(".")
                    try:
                        h_num_int = int(h_num)
                        if h_num_int > 50:  # Not realistic
                            continue
                    except ValueError:
                        pass

                    if len(headings) == 0 or headings[-1][0] > depth:
                        headings.append([depth, heading])

                        if len(h_num.split(".")) > 1:
                            next_heading = ".".join(h_num.split(".")[:-1])
                        else:
                            h_num = None
                    elif headings[-1][0] == depth:  # For headings, assume e.g. 3.3.5 OR e.g. II -> C -> 5
                        if re.match(r"[IVXLCDM]+", h_num) and re.match(r"[IVXLCDM]+", headings[-1][1]) is None:  # II heading (top level)
                            headings.append([depth, heading])
                        elif re.match(r"[A-Z]+", h_num) and re.match(r"[IVXLCDM]|[A-Z]+", headings[-1][1]) is None:  # Letter heading (second level)
                            headings.append([depth, heading])
                        elif next_heading is not None and h_num == next_heading:  # Numerical heading
                            headings.append([depth, heading])
                            if len(h_num.split(".")) > 1:
                                next_heading = ".".join(h_num.split(".")[:-1])
                            else:
                                h_num = None

    headings_filtered = [h for h in headings if " ".join(h[1].split()[1:]).strip() != ""]
    if len(headings_filtered) == 0:
        return (mention_page_num, None)

    top_level_heading = sorted(headings_filtered, key=lambda h: (h[0], len(h[1].split()[0].split("."))))[0][1].strip()  # First sort according to h_depth, then level of h_num
    if len(top_level_heading) == 0:
        top_level_heading = None

    return (mention_page_num, top_level_heading)


def get_total_pages(conf: str, doi: str) -> int:
    pdf_path = f"../data-collection/pdfs-cleanup/{conf}/{doi.replace('.', '_').replace('/', '-')}.pdf"
    doc = pymupdf.open(pdf_path)
    return len(list(doc.pages()))


if __name__ == "__main__":
    with open("get_mentions.log", "w+") as f:
        f.write("")

    df = pd.DataFrame(columns=["conf", "doi", "fig_num", "fig_page", "mention_page", "mention_heading", "mention_heading_txt", "path"])

    for conf in os.listdir("../figure-extraction/extracted/"):
        for data_file in os.listdir(f"../figure-extraction/extracted/{conf}/data/"):
            doi = data_file.split(".")[0]

            with open(f"../figure-extraction/extracted/{conf}/data/{data_file}", "r") as f:
                data_dict = json.load(f)

            total_pages = get_total_pages(conf, doi)
            for elem in data_dict:
                try:
                    if elem["figType"] != "Figure":  # Skip Tables etc.
                        continue

                    mention_page = None
                    mention_heading = None
                    mention_heading_cleaned = None
                    heading = get_mention_heading(f"../data-collection/pdfs-cleanup/{conf}/{doi}.pdf", elem["name"], elem["caption"])
                    if heading is not None:
                        mention_page, mention_heading = heading
                        if mention_heading is not None:
                            mention_heading_cleaned = re.sub(r"^((?:[0-9]+(?:\.[0-9]+)*)|(?:[IVXLCDM]+\.)|(?:[A-Z]+\.))[^a-zA-Z0-9]*", "", mention_heading).strip()
                            if mention_heading_cleaned == "":
                                mention_heading_cleaned = None
                    df.loc[len(df)] = [conf, doi.replace("__", ".").replace("--", "/"), elem["name"], elem["page"], mention_page, mention_heading, mention_heading_cleaned, elem["renderURL"], total_pages]

                except Exception as e:
                    with open("process_figures.log", "a+") as f:
                        f.write(e.__str__() + " " + json.dumps(elem) + "\n")
                    df.loc[len(df)] = [conf, doi.replace("__", ".").replace("--", "/"), elem["name"], elem["page"], "ERROR", "ERROR", "ERROR", elem["renderURL"], total_pages]

    df.to_csv("figures_mentions2.csv")
