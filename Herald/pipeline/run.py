import sys
from util import profiler, CommonUtil
from service import ParallelHttpService
import argparse
def run_http_parallel(args):
    """
    多卡并行运行: 翻译使用http接口
    """

    source_file = args.source_file
    result_dir = args.result_dir
    
    profiler.start(f"pipeline_http_parallel")
    parallel_service = ParallelHttpService(source_file=source_file, result_dir=result_dir, trans_gpus=[0])
    parallel_service.run()
    profiler.stop(f"pipeline_http_parallel")

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source_file', default=None,required=True)
    parser.add_argument('--result_dir', default=None,required=True)
    args = parser.parse_args()
    run_http_parallel(args)