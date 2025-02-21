import base64
import json
import logging
import os
import re
from openai import OpenAI

IMAGES_PER_PROMPT = 25
OUT_DIR = "outputs/try1"
MAX_TOKENS = 2350000  # 2.35 million

if __name__ == "__main__":
    # Set up
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    lfhd = logging.FileHandler("classify_debug.log")
    lfhd.setLevel(logging.DEBUG)
    logger.addHandler(lfhd)
    lfhi = logging.FileHandler("classify.log")
    lfhi.setLevel(logging.INFO)
    logger.addHandler(lfhi)

    if not os.path.exists(OUT_DIR):
        os.mkdir(OUT_DIR)
        logging.debug(f"Created out dir: {OUT_DIR}")

    client = OpenAI()

    # Get all image files
    image_files = []
    for conf in os.listdir("../figure-extraction/extracted"):
        for fig in os.listdir(f"../figure-extraction/extracted/{conf}/figures"):
            if not fig.split("-")[-2].startswith("Figure"):
                continue
            image_files.append(f"../figure-extraction/extracted/{conf}/figures/{fig}")

    n_images = len(image_files)
    logging.info(f"Got {n_images} image files.")

    # Load prompt
    with open("./prompt.txt", "r") as img_f:
        prompt_txt_base = img_f.read()
        logging.debug(f"Loaded prompt:\n{prompt_txt_base}\n")

    with open("./taxonomy.json", "r") as img_f:
        taxonomy_str = json.dumps(json.load(img_f))
        logging.debug(f"Loaded taxonomy:\n{taxonomy_str}\n")

    prompt_txt_base = prompt_txt_base.split("<INSERT TAXONOMY>")[0] + taxonomy_str + prompt_txt_base.split("<INSERT TAXONOMY>")[1]

    # Get classifications
    done = 0
    total_tokens = 0
    for prompt_i in range(0, n_images, IMAGES_PER_PROMPT):
        if os.path.exists(f"{OUT_DIR}/{prompt_i}.json"):
            logging.info(f"\nAlready did i={prompt_i}, skipping!")
            continue

        if total_tokens >= MAX_TOKENS:
            logging.critical(f"\nMax number of tokens reached ({total_tokens}/{MAX_TOKENS})")
            exit()

        image_selection = image_files[prompt_i:min(prompt_i+IMAGES_PER_PROMPT, n_images)]
        print("\n".join(image_selection))

        content = []
        prompt_txt = prompt_txt_base

        # Add images to prompt
        for img_i in range(len(image_selection)):
            img_path = image_selection[img_i]

            with open(img_path, "rb") as img_f:
                base64_img = base64.b64encode(img_f.read()).decode("utf-8")

            path_match = re.search(r"../figure-extraction/extracted/(.+\-.+)/figures/(10_.+\-.+)\-Figure([0-9]+)", img_path)
            if path_match is None:
                logging.error(f"({prompt_i}) could not parse image path {img_path}")
                continue
            data_path = f"../figure-extraction/extracted/{path_match[1]}/data/{path_match[2]}.json"
            with open(data_path, "r") as data_f:
                data = json.load(data_f)
            for fig in data:
                if fig["figType"] == "Figure" and fig["name"] == path_match[3]:
                    caption = fig["caption"]
                    prompt_txt += f" The caption of image number {img_i} given is \"{caption}\"."
                    break

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
        with open(f"{OUT_DIR}/{prompt_i}.json", "w+") as out_f:
            json.dump(out_dict, out_f)
