# LeanSearch-PS Server

## Quickstart

1. Install dependencies

   ```bash
   pip install transformers==4.52.4 faiss-gpu==1.12 flask
   ```

2. Download Models and FAISS index

   -   LeanSearch-PS model:  
        [https://huggingface.co/FrenzyMath/LeanSearch-PS](https://huggingface.co/FrenzyMath/LeanSearch-PS)
        
   -   FAISS index:  
        [https://huggingface.co/FrenzyMath/LeanSearch-PS-faiss](https://huggingface.co/FrenzyMath/LeanSearch-PS-faiss)

3. Configure the Server

   Update the configuration file at [`conf/config.py`](conf/config.py):
   ```python
   INDEX_PATH = "path/to/faiss/index"
   TOKENIZER_PATH = "intfloat/e5-mistral-7b-instruct"
   MODEL_PATH = "FrenzyMath/LeanSearch-PS"
   ANSWER_PATH = "path/to/answer/data" # answer.json in repo https://huggingface.co/FrenzyMath/LeanSearch-PS-faiss
   ```

4. Start LeanSearch-PS server

   ```bash
   python server.py
   ```

5. Test server avaibility

   ```bash
   python -m test.test_request
   ```

## Run locally

```bash
python -m test.test_local_run
```
