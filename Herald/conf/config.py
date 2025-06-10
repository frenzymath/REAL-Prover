# -*- coding: utf-8 -*-
################################################################################

################################################################################
"""
This module provide configure.
"""

AIFORMATH_PATH = "/AI4M"  # 挂载磁盘的路径

MODEL_CONFIG = {
    'trans': "FrenzyMath/Herald_translator",  # informal -> formal
    'back_trans': "deepseek-ai/DeepSeek-V3",  # formal -> informal
    'compare': "deepseek-ai/DeepSeek-V3"
}

LEAN_TEST_PATH = "/path/to/lean_test"
DEFAULT_LAKE_PATH = '/path/to/lake'


NIM_CONFIG = {
    'url': "https://api.deepseek.com/v1",
    'key': "your api key"
}

# API_CONFIG = {
#     "step_prover": 'Your realprover address' #not use now
# }



# 线程数量控制
THREAD_CONFIG = {
    "lean_build": 10,
    "same_check": 10,
    "proof": 5
}

TRAN_CONFIG = {
    'sampling_params': dict(
        n=8,
        max_tokens=1024,
        temperature=0.99,
        top_p=0.99,
    )
}

SALT = "ai-for-math"
EXPIRE_TIME = 5 * 60
