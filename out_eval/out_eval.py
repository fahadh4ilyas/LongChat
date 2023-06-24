import json
import math
import re
import numpy as np

from pathlib import Path
from util.out_eval_util import *

SCRIPT_PATH = Path(__file__).resolve()
WORKING_DIR = SCRIPT_PATH.parent
REPO_DIR = WORKING_DIR / Path("../")


def run_lrt_exp(cfgs):
    raise NotImplementedError()


def run_conv_eval_exp(cfgs, tokenizer):
    TEST_DIR = WORKING_DIR / Path(f"{cfgs['model_name']}_testcases")
    output_dir = WORKING_DIR / Path(f"{cfgs['model_name']}_predictions")
    test_files = list(TEST_DIR.iterdir())

    if not output_dir.exists():
        output_dir.mkdir()

    for num_topics in cfgs["num_topics"]:
        print(f"**********Start testing {num_topics} topics per prompt**********")

        for file in test_files:
            if re.search(f"^{num_topics}_topics_{cfgs['question_dist']}", \
                         str(file.name)) is not None:
                test_file = file
                break

        with open(test_file, 'r') as json_file:
            conversation_list = list(json_file)

        total_sim_score = 0

        output_file = output_dir / Path(f"{test_file.stem}.prediction")
        for test_case in conversation_list:
            test_case = json.loads(test_case)
            prompt = test_case["prompt"]
            prompt_length = test_case["total_length"]
            topics = test_case["topics"]
            picked_topics = test_case["picked_topics"]
            lenth_dist = [float(i)/sum(test_case["length"]) for i in test_case["length"]]

            response = query_model(cfgs["model_name"], cfgs["model_path"], 
                                    prompt, tokenizer, cfgs["local_model"],
                                    cfgs["gpu_id"])
            summary = f"Label:      {picked_topics}, \nPrediction: {response}, \ntopics:     {topics}, \nprompt_length: {prompt_length}, \nlength_dist: {lenth_dist}\n"

            print(summary)
            with open(output_file, "a+") as f:
                f.write(summary)
                f.write("\n")
        
        acc = total_sim_score / len(conversation_list)
        with open(output_file, "a+") as f:
            f.write(f"\naccuracy: {acc}\n")
            f.close()
        output_file.rename(output_dir / Path(f"{test_file.stem}_{acc}.prediction"))
        # print(f"accuracy: {acc}")


def generate_conversations(cfgs, tokenizer):
    conv_list = []

    output_dir = WORKING_DIR / Path(f"{cfgs['model_name']}_testcases")
    if not output_dir.exists():
        output_dir.mkdir()
    
    with open(REPO_DIR / Path("evaluation/topics/conversations.jsonl"), 'r') as json_file:
        conv_obj_list = list(json_file)

    for conv_obj in conv_obj_list:
        conv_obj = json.loads(conv_obj)
        conv_len = token_counter(tokenizer, cfgs["model_name"], cfgs["model_path"], conv_obj["conversation"])
        conv_list.append(Conv(conv_obj["topic"], conv_len, conv_obj["conversation"]))

    # generate prompts for each num_topics
    for num_topics in cfgs["num_topics"]:

        prompt_list = []
        
        for i in range(cfgs["num_test_samples"]):
            prompt = Prompt(cfgs["model_name"], cfgs["model_path"], i, cfgs["question_dist"], tokenizer)
            indices = np.random.choice(list(range(len(conv_list))), size=num_topics, replace=False)
            for idx in indices:
                prompt.add_conv(conv_list[idx])
            prompt_list.append(prompt)
            
            prompt = None
        
        # write to output file
        avg_len = 0
        output_path = output_dir / Path(f"{num_topics}_topics_{cfgs['question_dist']}.jsonl")
        f = open(output_path, "w")
        for i, p in enumerate(prompt_list):
            pt, picked_topics = p.assemble_prompt()
            
            curr_output = {"test_id": p.id, 
                           "picked_topics": picked_topics,
                           "topics": p.topic_list, 
                           "length": p.length_list, 
                           "total_length": p.length,
                           "prompt": pt}
            avg_len += p.length
            json.dump(curr_output, f)
            f.write("\n")
        avg_len = math.ceil(avg_len/len(prompt_list))
        f.close()

        output_path.rename(output_dir / Path(f"{num_topics}_topics_{cfgs['question_dist']}_{avg_len}.jsonl"))

def main():
    cfgs = retrieve_cmd_args()
    tokenizer = load_tokenizer(cfgs["model_name"], cfgs["model_path"], cfgs["local_model"])
    
    if cfgs["level"] == "easy":
        generate_conversations(cfgs, tokenizer)
        run_conv_eval_exp(cfgs, tokenizer)
    else:
        run_lrt_exp(cfgs, tokenizer)

if __name__ == "__main__":
    main()