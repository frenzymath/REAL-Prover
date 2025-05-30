# LeanSearch-PS

We leverage [Tevatron V2.0](https://github.com/texttron/tevatron) for training. 

## Two-stage Training Pipeline

### 1. Building pairwise dataset

  This process aims to construct a dataset of $(s, t_{\text{pos}})$ pairs. These pairs are extracted from Mathlib using the Jixia tool. In this context, $s$ refers to a Lean proof state, and $t_{\text{pos}}$ refers to its corresponding theorem. 

  Notice that in Tevatron V2.0 training pipeline, the negative samples should be set to random 64 theorems in the datasets. 

### 2. Initial training
  
  ```
  sh examples/train.sh
  ```

### 3. Building triplets with hard negative data
  
  This process produces triplets of the form $(s, t_{\text{pos}}, t_{\text{hard-neg}})$, where $t_{\text{hard-neg}}$ refers to hard negative premise. For the hard negative examples, we first embed all statements and theorems with the initial trained embedding model, and then randomly select one passage from the top 30 to top 100 most similar ones for each query as its hard negative premise. Specifically, 
  - (1) build query data and corpus data;
  - (2) embed query data and corpus data;
  - (3) search corpus embedding within query embedding;
  - (4) build training data. 
  
  ```
  python build_training_data.py
  ```

### 4. Hard Negative Enhanced Training
  
  ```
  sh examples/train.sh
  ```
