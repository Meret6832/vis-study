import bibtexparser
import pandas as pd


def get_title(conf: str, doi: str) -> str:
    with open(f"../data-collection/bibs/{conf}.bib", "r") as f:
        bibs = bibtexparser.loads(f.read())

    for ent in bibs.entries:
        ent_doi = ent["doi"].replace("\_", "_")
        if ent_doi == doi:
            return ent["title"].replace("{", "").replace("}", "")

    raise Exception(conf, doi)


classify_df = pd.read_csv("../classify-figures/classifications/try3.csv", index_col=0)
properties_df = pd.read_csv("../figure-properties-extraction/img_properties_small.csv", index_col=0)
mention_df = pd.read_csv("../mention-extraction/figures_mentions.csv", index_col=0)

df = pd.merge(classify_df, properties_df, on=["conf", "doi", "fig_num"])

# Fill title and url columns
df["title"] = df.apply(lambda row: get_title(row.conf, row.doi), axis=1)
df["url"] = df.apply(lambda row: "https://doi.org/" + row.doi, axis=1)

# Reorder columns
df = df.loc[:, ["doi", "conf", "title", "url", "fig_num",
                "status", "category", "subcategory", "subsubcategory", "dimensionality", "multiplicity", "n_panels",
                "width", "height", "colors", "visual_density"]]

df.to_csv("vis_dataset.csv", index=False)
