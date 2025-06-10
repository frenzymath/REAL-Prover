import os
import torch
import multiprocessing as mp

from service.handler import TranHandler, BackHandler
from util import CommonUtil


class ParallelService(object):
    """
    多卡并行运行服务：翻译使用本地模型
    """

    def __init__(self, source_file, result_dir, re_run=False,
                 trans_gpus=None, back_gpus=None):
        """
        source_file: 输入文件jsonl路径
        result_dir: 输出文件目录
        re_run: 已经存在结果文件时, True: 重新run, False: 跳过
        trans_gpus: trans用到的gpu卡
        back_gpus: 反翻译用到的gpu卡
        """
        if trans_gpus is None:
            trans_gpus = [0]
        if back_gpus is None:
            back_gpus = [1]

        self.source_file = source_file
        self.result_dir = result_dir
        self.re_run = re_run
        self.trans_gpus = trans_gpus
        self.back_gpus = back_gpus

        # 初始化原始数据
        self._init_source_list()

        self.manager = mp.Manager()
        self.shared_dict = self.manager.dict()  # 创建一个共享字典
        self._init_one_share_data()

        self.trans_queue = mp.Queue()
        self.back_queue = mp.Queue()
        self.lock = mp.Lock()

        # 存放handler, Key是gpu_id
        self.handler = self.manager.dict()

    def _init_handler(self):
        for i in self.trans_gpus:
            self.handler[i] = TranHandler()
        for j in self.back_gpus:
            self.handler[j] = BackHandler()

    def _init_source_list(self):
        source_list = CommonUtil.read_json_list(self.source_file)
        # unique_key 用来作为唯一索引和每条结果文件的目录
        for index, item in enumerate(source_list):
            item['unique_key'] = f"index_{index}"
        self.source_list = source_list

    def _init_one_share_data(self):
        """
        初始化结构体数据
        """
        for item in self.source_list:
            temp_dict = {
                'unique_key': item['unique_key'],
                'informal_statement': item['informal_statement'],
                'translate_list': [],
                'back_trans_list': [],
            }
            temp_dict.update(item)
            self.shared_dict[item['unique_key']] = self.manager.dict(temp_dict)

    def _set_dict_data(self, key_name, type_name, data_list):
        try:
            with self.lock:  # 使用锁来确保对 shared_dict 的操作是线程安全的
                self.shared_dict[key_name][type_name] = data_list
        except BrokenPipeError as e:
            print(f"Error: {e}")

    def _init_trans_queue(self):
        for item in self.source_list:
            if not self.re_run:
                # 不重新跑时, 如果已经存在结果文件则跳过
                back_file_path = f"{self.result_dir}/{item['unique_key']}/back_trans.json"
                if CommonUtil.file_exist(back_file_path):
                    continue
            self.trans_queue.put(item)

        for _ in self.trans_gpus:
            self.trans_queue.put(None)

    def run(self):
        gpus = torch.cuda.device_count()
        assert gpus >= 2
        self._init_handler()
        self._init_trans_queue()
        print(f"data_list_size = {len(self.source_list)}")

        trans_process_list = []
        back_process_list = []
        for i in self.trans_gpus:
            # 创建trans进程
            process1 = mp.Process(target=self._run_translate, args=(i,))
            process1.start()
            trans_process_list.append(process1)
        for j in self.back_gpus:
            # 创建back进程
            process2 = mp.Process(target=self._run_back_trans, args=(j,))
            process2.start()
            back_process_list.append(process2)

        for i in range(len(trans_process_list)):
            trans_process_list[i].join()

        # 发送结束信号到第二步, 因为步骤2有多个进程，每个进程都需要单独收到一个 None 才能正确退出.
        for _ in self.back_gpus:
            self.back_queue.put(None)

        for j in range(len(back_process_list)):
            back_process_list[j].join()

        print("All data processed.")

    def _run_translate(self, gpu_id):
        """
        翻译、编译
        """
        # 设置GPU环境变量
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        this_handler = self.handler[gpu_id]

        while True:
            item = self.trans_queue.get()
            if item is None:  # 检测结束信号
                break
            self._init_dir(item['unique_key'])
            generate_list = this_handler.generate_and_check(item['informal_statement'])
            item['translate_list'] = generate_list
            print(f"translate_list.size = {len(item['translate_list'])}")

            self._set_dict_data(item['unique_key'], 'translate_list', generate_list)
            self._save_trans_data(item)
            self.back_queue.put(item)  # 将结果放入队列

        # self.back_queue.put(None)  # 发送结束信号

    def _run_back_trans(self, gpu_id):
        """
        反翻译 & 比对
        """
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        this_handler = self.handler[gpu_id]
        while True:
            item = self.back_queue.get()
            if item is None:  # 检测结束信号
                break
            data_list = [{
                'informal_statement': item['informal_statement'],
                'formal_statement': i
            } for i in item['translate_list']]
            valid_list = this_handler.back_compare_filter(data_list)
            valid_formal_list = [i['formal_statement'] for i in valid_list]
            print(f"valid_formal_list.size = {len(valid_formal_list)}")

            self._set_dict_data(item['unique_key'], 'back_trans_list', valid_formal_list)
            self._save_back_trans_data(item)

    def _init_dir(self, file_name):
        temp_dir = f"{self.result_dir}/{file_name}"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

    def _save_trans_data(self, item):
        CommonUtil.write_to_json_file(self._gen_file_path(item), dict(self.shared_dict[item['unique_key']]))

    def _save_back_trans_data(self, item):
        CommonUtil.write_to_json_file(self._gen_file_path(item, 'back'), dict(self.shared_dict[item['unique_key']]))

    def _gen_file_path(self, item, type_name='trans'):
        return f"{self.result_dir}/{item['unique_key']}/translate.json" if type_name == "trans" \
            else f"{self.result_dir}/{item['unique_key']}/back_trans.json"
