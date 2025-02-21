import pandas as pd

SAMPLE_SIZE = 215

df = pd.read_csv("../classify-figures/classifications/try3.csv")

sample_df = df[df["status"] == "SUCCESS"].sample(SAMPLE_SIZE)

sample_df["path"] = sample_df.apply(lambda row: f"../figure-extraction/extracted/{row.conf}/figures/{row.doi.replace('/', '-').replace('.', '_')}-Figure{row.fig_num}-1.png", axis=1)

sample_df.filter(["path", "type", "category", "subcategory", "subsubcategory", "dimensionality", "multiplicity", "n_panels"]).to_csv("classification_testtable.csv", index=False)
