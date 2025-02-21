import re
import json
import os
import pandas as pd
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


def add_row_to_df(
    conf, doi, num, status, chart_type, category, subcategory, subsubcategory,
    dimensionality, multiplicity, n_panels, first, replace
) -> bool:
    global df
    new_row = [conf, doi, num, status, chart_type, category, subcategory, subsubcategory, dimensionality, multiplicity, n_panels]

    if status == "SUCCESS":
        drop_idxs = df[(df["conf"] == conf) & (df["doi"] == doi) & (df["fig_num"] == num)].index
        df.drop(drop_idxs, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.loc[len(df)] = new_row
    # Keep row(s) with the least "INVALID"/None entries
    elif status == "INVALID":
        if not first:
            if replace:
                df.loc[len(df)] = new_row
                return replace
            else:
                return replace

        existing_idxs = df[(df["conf"] == conf) & (df["doi"] == doi) & (df["fig_num"] == num)].index
        other_invalids = 0
        for i in existing_idxs:
            if df.loc[i].status == "SUCCESS":  # Do not replace
                return False
            if df.loc[i].status == "FAILED":  # Replace
                df.drop(existing_idxs, inplace=True)
                df.reset_index(drop=True, inplace=True)
                df.loc[len(df)] = new_row
                return True
            other_invalids += len([v for v in df.loc[i] if v is None or v == "INVALID"])
        other_invalids_avg = other_invalids / len(existing_idxs)
        num_invalids = len([v for v in new_row if v is None or v == "INVALID"])
        print(num_invalids, other_invalids_avg)
        if num_invalids < other_invalids_avg:
            print(f"replacing, {num_invalids} < {other_invalids_avg}")
            df.drop(existing_idxs, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.loc[len(df)] = new_row
            return True

    return False  # FAILED


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
    file_name: str, status: str, first: bool, replace: bool | None = None, classification_parts: list[str] = []
) -> int:
    name_match = re.search("figure-extraction/extracted/(.+)/figures/(10_.*)-Figure([0-9]+)-1.png", file_name)
    conf = name_match[1]
    doi = name_match[2].replace("__", ".").replace("--", "/")
    num = int(name_match[3])

    if len(classification_parts) != 7:
        return False

    chart_type, category, subcategory, subsubcategory, dimensionality, multiplicity, n_panels = parts

    chart_type = parse_chart_type(chart_type)
    if chart_type == "INVALID":
        status = "INVALID"
    if chart_type != "D":
        add_row_to_df(conf, doi, num, status, chart_type, None, None, None, None, None, None, first, replace)
        return False

    category, subcategory, subsubcategory = parse_categories(category, subcategory, subsubcategory)
    if category == "INVALID" or subcategory == "INVALID" or subsubcategory == "INVALID":
        status = "INVALID"

    grouped_terms = ["Grouped", "Stacked", "Overlapped"]
    if subsubcategory is not None:
        for gt in grouped_terms:
            if gt in subsubcategory:
                multiplicity = "Grouped"
                break

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

    return add_row_to_df(conf, doi, num, status, chart_type, category, subcategory, subsubcategory, dimensionality, multiplicity, n_panels, first, replace)


def fill_multipanel(row) -> None:
    """For (doi, fig_num) combinations that only have one Multipanel entry, duplicate the entry n_panels times."""
    global df

    if row.multiplicity != "Multipanel" or row.n_panels is None or row.n_panels == "INVALID" or int(row.n_panels) < 2:
        return
    match_rows = df[(df["doi"] == row.doi) & (df["fig_num"] == row.fig_num)]
    if len(match_rows) > 1:
        return

    for _ in range(int(row.n_panels)-1):
        df = pd.concat([df, match_rows.iloc[[0]]], ignore_index=True)


if __name__ == "__main__":
    try_num = int(sys.argv[1])
    in_dir = f"outputs/try{try_num}"
    in_csv = f"classifications/try{try_num-1}.csv"
    out_csv = f"classifications/try{try_num}.csv"

    with open("taxonomy.json") as f:
        taxonomy = json.load(f)

    taxonomy_reverse_subsub = {}
    taxonomy_reverse_sub = {}
    for cat in taxonomy:
        for subcat in taxonomy[cat]:
            taxonomy_reverse_sub[subcat] = cat
            for subsubcat in taxonomy[cat][subcat]:
                taxonomy_reverse_subsub[subsubcat] = [cat, subcat]

    df = pd.read_csv(in_csv, index_col=0)
    print("total:", len(df))
    df["fig_num"] = df["fig_num"].apply(lambda n: int(n))

    total_count = 0
    failed_count = 0
    failed_num = 0
    for file in os.listdir(in_dir):
        total_count += 1
        with open(f"{in_dir}/{file}", "r") as f:
            d = json.load(f)

        img_files = d["img_files"]
        classification_str = re.search(r"[0-9]+\.s*(?:.|\n)*[^\"`']", d["classification"])
        if classification_str is None:  # Classification failed
            failed_count += 1
            for img_file in img_files:
                add_to_df(img_file, "FAILED", True)
            continue

        classifications_strs = re.findall(r"[0-9]+\.\s*.*[^\"`']", classification_str[0])
        classifications = [(int(c.split(".")[0])-1, "".join(c.split(".")[1:]).strip()) for c in classifications_strs]
        classifications = [c for c in classifications if c[0] < 30]
        if len(classifications) > len(img_files):
            failed_num += 1
            print("classification number failed", file, len(classifications))
            for img_file in img_files:
                add_to_df(img_file, "FAILED", True)
            continue

        if not ([c[0] for c in classifications] == list(range(len(classifications)))):
            print("numbering failed", file, [c[0] for c in classifications])
            for img_file in img_files:
                add_to_df(img_file, "FAILED", True)
            continue

        first = True
        replace = None
        for n, c_strs in classifications:
            for c_str in c_strs.split("\\n"):
                c_str = c_str.strip()
                if c_str == "":
                    continue
                parts = [p.strip() for p in c_str.split(",")]
                if len(parts) != 7:
                    print("parts number failed:", len(parts), img_files[n])
                    add_to_df(img_files[n], "FAILED", first)
                    first = False
                    replace = False
                    continue

                # print(parse_match)
                replace = add_to_df(img_files[n], "SUCCESS", first, replace, parts)
                first = False

    print(f"{failed_count} failed out of {total_count}")
    print(f"{failed_num} num failed out of {total_count}")

    total_failed = len(df[df["status"] == "FAILED"])
    total_invalid = len(df[df["status"] == "INVALID"])
    total_not_success = len(df[df["status"] != "SUCCESS"])
    print(f"total: {len(df)}, total failed: {total_not_success}, failed: {total_failed}, invalid: {total_invalid}")

    missing = 0
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
            fig_num = int(path_match[2])
            df_match = df[(df["conf"] == conf) & (df["doi"] == doi) & (df["fig_num"] == fig_num)]
            if len(df_match) == 0:
                missing += 1

    print("Missing:", missing)

    # Duplicate multipanels
    df.apply(lambda row: fill_multipanel(row), axis=1)

    print("writing to", out_csv)
    df.to_csv(out_csv)
