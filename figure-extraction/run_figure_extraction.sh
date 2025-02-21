#!/bin/bash


# Extract figures
source ~/.profile
cd ../pdffigures2

avail_begin=$(df --output=avail -BG / | tail -n 1 | sed 's/[^0-9]//g')

for dir in ../data-collection/pdfs/*/; do
    #Get the available space in GB for the root partition
    avail_now=$(df --output=avail -BG / | tail -n 1 | sed 's/[^0-9]//g')

    # Check if the available space is below the threshold
    if [ "$avail_now" -lt "10" ]; then
        echo "Less than 10G available space left. Exiting loop."
        break
    fi
    echo "Available space: ${avail_now}G. Continuing loop."

    # Clean up PDFs
    for file in $dir/*; do
        mkdir -p ../data-collection/pdfs-cleanup/$(basename $dir)
        doi_pdf=$(basename $file)
        timeout 30 mutool clean $file ../data-collection/pdfs-cleanup/$(basename $dir)/$doi_pdf
        exit_status=$?
        if [[ $exit_status -eq 124 ]]; then
            echo "Could not clean up $(basename $dir) $doi_pdf"
            echo "PDF cleanup timed out"
            cd $file ../data-collection/pdfs-cleanup/$(basename $dir)/$doi_pdf
        fi
    done

    # Extract figures
    mkdir -p ../figure-extraction/extracted/$(basename "$dir")/figures;
    mkdir -p ../figure-extraction/extracted/$(basename "$dir")/data;
    sbt "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider"  "runMain org.allenai.pdffigures2.FigureExtractorBatchCli ../data-collection/pdfs-cleanup/$(basename $dir)/ -s ../figure-extraction/stat_file.json -m ../figure-extraction/extracted/$(basename "$dir")/figures/ -d ../figure-extraction/extracted/$(basename "$dir")/data/"
done

avail_now=$(df --output=avail -BG / | tail -n 1 | sed 's/[^0-9]//g')
echo "Consumed $((avail_begin - avail_now))G."

# Check if all PDFs could be successfully cleaned up.
> missing_pdf_analysis.txt

missing=0

for dir in ../data-extraction/pdfs/*/; do
    for file in $dir/*; do
        # Check if data file for pdf exists
        doi_pdf=$(basename $file)
        echo "$(basename $dir) ${doi_pdf/pdf/json}"
        if [ ! -f ./extracted/$(basename $dir)/data/"${doi_pdf/pdf/json}" ]; then
            echo "Missing $(basename $dir) ${doi_pdf/pdf/json}" >> missing_pdf_analysis.txt
            missing=$((missing + 1))
        fi
    done
done

echo "Found total $missing PDFs missing." >> missing_pdf_analysis.txt
