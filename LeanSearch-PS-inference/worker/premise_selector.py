import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
import faiss 
import numpy as np
import json
import conf.config

np.random.seed(42)  # make reproducible

class PremiseSelector(object):
    def __init__(self):
        self.device = 'cuda'

        self.index = faiss.read_index(conf.config.INDEX_PATH)
        self.answer_path = conf.config.ANSWER_PATH
        self.tokenizer = None
        self.model = None
        self.formals = []

        self.init_formals()
        self.init_data()

    def init_formals(self):
        formals = []
        with open(self.answer_path, "r") as fd:
            data = json.load(fd)
            for i in data:
                formals.append(data[i]['Formal name'] + '\n' + data[i]['Formal statement'])
        self.formals = formals

    def init_data(self):
        datas = []
        with open(self.answer_path, "r") as fd:
            data = json.load(fd)
            for i in data:
                datas.append(data[i])
        self.datas = datas

    def init_model(self):
        if self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained(conf.config.TOKENIZER_PATH)
            self.model = AutoModel.from_pretrained(conf.config.MODEL_PATH).half()
            self.model.to(self.device)

    def release_model(self):
        self.tokenizer = None
        self.model = None

    def retrieve(self, queries, num=10):
        self.init_model()
        task = "Given a lean4 context, retrieve Lean4 theorems useful to solve it: "
        if isinstance(queries, str):
            queries = [queries]

        query_vecs = self.get_embeddings(task, queries).cpu().numpy().astype(np.float32)

        # faiss for searching
        D, I = self.index.search(query_vecs, num)

        all_related_theorems = []
        for query_results in I:
            related_theorems = []
            for docid in query_results:
                related_theorems.append(self.datas[docid])
            all_related_theorems.append(related_theorems[:num])

        return all_related_theorems

    def get_embeddings(self, task, input_texts):
        with torch.no_grad():
            max_length = 4096
            detailed_input_texts = [self.get_detailed_instruct(task, input_text) for input_text in input_texts]
            # Tokenize the input texts
            batch_dict = self.tokenizer(detailed_input_texts, max_length=max_length - 1, return_attention_mask=False,
                                        padding=False, truncation=True)
            batch_dict['input_ids'] = [input_ids + [self.tokenizer.eos_token_id] for input_ids in
                                       batch_dict['input_ids']]
            batch_dict = self.tokenizer.pad(batch_dict, padding=True, return_attention_mask=True,
                                            return_tensors='pt').to(
                self.device)

            outputs = self.model(**batch_dict)
            embeddings = self.last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])

            embeddings = F.normalize(embeddings, p=2, dim=1)

            # Release cuda memory
            del batch_dict
            del outputs

        # Release cuda memory
        torch.cuda.empty_cache()

        return embeddings

    def last_token_pool(self, last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

    def get_detailed_instruct(self, task_description: str, query: str) -> str:
        return f'{task_description}\n{query}'
