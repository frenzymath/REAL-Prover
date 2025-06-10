import asyncio
import multiprocessing as mp

from service.handler import TranHandler, BackHttpHandler
from service import ParallelService


class ParallelHttpService(ParallelService):
    """
    翻译使用http接口请求
    """

    def __init__(self, source_file, result_dir, re_run=False,
                 trans_gpus=None, back_process_count=8):
        super().__init__(source_file=source_file, result_dir=result_dir, re_run=re_run, trans_gpus=trans_gpus,
                         back_gpus=[])

        self.back_process_count = back_process_count
        self.back_handler = {}

    def _init_handler(self):
        for i in self.trans_gpus:
            self.handler[i] = TranHandler()
        for j in range(self.back_process_count):
            self.back_handler[j] = BackHttpHandler()

    def run(self):
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

        # 创建back进程
        for j in range(self.back_process_count):
            process2 = mp.Process(target=self._run_back_trans, args=(j,))
            process2.start()
            back_process_list.append(process2)

        for i in range(len(trans_process_list)):
            trans_process_list[i].join()

        # 发送结束信号到第二步, 因为步骤2有多个进程，每个进程都需要单独收到一个 None 才能正确退出.
        for _ in range(self.back_process_count):
            self.back_queue.put(None)

        for j in range(len(back_process_list)):
            back_process_list[j].join()

        print("All data processed.")

    def _run_back_trans(self, process_index=0):
        """
        反翻译 & 比对
        """
        this_handler = self.back_handler[process_index]
        while True:
            item = self.back_queue.get()
            if item is None:  # 检测结束信号
                break
            data_list = [{
                'informal_statement': item['informal_statement'],
                'formal_statement': i
            } for i in item['translate_list']]
            print("start_back_compare_filter")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            valid_list = []
            try:
                valid_list = loop.run_until_complete(this_handler.back_compare_filter(data_list))
            except RuntimeError as e:
                if "Event loop is closed" not in str(e):
                    raise  # 只忽略特定的 RuntimeError，其他的仍然抛出
            finally:
                loop.close()

            valid_formal_list = [i['formal_statement'] for i in valid_list]
            print(f"valid_formal_list.size = {len(valid_formal_list)}")

            self._set_dict_data(item['unique_key'], 'back_trans_list', valid_formal_list)
            self._save_back_trans_data(item)
