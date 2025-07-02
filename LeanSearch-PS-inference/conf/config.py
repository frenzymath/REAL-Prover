"""
This module provide configurations.
"""
INDEX_PATH = "path/to/faiss/index"
TOKENIZER_PATH = "intfloat/e5-mistral-7b-instruct"
MODEL_PATH = "path/to/embedding/model"
ANSWER_PATH = "path/to/answer/data"


EXPIRE_TIME = 5 * 60

TEST_QUERY = '''G : Type u_1
      inst✝ : Group G
      a b c : G
      ⊢ (fun x => a * x * b = c) (a⁻¹ * c * b⁻¹) ∧ ∀ (y : G), (fun x => a * x * b = c) y → y = a⁻¹ * c * b⁻¹'''


