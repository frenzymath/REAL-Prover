import threading
import torch.multiprocessing as mp
import os
import time
import sys
from pathlib import Path
import traceback
from manager.service import BaseService
from manager.thirdparty import TacticGenerator
from util import CommonUtil #, profiler
import conf.config
from manager.thirdparty.verifier import verify_proof


def data_producer(queue, counter, total_count, result_dir, file_prefix, re_run, num_workers=2):
    """
    轮训检测Herald生成的back_trans的数据，并添加到队列中
    """
    exist_keys = set()

    while True:
        print("run_data_producer")
        for index in range(total_count):
            unique_key = f"{file_prefix}{index}"
            tran_path = f"{result_dir}/{unique_key}/back_trans.json"
            prove_path = f"{result_dir}/{unique_key}/prove_info.json"
            if CommonUtil.file_exist(tran_path):
                if CommonUtil.file_exist(prove_path) and not re_run:
                    # 结果文件已经存在 & 不需要重新跑时
                    exist_keys.add(unique_key)
                else:
                    if unique_key not in exist_keys:
                        json_data = CommonUtil.load_json(tran_path)
                        json_data['prove_path'] = prove_path

                        exist_keys.add(unique_key)
                        queue.put(json_data)
                        counter.value += 1

        print(f"exist_keys_size = {len(exist_keys)}")
        print(f"queue_size: {counter.value}")
        if len(exist_keys) >= total_count:
            print(f"producer_finished_count = {len(exist_keys)}")
            for _i in range(num_workers):
                # 完成时发送空消息给消费者
                queue.put(None)
            break

        sys.stdout.flush()  # 保证该线程内的日志正常输出
        # m每20s循环检测一次
        time.sleep(20)


class PipelineMainService(BaseService):
    """
    处理Herald_pipeline 生成的formal_statement
    单独处理原因: 特定的结构体, informal_statement, translate_list, back_trans_list

    整体思路:
        定时器轮训检测Herald生成的每个文件的 "back_trans.json" 文件, 如何存在则添加到待队列中，全部添加完成后停止掉定时器
        多进程从队列中获取待执行任务, 每条数据执行完成后保存结果文件到 "prove_info.json" 中
    """

    def __init__(self,
                 source_file: str,
                 result_dir: str,
                 gpus_list=None,
                 num_samples: int = conf.config.NUM_SAMPLES,
                 max_calls: int = conf.config.MAX_NODES,
                 root: Path = Path(conf.config.LEAN_TEST_PATH),
                 lean_env: str = conf.config.LEAN_ENV_PATH,
                 model_list: list = conf.config.DEFAULT_MODEL_LIST,
                 local_model_path: str = conf.config.PROVER_MODEL_PATH,
                 re_run=False
                 ):
        """

        """
        super().__init__(num_samples=num_samples, max_nodes=max_calls, root=root, lean_env=lean_env,
                         model_list=model_list, local_model_path=local_model_path)
        self.source_file = source_file
        self.result_dir = result_dir
        if gpus_list is None:
            gpus_list = [0]
        self.gpus_list = gpus_list

        self.source_list = CommonUtil.read_json_list(self.source_file)
        self.length = len(self.source_list)
        self.back_data_list = []
        self.file_prefix = f"index_"

        self.manager = mp.Manager()

        self.queue = mp.Queue()
        self.counter = mp.Value('i', 0)  # 初始化计数器,用来存储队列中的数据量
        self.generator = self.manager.dict()
        self.re_run = re_run

    def _check_add_task_to_queue(self):
        """
        """
        producer_thread = threading.Thread(target=data_producer, args=(self.queue, self.counter, len(self.source_list),
                                                                       self.result_dir, self.file_prefix,
                                                                       self.re_run, len(self.gpus_list)),
                                           daemon=True)
        producer_thread.start()

    def _add_exist_to_queue(self):
        """
        添加已经back_tran完成的数据到queue
        """
        print("_add_exist_to_queue")
        add_index_list = []
        for index in range(len(self.source_list)):
            unique_key = f"{self.file_prefix}{index}"
            tran_path = f"{self.result_dir}/{unique_key}/back_trans.json"
            prove_path = f"{self.result_dir}/{unique_key}/prove_info.json"
            if not CommonUtil.file_exist(tran_path):
                continue
            if CommonUtil.file_exist(prove_path) and not self.re_run:
                continue
            json_data = CommonUtil.load_json(tran_path)
            json_data['prove_path'] = prove_path

            add_index_list.append(index)
            self.queue.put(json_data)
            self.counter.value += 1
        for _ in self.gpus_list:
            self.queue.put(None)
        print(
            f"add_count = {len(add_index_list)}, min_index = {min(add_index_list)}, max_index = {max(add_index_list)}")

    def _int_generator(self):
        for i in self.gpus_list:
            self.generator[i] = TacticGenerator(self.model_list, i, self.local_model_path)

    def _process_run(self, gpu_id: int):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        this_generator = self.generator[gpu_id]
        while True:
            item = self.queue.get()
            if item is None:  # 检测结束信号
                break
            self.counter.value -= 1
            prove_detail_dict = {}
            result_list = []  # 收集成对的formal_statement 和formal_proof

            # profiler.start(f"run_time_{item['unique_key']}")
            print(f"run_time_start_{item['unique_key']}: back_size = {len(item['back_trans_list'])}: gpu_id = {str(gpu_id)}",flush=True)
            for inner_index, formal_statement in enumerate(item['back_trans_list']):
                try:
                    temp_results = self.process_one(source=formal_statement, generator=this_generator)
                    temp_result = self.parse_result(formal_statement, temp_results)
                    # check result right
                    if 'formal_proof' in temp_result:
                        try:
                            repl_res = verify_proof(temp_result['formal_proof'],os.path.join(conf.config.LEAN_ENV_PATH,'bin/lake'),conf.config.LEAN_TEST_PATH)
                        except Exception as e:
                            print(traceback.format_exc())
                            repl_res = False
                    else:
                        repl_res = False
                    prove_detail_dict[inner_index] = temp_result

                    if repl_res:  # 如果proof成功
                        result_list.append({
                            'formal_statement': formal_statement,
                            'formal_proof': temp_result['formal_proof']
                        })
                except Exception as e:
                    print(f"Error occurred: {e}")
                    print(f"run_error_unique_key = {item['unique_key']}")

            item['prove_detail_dict'] = prove_detail_dict
            item['result_list'] = result_list
            CommonUtil.write_to_json_file(item['prove_path'], item)

            # profiler.stop(f"run_time_{item['unique_key']}")
            print(f"run_time_finished_{item['unique_key']}")

    def run_pipeline_prover(self):
        """

        """
        process_list = []
        self._check_add_task_to_queue()  # herald实时产生数据时使用此处
        # self._add_exist_to_queue()      # Herald数据已产生完成时使用此处

        self._int_generator()

        for i in self.gpus_list:
            # 创建trans进程
            process = mp.Process(target=self._process_run, args=(i,))
            process.start()
            process_list.append(process)

        for j in range(len(process_list)):
            process_list[j].join()
        print("All data processed.")
