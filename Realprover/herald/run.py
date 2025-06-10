""""
使用Herald-pipeline 跑出的数据继续stepprover
"""
import sys
import torch
from manager.service import PipelineMainService
import argparse

def run_herald_stepprover(args):
    source_file = args.source_file
    result_dir = args.result_file
    gpus = torch.cuda.device_count()
    assert gpus >= 1
    # 使用全部可用的卡，第一张卡默认用作翻译
    gpu_list = list(range(1, gpus))
    print(gpu_list)
    pipeline_service = PipelineMainService(source_file=source_file, result_dir=result_dir, gpus_list=gpu_list)
    # gpu_list = list(range(torch.cuda.device_count()))

    pipeline_service.run_pipeline_prover()

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source_file', default=None,required=True)
    parser.add_argument('--result_dir', default=None,required=True)
    args = parser.parse_args()
    run_herald_stepprover(args)