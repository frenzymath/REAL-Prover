# -*- coding: utf-8 -*-
################################################################################

################################################################################
"""
This module provide configure.
"""


# 支持的几个模型
MODEL_TYPE_LOCAL = 'local'
MODEL_TYPE_GEMINI = 'gemini'
MODEL_TYPE_CLAUDE = 'claude'

# 默认使用的模型List
DEFAULT_MODEL_LIST = [MODEL_TYPE_LOCAL]
# DEFAULT_MODEL_LIST = [MODEL_TYPE_GEMINI]

AIFORMATH_PATH = "/volume/ai4math"

PROVER_MODEL_ID = 'realprover'
PROVER_MODEL_PATH = '/path/to/your/model'
LEAN_TEST_PATH = '/path/to/lean/environment' #Path to repo https://github.com/frenzymath/lean_test_v4160
LEAN_ENV_PATH = "/path/to/lean/dir"

# NUM_SAMPLES = 64
# MAX_DEPTH = 128
# MAX_NODES = 1024
# MAX_CALLS = 1024

NUM_SAMPLES = 16
MAX_DEPTH = 32
MAX_NODES = 64
MAX_CALLS = 512

MAX_RETRIES = 1
USE_BEAM_SEARCH = False
USE_MCTS_SEARCH = False
BEAM_WIDTH = 3
IS_INCONTEXT = False
USE_RETRIEVAL = True

SIM_DEPTH = 5
C_PUCT = 1.0
C_SCORE = 1.0
C_EXPANSION_FAIL_PENALTY = 30.0
MAX_ROOT_EXPANSION = 5

# params for model other than n
PROVER_MODEL_PARAMS = {
    "temperature": 1.5,
    "max_tokens": 256,
    "top_p": 0.9,
    "logprobs": 1
}

API_CONFIG = {
    "lean_search": 'address to leansearch-ps'
}
NUM_QUERYS = 10


CLAUDE_CONFIG = {
    'base_url': 'url path',
    'api_key': 'your api key',
}

OTHER_MODELS = ["gemini", "claude"]

# 此为需要过滤的不合法tactic列表
ABANDON_IF_CONTAIN = ["sorry", "admit", "apply?"]

# interactive 用到的一些配置
from pathlib import Path
base_path = Path(__file__).parent.parent
analyzer_path = Path(base_path, "../jixia/.lake/build/bin/jixia")
interactive_path = Path(base_path, "../interactive")
build_path = Path(base_path, "../interactive/.lake/build")



# 接口验权参数
SALT = "ai-for-math"
EXPIRE_TIME = 5 * 60

# DATA_ID = 'alg-test-v1-20'
# DATA_PATH = 'data/example/alg-test-v1.jsonl'
