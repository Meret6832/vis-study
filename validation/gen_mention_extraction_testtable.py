import pandas as pd

SAMPLESIZE = 100

df = pd.read_csv("../mention-extraction/figures_mentions.csv")
selected = df.sample(SAMPLESIZE)

testtable_str = "pdf_path,fig_num,mention_page,mention_heading,correct_page,correct_heading\n"
for (_, conf, doi, fig_num, _, mention_page, mention_heading, _, _) in selected.values:
    pdf_path = f"data-collection/pdfs-cleanup/{conf}/{doi.replace('/', '-').replace('.', '_')}.pdf"
    if pd.notna(mention_heading):
        mention_heading = f'"{mention_heading}"'
    testtable_str += f"{pdf_path},{fig_num},{mention_page},{mention_heading},,\n"

with open("mention_extraction_testtable.csv", "w+") as f:
    f.write(testtable_str)
