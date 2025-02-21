The dataset containing the extracted figures and their properties can be found in [dataset/vis_dataset.csv](dataset/vis_dataset.csv). For this dataset, the small version ([img_properties_small.csv](figure-properties-extraction/img_properties_small.csv)) of the _img_properties_ dataset has been used only containing the 10 most ocurring colours in a figure.


To reproduce the results and analysis described in the papers, follow the following steps.

_Note: the folders containing the PDFs and Figures of the papers discussed here have been removed._

# A. Conference Selection
The conferences considered for the conference selection phase can be found in [conference_selection.csv](conference_selection.csv). If a researcher thought a conference was relevant, their column is marked with "x" for that conference's row.

# B. Data collection
The files for the data collection phase can be found in the [data-collection](data-collection) folder.

1. **Get research papers from conference site**: [gen_paper_lists.sh](data-collection/gen_paper_lists.sh), which calls [get_paper_lists.py](data-collection/get_paper_lists.py) for each conference except ISSRE, which does not have a _conf.researchr.org_ page. [get_paper_lists.py](data-collection/get_paper_lists.py) writes the titles of the research papers to a file for each respective conference in the [paper-lists-automatic](data-collection/paper-lists-automatic) folder.
2. **Manually create the paper list for ISSRE** (from [this page](https://issre.github.io/2024/program_research.html)) and add it to the [paper-lists](data-collection/paper-lists) folder along with the files from [paper-lists-automatic](data-collection/paper-lists-automatic).
2. **Get bibliographies of research papers from _dblp.org_**: [gen_bibs.sh](data-collection/gen_bibs.sh), which calls [crawldblp.py](data-collection/crawldblp.py) for all 17 conferences. [crawldblp.py](data-collection/crawldblp.py) saves the citation of a conference's papers to a file in the [bibs-automatic](data-collection/bibs-automatic) folder based on the conference's paper list from the [paper-lists](data-collection/paper-lists) folder. Sometimes, titles do not match across a conference's _conf.researchr.org_ and _dblp.org_ pages, those are saved to the conference's file in the [missing-bibs](data-collection/missing-bibs) folder.
3. **Manually check the missed titles** in the [missing-bibs](data-collection/missing-bibs) folder. If a missed title does have a matching entry on _dblp.org_, get its bibtex citation and add it to a copy of the conference's [bibs-automatic](data-collection/bibs-automatic) file in the [bibs](data-collection/bibs) folder. Also create a copy in the [bibs](data-collection/bibs) folder if all titles were found.
4. **Download PDFs**: [get_pdfs.sh](data-collection/get_pdfs.sh), which calls [get_pdfs.py](data-collection/get_pdfs.py) for each conference and requires IEEE and ACM proxys and for the headers and cookies of the logged-in proxies to be entered. PDFs are stored in the [pdfs-automatic](data-collection/pdfs-automatic) directory in their conference's folder. Whichever PDFs cannot be downloaded is recorded in [pdfs-automatic/missed.txt](data-collection/pdfs-automatic/missed.txt).
5. **Manually download** the PDFs that could not be downloaded automatically (as recorded in [pdfs-automatic/missed.txt](data-collection/pdfs-automatic/missed.txt)). Store the automatically and manually downloaded PDFs together in the [pdfs](data-collection/pdfs) directory.

## C. Figure extraction
The files for the figure extraction phase can be found in the [figure-extraction](figure-extraction) folder.

6. **Extract figures**: [run_figure_extraction.sh](figure-extraction/run_figure_extraction.sh), which uses a slightly modified version of [pdffigures2](https://github.com/allenai/pdffigures2). To do so, it cleans up the downloaded PDFs. These cleaned up PDFs are saved to [data-collection/pdfs-cleanup](data-collection/pdfs-cleanup). PDFs that are corrupted and could not be successfully cleaned up are recorded in [missing_pdf_analysis.tx](figure-extraction/missing_pdf_analysis.txt).
7. **Manually download the PDFs** in [missing_pdf_analysis.tx](figure-extraction/missing_pdf_analysis.txt) that were automatically downloaded in a corrupted state. Save these pdfs to the [data-collection/pdfs-missing-manual](data-collection/pdfs-missing-manual) directory in folders for their respective conferences.
8. **Extract figures from previously corrupted PDFs**: [run_figure_extraction_missing.sh](figure-extraction/run_figure_extraction_missing.sh).

The results of a small manual test of the figure extraction can be found in [validation/figure_extraction_testtable.csv](validation/figure_extraction_testtable.csv).


## D. Figure analysis
The files for the figure analysis phase are divided among three folders:

9. **Extract first mention of figure**: [mention-extraction/get_mentions.py](mention-extraction/get_mentions.py), writes the result to [mention-extraction/figures_mentions.csv](mention-extraction/figures_mentions.csv).
The results of a small manual test of the mention extraction can be found in [validation/mention_extraction_testtable.csv](validation/mention_extraction_testtable.csv).
10. **Classify figures**: to classify the figures, OpenAI's gpt-4o-2024-08-06 is used, which does not always produce usable outputs. Because of this, we ran three iterations of classification. The classification files can be found in the [classify-figures](classify-figures) folder.
    - [classify.sh](classify-figures/classify.sh), which carries out the following steps:
        1. First classification round: [classify.py](classify-figures/classify.py), the result of which is stored in [outputs/try1](classify-figures/outputs/try1). The resulting logs are not included here because they are too big.
        2. Extract classifications from first round: [extract_classifications.py](classify-figures/extract_classifications.py), the result of which is stored in [classifications/try1.csv](classify-figures/classifications/try1.csv).
        3. Second (and third) classification round:  [classify_failed](classify-figures/classify_failed.py), make sure to set the round number as argument (2 or 3). While the Figure's caption is included with the prompt to increase the classification accuracy for the first classification round, this is not done for the following roundds as the caption can trigger moderation.
        4. Extract classifications from second round (and third): [extract_classifications_failed.py](classify-figures/extract_classifications_failed.py), again with the round number as command line argument.
The results of a small manual test of the figure classificaton can be found in [validation/classification_testtable.csv](validation/classification_testtable.csv).
12. **Extract image properties**: [figure-properties-extraction/get_img_stats.py](figure-properties-extraction/get_img_stats.py), writes the results to _figure-properties-extraction/img_properties.csv_.
The resulting _img_properties.csv_ is too large for GitHub, which is why the smaller [img_properties_small.csv](figure-properties-extraction/img_properties_small.csv) has been compiled with [compress.py](figure-properties-extraction/compress.py) by only saving the 10 most occuring colours.

The calculations for the accuracy numbers for these extractions can be found in [validation/accuracy_stats.ipynb](validation/accuracy_stats.ipynb).

## E. Data Synthesis
The code for the data synthesis and to produce the visualisations in the paper, see [sythesize-data/exploratory.ipynb](sythesize-data/exploratory.ipynb).

## F Dataset
To produce the final dataset ([dataset/vis_dataset.csv](dataset/vis_dataset.csv)), run [dataset/gen_dataset.py](dataset/gen_dataset.py).
