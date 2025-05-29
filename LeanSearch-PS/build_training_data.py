### build training data for embedding
# The format of the training data is a json file as follow:
#  {
#    "query_id": "<query id>",
#    "query": "<query text>",
#    "positive_passages": [
#      {"docid": "<passage id>", "title": "<passage title>", "text": "<passage body>"},
#      ...
#    ],
#    "negative_passages": [
#      {"docid": "<passage id>", "title": "<passage title>", "text": "<passage body>"},
#      ...
#    ]
# }
# 
# Process for building: 
# 1. build query data and corpus data
# 2. embed query data and corpus data
# 3. search corpus embedding within query embedding 
# 4. build training data


import argparse
import json
import os
import random
import glob
import pickle
from tqdm import tqdm
import subprocess
import numpy as np

def build_query_and_corpus_data(args):
    print('Building query and corpus data')
    # Step 1: build query data and corpus data
    if os.path.exists(os.path.join(args.save_dir, 'query_data/')) and os.path.exists(os.path.join(args.save_dir, 'corpus_data/')):
        print("query and corpus data already exist")
        return 
    os.makedirs(os.path.join(args.save_dir, 'query_data/'))
    os.makedirs(os.path.join(args.save_dir, 'corpus_data/'))
    with open('./answers.json', 'r') as f:
        answers = json.load(f)
    for key, value in tqdm(answers.items(), ):
        corpus_data, query_data = {}, {}
        query_data['query_id'] = key
        query_data['query'] = value['Informal statement']
        corpus_data['docid'] = key
        corpus_data['title'] = ""
        corpus_data['text'] = f"Formal name: {value['Formal name']} Formal statement: {value['Formal statement']}"
        # Save the query data to a file
        with open(os.path.join(args.save_dir, 'query_data/query_data.json'), 'a') as f:
            json.dump(query_data, f, ensure_ascii=False)
            f.write('\n')
        # Save the corpus data to a file
        with open(os.path.join(args.save_dir, 'corpus_data/corpus_data.json'), 'a') as f:
            json.dump(corpus_data, f, ensure_ascii=False)
            f.write('\n')

def embed_query_and_corpus_data(args):
    print('Embedding query and corpus data')
    # Step 2: embed query data and corpus data
    if not os.path.exists(os.path.join(args.save_dir, 'query_embedding/')):
        os.makedirs(os.path.join(args.save_dir, 'query_embedding/'))
    if not os.path.exists(os.path.join(args.save_dir, 'corpus_embedding/')):
        os.makedirs(os.path.join(args.save_dir, 'corpus_embedding/'))
    # query embedding 
    print("----embed query data")
    processes = []
    for s in args.gpu_ids:
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(s)
        command = [
            'python', '-m', 'tevatron.retriever.driver.encode',
            '--output_dir=temp',
            '--model_name_or_path', args.model_name_or_path,
            '--lora', '--lora_name_or_path', args.lora_name_or_path, 
            '--query_prefix', '"Given a math statement, retrieve Lean4 code mathematically equivalent to it: "',
            '--passage_prefix', '"Lean4 code: "',
            '--bf16',
            '--pooling', 'eos',
            '--append_eos_token',
            '--normalize',
            '--encode_is_query',
            '--per_device_eval_batch_size', '128',
            '--query_max_len', '128',
            '--passage_max_len', '256',
            '--dataset_name', os.path.join(args.save_dir, 'query_data/'),
            '--dataset_number_of_shards', str(len(args.gpu_ids)),
            '--dataset_shard_index', str(s),
            '--encode_output_path', os.path.join(args.save_dir, 'query_embedding/query.{}.pkl'.format(s)),
        ]
        # if args.lora:
        #     command = command[:6] + ['--lora', '--lora_name_or_path', args.lora_name_or_path] + command[6:]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        processes.append(process)
    for p in processes:
        p.wait()
    # corpus embedding
    print("----embed corpus data")
    processes = []
    for s in args.gpu_ids:
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(s)
        command = [
            'python', '-m', 'tevatron.retriever.driver.encode',
            '--output_dir=temp',
            '--model_name_or_path', args.model_name_or_path,
            '--lora', '--lora_name_or_path', args.lora_name_or_path, 
            '--query_prefix', 'Given a math statement, retrieve Lean4 code mathematically equivant to it: ',
            '--passage_prefix', 'Lean4 code: ',
            '--bf16',
            '--pooling', 'eos',
            '--append_eos_token',
            '--normalize',
            '--per_device_eval_batch_size', '128',
            '--query_max_len','128',
            '--passage_max_len', '256',
            '--dataset_name', os.path.join(args.save_dir, 'corpus_data/'),
            '--dataset_number_of_shards', str(len(args.gpu_ids)),
            '--dataset_shard_index', str(s),
            '--encode_output_path', os.path.join(args.save_dir, 'corpus_embedding/corpus.{}.pkl'.format(s)), 
        ]
        # if args.lora:
        #     command = command[:6] + ['--lora', '--lora_name_or_path', args.lora_name_or_path] + command[6:]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        processes.append(process)
    for p in processes:
        p.wait()
    
def search(args):
    print('Searching corpus embedding within query embedding')
    # Step 3: search corpus embedding within query embedding
    index_files = glob.glob(os.path.join(args.save_dir, 'query_embedding/query.*.pkl'))
    reps_list, lookup_list = [], []
    for path in index_files:
        with open(path, 'rb') as f:
            reps, lookup = pickle.load(f)
            print(reps.shape, type(lookup))
            reps_list.append(reps)
            lookup_list += lookup
    reps_array = np.vstack(reps_list)
    print(reps_array.shape)
    with open(os.path.join(args.save_dir, 'query_embedding/query.pkl'), 'wb') as f:
        pickle.dump((reps_array, lookup_list), f)
    command = [
        'set', '-f', '&&', 'python', '-m', 'tevatron.retriever.driver.search',
        '--query_reps', os.path.join(args.save_dir, 'query_embedding/query.pkl'),
        '--passage_reps', os.path.join(args.save_dir, 'corpus_embedding/corpus.*.pkl'), 
        '--depth', str(args.top_k),
        '--batch_size', '64',
        '--save_text',
        '--save_ranking_to', os.path.join(args.save_dir, 'retrieval.txt'),
    ]
    subprocess.run(command[3:])
    
def build_training_data(args):
    print('Building training data')
    # Step 4: build training data
    with open('./answers.json', 'r') as f:
        answers = json.load(f)
    training_dataset = {}
    with open(os.path.join(args.save_dir, 'retrieval.txt'), 'r', encoding='utf-8') as f:
        content = f.read().strip()
        for line in tqdm(content.split(sep='\n')):
            parts = line.split(sep='\t')
            query_id, docid = int(parts[0]), parts[1]
            try:
                training_dataset[query_id].append(docid)
            except:
                training_dataset[query_id] = [docid]
    # 按照query_id对training_data这个dir排序
    training_dataset = sorted(training_dataset.items(), key=lambda x: x[0])
    with open(os.path.join(args.save_dir, 'training_data.json'), 'w', encoding='utf-8') as f:
        random.seed(args.seed)
        for query_id, data in tqdm(training_dataset):
            if args.is_choice:
                docids = [data[random.randrange(args.bottom_k, args.top_k)]]
            else:
                docids = data[args.bottom_k:args.top_k]
            train_data = {
                "query_id": query_id,
                "query": answers[str(query_id)]['Informal statement'],
                "positive_passages": [{
                    "doc_id": query_id,
                    "title": answers[str(query_id)]['Formal name'],
                    "text": answers[str(query_id)]['Formal statement']
                }],
                "negative_passages": [{
                    "doc_id": int(docid),
                    "title": answers[docid]['Formal name'],
                    "text": answers[docid]['Formal statement']
                } for docid in docids],
            }
            json.dump(train_data, f, ensure_ascii=False)
            f.write('\n')

if __name__ == "__main__":
    # build parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_name_or_path', type=str, default='./models/model_name_or_path')
    parser.add_argument('--lora', action='store_true')
    parser.add_argument('--lora_name_or_path', type=str, default='./checkpoints/lora_name_or_path')
    parser.add_argument('--top_k', type=int, default=100)
    parser.add_argument('--bottom_k', type=int, default=30)
    parser.add_argument('--save_dir', type=str, default='./datasets/training_data')
    parser.add_argument('--gpu_ids', type=list, default=[0,1,2,3])
    parser.add_argument('--is_choice', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    
    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)
    # Step 1: build query data and corpus data
    build_query_and_corpus_data(args)
    # Step 2: embed query data and corpus data
    embed_query_and_corpus_data(args)
    # Step 3: search corpus embedding within query embedding 
    search(args)
    # Step 4: build training data
    build_training_data(args)
