import uuid
import os
import gc
import torch

from service.handler import TranHandler, BackHandler, ProverHandler
from util import CommonUtil


class PipelineService(object):
    """
    服务
    """

    def __init__(self, result_dir):
        """

        """
        self.result_dir = result_dir
        self.tran_handler = None
        self.back_handler = None
        self.proof_handler = None
        if result_dir is None:
            self.result_dir = f"./data_result/{CommonUtil.get_date_time(), uuid.uuid4()}"
        self._init_dir()

        self.informal_statement = ""
        self.formal_list_after_validate = []  # 生成并编译后的
        self.formal_list_after_compare = []  # 反翻译比对通过的
        self.prove_detail_dict = {}  # proof详情信息
        self.result_list = []  # statement和proof的成对

    def _init_dir(self):
        self.tran_file_path = f"{self.result_dir}/translate.json"
        self.prove_file_path = f"{self.result_dir}/prove_info.json"

        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

    def _init_handler(self):
        if self.tran_handler is None:
            self.tran_handler = TranHandler()
        if self.back_handler is None:
            self.back_handler = BackHandler()
        if self.proof_handler is None:
            self.proof_handler = ProverHandler()

    def run(self, informal_statement, with_proof=True):
        self.informal_statement = informal_statement
        self._init_handler()

        if CommonUtil.file_exist(self.tran_file_path):
            saved_data = CommonUtil.load_json(self.tran_file_path)
            self.formal_list_after_validate = saved_data['formal_list_after_validate']
            self.formal_list_after_compare = saved_data['formal_list_after_compare']
        else:

            self._run_translate()
            self._run_back_trans()
            self._save_tran_data()

        if with_proof:
            self._run_proof()
            self._save_proof_data()

    def _run_translate(self):
        """
        翻译、编译
        """
        generate_list = self.tran_handler.generate_and_check(self.informal_statement)
        self.tran_handler.release_model()
        self._gc_collect()

        print('generate finished: data_list_size = %s' % len(generate_list))
        self.formal_list_after_validate = generate_list
        print(f"formal_list_after_validate_size = {len(generate_list)}")

    def _run_back_trans(self):
        """
        反翻译 & 比对
        """
        data_list = [{
            'informal_statement': self.informal_statement,
            'formal_statement': i
        } for i in self.formal_list_after_validate]
        valid_list = self.back_handler.back_compare_filter(data_list)
        self.back_handler.release_model()
        self._gc_collect()
        self.formal_list_after_compare = [i['formal_statement'] for i in valid_list]
        print(f"formal_list_after_compare_size = {len(valid_list)}")

    def _run_proof(self):
        self.prove_detail_dict = self.proof_handler.batch_gen_proof(self.formal_list_after_compare)
        for index, prove_detail in self.prove_detail_dict.items():
            if "formal_proof" in prove_detail:
                self.result_list.append({
                    'formal_statement': self.formal_list_after_compare[index],
                    'formal_proof': prove_detail['formal_proof']
                })


    def _gc_collect(self):
        gc.collect()  # 调用垃圾回收
        torch.cuda.empty_cache()  # 清理 GPU 缓存

    def _save_tran_data(self):
        CommonUtil.write_to_json_file(self.tran_file_path, self._build_save_data())

    def _save_proof_data(self):
        CommonUtil.write_to_json_file(self.prove_file_path, self._build_save_data(True))

    def _build_save_data(self, with_proof=False):
        """

        """
        save_data = {
            'informal_statement': self.informal_statement,
            'formal_list_after_validate': self.formal_list_after_validate,
            'formal_list_after_compare': self.formal_list_after_compare
        }
        if with_proof:
            save_data['prove_detail_dict'] = self.prove_detail_dict
            save_data['result_list'] = self.result_list
        return save_data
