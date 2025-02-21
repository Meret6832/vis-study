import base64
import json
import logging
import os
import pandas as pd
import sys
from openai import OpenAI

IMAGES_PER_PROMPT = 25
MAX_TOKENS = 1000000  # 0.5 million

if __name__ == "__main__":
    try_num = int(sys.argv[1])
    in_csv = f"classifications/try{try_num-1}.csv"
    out_dir = f"outputs/try{try_num}"

    # Set up
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    lfhd = logging.FileHandler(f"classify_multiple_failed{try_num}_debug.log")
    lfhd.setLevel(logging.DEBUG)
    logger.addHandler(lfhd)
    lfhi = logging.FileHandler(f"classify_multiple_failed{try_num}.log")
    lfhi.setLevel(logging.INFO)
    logger.addHandler(lfhi)

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
        logging.debug(f"Created out dir: {out_dir}")

    client = OpenAI()

    # Get all failed/incomplete image files
    df = pd.read_csv(in_csv)
    image_files = []
    for _, row in df.iterrows():
        if row.status != "SUCCESS":
            file_doi = row.doi.replace(".", "__").replace("/", "--")
            path = f"../figure-extraction/extracted/{row.conf}/figures/{file_doi}-Figure{row.fig_num}-1.png"
            if path not in image_files:
                image_files.append(path)

    n_images = len(image_files)
    logging.info(f"Got {n_images} image files.")
    # Load prompt
    with open("./prompt_failed.txt", "r") as img_f:
        prompt_txt_base = img_f.read()
        logging.debug(f"Loaded prompt:\n{prompt_txt_base}\n")

    with open("./taxonomy.json", "r") as img_f:
        taxonomy_str = json.dumps(json.load(img_f))
        logging.debug(f"Loaded taxonomy:\n{taxonomy_str}\n")

    prompt_txt_base = prompt_txt_base.replace("<INSERT TAXONOMY>", taxonomy_str)

    # Get classifications
    done = 0
    total_tokens = 0
    for prompt_i in range(0, n_images, IMAGES_PER_PROMPT):
        if os.path.exists(f"{out_dir}/{prompt_i}.json"):
            logging.info(f"\nAlready did i={prompt_i}, skipping!")
            continue

        if total_tokens >= MAX_TOKENS:
            logging.critical(f"\nMax number of tokens reached ({total_tokens}/{MAX_TOKENS})")
            exit()

        image_selection = image_files[prompt_i:min(prompt_i+IMAGES_PER_PROMPT, n_images)]

        content = []
        prompt_txt = prompt_txt_base.replace("<INSERT IMAGE NUMBER>", str(len(image_selection)))

        # Add images to prompt
        for img_i in range(len(image_selection)):
            img_path = image_selection[img_i]

            with open(img_path, "rb") as img_f:
                base64_img = base64.b64encode(img_f.read()).decode("utf-8")

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_img}",
                }
            })
            logging.info(f"({prompt_i}) added {img_path} to content")

        # Query API
        content.insert(0, {"type": "text", "text": prompt_txt})
        logging.debug(f"\n({prompt_i}) prompting with prompt:\n{prompt_txt}")

        msgs = [
            {
                "role": "system",
                "content": "You are an accurate visualization classification system."
            },
            {
                "role": "user",
                "content": content
            }
        ]

        res = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=msgs
        )
        logging.debug(f"({prompt_i}) received res\n{str(res)}")
        classification = res.choices[0].message.content
        used_tokens = res.usage.total_tokens
        total_tokens += used_tokens
        logging.info(f"({prompt_i}) got response, used {used_tokens} tokens ({total_tokens} total used, {MAX_TOKENS - total_tokens} left)")

        out_dict = {
            "img_files": image_selection,
            "classification": classification
        }
        with open(f"{out_dir}/{prompt_i}.json", "w+") as out_f:
            json.dump(out_dict, out_f)
