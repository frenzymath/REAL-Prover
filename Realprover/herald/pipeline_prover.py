""""
使用Herald-pipeline 跑出的数据继续stepprover
"""
import torch

from manager.service import PipelineMainService
from util import CommonUtil, profiler


FILE_DIR = "data"
# source_file = f"{FILE_DIR}/example/simp.jsonl"
# result_dir = f"{FILE_DIR}/example_result/simp"

source_file = f"{FILE_DIR}/example/simp_10.jsonl"
result_dir = f"{FILE_DIR}/example_result/simp_10"



def run_herald_stepprover():
    gpus = torch.cuda.device_count()
    assert gpus >= 1
    # 默认使用全部可用的gpu卡，可以自己配置
    gpu_list = list(range(gpus))
    print(gpu_list)

    pipeline_service = PipelineMainService(source_file=source_file, result_dir=result_dir, gpus_list=gpu_list)
    # gpu_list = list(range(torch.cuda.device_count()))

    pipeline_service.run_pipeline_prover()


if __name__ == '__main__':
    profiler.start("run_prover")
    run_herald_stepprover()
    profiler.stop("run_prover")
