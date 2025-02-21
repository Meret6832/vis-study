import re
import json
import os
import pandas as pd

OUT_DIR = "outputs/try1"


def parse_chart_type(chart_type_raw: str) -> str:
    chart_type = chart_type_raw.strip()
    if chart_type == "":
        return chart_type

    if chart_type not in ["D", "P", "T"]:
        if chart_type == "Diagram":
            chart_type = "D"
        else:
            print("could not parse chart type", chart_type_raw, end=" ")
            chart_type = "INVALID"

    return chart_type


def parse_categories(category: str, subcategory: str, subsubcategory: str) -> tuple[str | None, str | None, str | None]:
    if category == "" and subcategory == "" and subsubcategory == "":
        return (None, None, None)

    if subsubcategory in taxonomy_reverse_subsub:
        category, subcategory = taxonomy_reverse_subsub[subsubcategory]
    else:
        if subsubcategory == "":
            subsubcategory = None
        else:
            subsubcategory = "INVALID"

        if subcategory in taxonomy_reverse_sub:
            category = taxonomy_reverse_sub[subcategory]
        else:
            if subcategory == "":
                subcategory = None
            else:
                subcategory = "INVALID"

            if category == "":
                category = None
            elif category not in taxonomy:
                category = "INVALID"

    return (category, subcategory, subsubcategory)


def add_to_df(
    file_name: str, status: str, classification_parts: list[str] = []
) -> None:
    name_match = re.search("figure-extraction/extracted/(.+)/figures/(10_.*)-Figure([0-9]+)-1.png", file_name)
    conf = name_match[1]
    doi = name_match[2].replace("__", ".").replace("--", "/")
    num = name_match[3]

    if len(classification_parts) != 7:
        df.loc[len(df)] = [conf, doi, num, status, None, None, None, None, None, None, None]
        return

    chart_type, category, subcategory, subsubcategory, dimensionality, multiplicity, n_panels = parts

    chart_type = parse_chart_type(chart_type)
    if chart_type == "INVALID":
        status = "INVALID"
    if chart_type != "D":
        df.loc[len(df)] = [conf, doi, num, status, chart_type, None, None, None, None, None, None]
        return

    category, subcategory, subsubcategory = parse_categories(category, subcategory, subsubcategory)
    if category == "INVALID" or subcategory == "INVALID" or subsubcategory == "INVALID":
        status = "INVALID"

    try:
        dimensionality = int(dimensionality)
    except ValueError:
        if dimensionality == "":
            dimensionality = None
        else:
            dimensionality = "INVALID"
            status = "INVALID"

    if multiplicity == "":
        multiplicity = None
    elif multiplicity not in ["Single", "Combination", "Grouped", "Multipanel"]:
        multiplicity = "INVALID"
        status = "INVALID"

    try:
        n_panels = int(n_panels)
    except ValueError:
        if n_panels == "":
            n_panels = None
        else:
            n_panels = "INVALID"
            status = "INVALID"

    df.loc[len(df)] = [conf, doi, num, status, chart_type, category, subcategory, subsubcategory, dimensionality, multiplicity, n_panels]


if __name__ == "__main__":
    with open("taxonomy.json") as f:
        taxonomy = json.load(f)

    taxonomy_reverse_subsub = {}
    taxonomy_reverse_sub = {}
    for cat in taxonomy:
        for subcat in taxonomy[cat]:
            taxonomy_reverse_sub[subcat] = cat
            for subsubcat in taxonomy[cat][subcat]:
                taxonomy_reverse_subsub[subsubcat] = [cat, subcat]

    df = pd.DataFrame(columns=["conf", "doi", "fig_num", "status", "type", "category", "subcategory", "subsubcategory", "dimensionality", "multiplicity", "n_panels"])

    total_count = 0
    failed_count = 0
    failed_num = 0

    for file in os.listdir(OUT_DIR):
        total_count += 1
        with open(f"{OUT_DIR}/{file}", "r") as f:
            d = json.load(f)

        img_files = d["img_files"]
        classification_str = re.search(r"[0-9]+\.s*(?:.|\n)*[^\"`']", d["classification"])
        if classification_str is None:  # Classification failed
            failed_count += 1
            for img_file in img_files:
                add_to_df(img_file, "FAILED")
            continue

        classifications_strs = re.findall(r"[0-9]+\.\s*.*[^\"`']", classification_str[0])
        classifications = [(int(c.split(".")[0]), "".join(c.split(".")[1:]).strip()) for c in classifications_strs]
        classifications = [c for c in classifications if c[0] < 30]
        if len(classifications) != len(img_files):
            failed_num += 1
            print("classification number failed", file, len(classifications))
            for img_file in img_files:
                add_to_df(img_file, "FAILED")
            continue

        for n, c_strs in classifications:
            for c_str in c_strs.split("\\n"):
                c_str = c_str.strip()
                if c_str == "":
                    continue
                parts = [p.strip() for p in c_str.split(",")]
                if len(parts) != 7:
                    add_to_df(img_files[n], "FAILED")
                    continue

                # print(parse_match)
                add_to_df(img_files[n], "SUCCESS", parts)

    # Check that all figures were actually done.
    for conf in os.listdir("../figure-extraction/extracted"):
        for fig_file in os.listdir(f"../figure-extraction/extracted/{conf}/figures"):
            if "Table" in fig_file:
                continue
            path_match = re.search(r"(10_.+\-.+)\-Figure([0-9]+)", fig_file)
            if path_match is None:
                print(fig_file)
                continue
            doi = path_match[1].replace("__", ".").replace("--", "/")
            fig_num = path_match[2]
            df_match = df[(df["conf"] == conf) & (df["doi"] == doi) & (df["fig_num"] == fig_num)]
            if len(df_match) == 0:
                df.loc[len(df)] = [conf, doi, fig_num, "INVALID", None, None, None, None, None, None, None]

    print(f"{failed_count} failed out of {total_count}")
    print(f"{failed_num} num failed out of {total_count}")


    total_failed = len(df[df["status"] == "FAILED"])
    total_invalid = len(df[df["status"] == "INVALID"])
    total_not_success = len(df[df["status"] != "SUCCESS"])
    print(f"total: {len(df)}, total failed: {total_not_success}, failed: {total_failed}, invalid: {total_invalid}")

    df.to_csv("classifications/try1.csv")
