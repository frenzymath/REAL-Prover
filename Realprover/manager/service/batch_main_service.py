import os
from pathlib import Path
import multiprocessing as mp
import traceback
from manager.thirdparty import TacticGenerator
from manager.service import BaseService
from util import CommonUtil, profiler
import conf.config
from manager.search.exception import SearchError, error_logging
import logging
from manager.thirdparty.verifier import verify_proof
import json

def search_check(path, max_retries):
    cnt = 0
    for root, dir, files in os.walk(path):
        for file in files:
            connect_error = False
            if '.json' in file and os.path.samefile(path,root):
                file_path = os.path.join(root, file)
                with open(file_path,'r') as f:
                    try:
                        file_json = json.load(f)
                        for res in file_json["collect_results"]:
                            if res['success']:
                                return True
                            if len(res['calls'])==0:
                                connect_error=True
                    except:
                        return False
                if not connect_error:
                    cnt += 1
    if cnt == max_retries:
        return True
    else:
        return False

class BatchMainService(BaseService):
    """
    多进程批量执行prover,
    """

    def __init__(self,
                source_file: str,
                result_dir: str,
                gpus_list=None,
                num_samples: int = conf.config.NUM_SAMPLES,
                max_nodes: int = conf.config.MAX_NODES,
                max_depth: int = conf.config.MAX_DEPTH,
                use_beam_search: bool = conf.config.USE_BEAM_SEARCH,
                use_mcts_search: bool = conf.config.USE_MCTS_SEARCH,
                simulation_depth: int = conf.config.SIM_DEPTH,
                c_puct: float = conf.config.C_PUCT,
                beam_width: int = conf.config.BEAM_WIDTH,
                root: Path = Path(conf.config.LEAN_TEST_PATH),
                lean_env: str = conf.config.LEAN_ENV_PATH,
                model_list: list = conf.config.DEFAULT_MODEL_LIST,
                local_model_path: str = conf.config.PROVER_MODEL_PATH,
                sampling_params: dict = conf.config.PROVER_MODEL_PARAMS,
                max_retries: int = conf.config.MAX_RETRIES,
                c_score: float = conf.config.C_SCORE,
                c_expansion_fail_penalty: float = conf.config.C_EXPANSION_FAIL_PENALTY,
                max_root_expansion: int = conf.config.MAX_ROOT_EXPANSION,
                max_calls: int = conf.config.MAX_CALLS,
                abandon_if_contain: list[str] = conf.config.ABANDON_IF_CONTAIN,
                is_incontext: bool = conf.config.IS_INCONTEXT,
                template: str = 'deepseek',
                use_retrieval: bool = conf.config.USE_RETRIEVAL
                ):
        """

        """
        # 支持此种方式透传的原因是：可能存在执行方参数配置的输入
        super().__init__(num_samples=num_samples, 
                        max_nodes=max_nodes,
                        max_depth=max_depth,
                        use_beam_search=use_beam_search,
                        use_mcts_search=use_mcts_search,
                        simulation_depth=simulation_depth,
                        c_puct=c_puct,
                        beam_width=beam_width,
                        root=root, 
                        lean_env=lean_env,
                        model_list=model_list, 
                        local_model_path=local_model_path,
                        sampling_params=sampling_params,
                        max_calls=max_calls,
                        max_root_expansion=max_root_expansion,
                        c_score=c_score,
                        c_expansion_fail_penalty=c_expansion_fail_penalty,
                        abandon_if_contain = abandon_if_contain,
                        is_incontext = is_incontext,
                        template=template,
                        use_retrieval=use_retrieval)
        self.source_file = source_file
        self.result_dir = result_dir
        self.max_retries = max_retries
        if not os.path.exists(self.result_dir+'/generated'):
            os.makedirs(self.result_dir+'/generated')
        if not os.path.exists(self.result_dir+'/error'):
            os.makedirs(self.result_dir+'/error')
        logging.basicConfig(
            filename=f"{self.result_dir}/error.log",  # File where logs will be saved
            level=logging.ERROR,       # Log level
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        if gpus_list is None:
            gpus_list = [0]
        self.gpus_list = gpus_list

        self.manager = mp.Manager()
        self.generator = self.manager.dict()
        self.queue = mp.Queue()

        self.source_list = []
        
        

    def _init_source_list(self):
        data_list = CommonUtil.read_json_list(self.source_file)
        print(f"data_list = {len(data_list)}")
        for source_index, item in enumerate(data_list):
            # 添加在原始文件的索引
            item['source_index'] = source_index
        self.source_list = data_list

    def _int_generator(self):
        for i in self.gpus_list:
            self.generator[i] = TacticGenerator(
                model_list=self.model_list,
                gpu_id=i, 
                local_model_path=self.local_model_path,
                sampling_params=self.sampling_params,
                max_calls=self.max_calls)

    def _int_queue(self):
        for item in self.source_list:
            self.queue.put(item)
        for _ in self.gpus_list:
            self.queue.put(None)

    def _process_run(self, gpu_id: int):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        this_generator = self.generator[gpu_id]
        while True:
            item = self.queue.get()
            if item is None:  # 检测结束信号
                break
            item_path = os.path.join(self.result_dir,'generated',f"{item['id']}")
            if not os.path.exists(item_path):
                os.makedirs(item_path)
            if search_check(item_path, self.max_retries):
                continue
            for idx in range(self.max_retries):
                try:
                    print(f"processing {item['id']}")
                    profiler.start(f"run_index_{item['id']}")
                    results = self.process_one(source=item["formal_statement"], generator=this_generator)
                    profiler.stop(f"run_index_{item['id']}")
                except SearchError as e:
                    error_log_path = f"{self.result_dir+'/error'}/{item['id']}.json"
                    error_logging(error_log_path, item["id"], item["formal_statement"], e.error_data)
                    # CommonUtil.write_to_json_file(error_log_path, e.error_data)
                    logging.error([e.error_type,item['id'], "Searching Error"] ,exc_info=True)
                except Exception as e:
                    print(traceback.format_exc())
                    print(f"Error occurred: {e}")
                    print(f"run_error_index = {item['id']}")
                    logging.error([e,item['id'], "Non-Searching Error"] ,exc_info=True)
                else:
                    save_data = self.parse_result(item["formal_statement"], results)
                    if 'formal_proof' in save_data:
                        try:
                            print(f"lake repl check:{item['id']}",flush=True)
                            repl_res = verify_proof(save_data['formal_proof'],os.path.join(conf.config.LEAN_ENV_PATH,'bin/lake'),conf.config.LEAN_TEST_PATH)
                        except Exception as e:
                            print(traceback.format_exc())
                            save_data['collect_results'][0]['success'] = False
                        else:
                            save_data['collect_results'][0]['success'] = repl_res
                    result_file = os.path.join(item_path,f"{item['id']}_{idx}.json")
                    CommonUtil.write_to_json_file(result_file, save_data)
                    print(f"finish_index_{item['id']}",flush=True)
                    if save_data['collect_results'] and save_data['collect_results'][0]['success']:
                        break
                    else:
                        continue
            self.info.update(self.get_info())
        print(self.info)
    
    def batch_run(self):
        """

        """
        process_list = []
        self._init_source_list()
        self._int_generator()
        self._int_queue()
        for i in self.gpus_list:
            # 创建trans进程
            process = mp.Process(target=self._process_run, args=(i,))
            process.start()
            process_list.append(process)

        for j in range(len(process_list)):
            process_list[j].join()
        print("All data processed.")
    
    def get_info(self):
        return dict(
            max_retries=self.max_retries,
            source_file=self.source_file,
            result_dir=self.result_dir
        )