from vllm import LLM, SamplingParams
import re
import json
import tempfile
import traceback
import subprocess
from typing import Optional
import concurrent.futures

import conf.config
from util import profiler, CommonUtil


class TranHandler(object):
    """
    自然语言 => lean 语言
    lean代码编译检测
    """

    def __init__(self, gpus=1):
        """

        """
        self.model = None
        self.name = 'textbook_exercise'
        self.model_id = 'Herald'
        self.lean_path = conf.config.LEAN_TEST_PATH

        self.gpus = gpus

        # self._init_model()

    def _init_model(self):
        if self.model is None:
            # self.model = LLM(model=conf.config.TRAN_MODEL_PATH, max_num_batched_tokens=8192, seed=1,
            #                  trust_remote_code=True)
            self.model = LLM(
                model=conf.config.MODEL_CONFIG['trans'],
                tensor_parallel_size=self.gpus,
                trust_remote_code=True,
                dtype='bfloat16',
                # gpu_memory_utilization=0.9,
            )

    def release_model(self):
        self.model = None


    def generate_and_check(self, informal_statement):
        """
        多线程处理
        """
        statement_list = self.generate(informal_statement)
        # return statement_list
        return self.batch_validate_item(statement_list)

    def generate(self, informal_statement):
        if self.model is None:
            self._init_model()

        prompt = self.get_query(informal_statement, self.name, self.model_id)
        output = self.model.generate(prompt, sampling_params=self._build_sampling_param(
            conf.config.TRAN_CONFIG['sampling_params']))
        outputs = output[0].outputs
        generated = [output.text for output in outputs]
        generated = self.process(generated, self.model_id)
        print('*** generated *** size = %s' % len(generated))
        # print(json.dumps({'generated': generated}, indent=4))
        return generated


    def batch_generate(self, data_list, sampling_params=None):
        """

        """
        if self.model is None:
            profiler.start('init_model')
            self._init_model()
            profiler.stop('init_model')
        prompt_list = [self.get_query(i['informal_statement'], self.name, self.model_id) for i in data_list]
        if not sampling_params:
            sampling_params = conf.config.TRAN_CONFIG['sampling_params']

        profiler.start(f"generate_{len(prompt_list)}")
        gen_result_list = self.model.generate(prompt_list, sampling_params=self._build_sampling_param(sampling_params))
        profiler.stop(f"generate_{len(prompt_list)}")
        CommonUtil.print(f"gen_result_list.size = {len(gen_result_list)}")
        for index, data in enumerate(data_list):
            data['generate_informal_statement_list'] = [self.process(output.text) for output in gen_result_list[index].outputs]
        return data_list

    def _build_sampling_param(self, sampling_params):
        """

        """
        return SamplingParams(
            n=sampling_params['n'],
            max_tokens=sampling_params['max_tokens'],
            temperature=sampling_params['temperature'],
            top_p=sampling_params['top_p'],
        )

    def get_query(self, informal_statement: str, name: str, model_id='Herald') -> str:
        template = """Please translate the natural language statement to Lean4 code with the header. Do not generate any notations.
        **Name**
        {name}
        **Informal statement**
        {informal_statement}
        """
        msgs = [
            {'role': 'system', 'content': 'You are an expert at Lean 4 and Mathematics.'},
            {'role': 'user', 'content': template.format(
                name=name,
                informal_statement=informal_statement)}
        ]
        if model_id == 'Herald':
            return self.chat_template_to_prompt(msgs, 'deepseek')
        elif model_id == 'InternLM':
            return self.chat_template_to_prompt(msgs, 'internlm')
        elif model_id == 'TheoremLlama':
            return self.chat_template_to_prompt(msgs, 'thmllm')
        else:
            raise NotImplementedError

    def process(self, generated: str, model_id='Herald') -> str:
        if model_id == 'Herald':
            return generated
        elif model_id in ['InternLM', 'TheoremLlama']:
            new_output = re.sub(r'^\s*-- .*$', '', generated, flags=re.MULTILINE)
            lean_code_pattern = r'```lean\n(.*?)(?:\n```|$)'  # Match to the end if not finished
            matches = re.findall(lean_code_pattern, new_output, re.DOTALL)
            new_output = '\n'.join(matches)
            new_output = re.sub(r'\n+', '', new_output).strip()
            new_output = re.sub(r'-+', '', new_output).strip()
            new_output = re.sub(r':=.*', ':= sorry', new_output)
            return new_output
        else:
            raise NotImplementedError

    def chat_template_to_prompt(self, prompt_list, model='default'):
        result = ""
        total_step = len(prompt_list)
        for i, message in enumerate(prompt_list):
            if model == 'internlm':
                result += ('<|im_start|>' + message['role'] +
                           '\n' + message['content'])
                if i + 1 != total_step:
                    result += '<|im_end|>\n'
                elif message['role'] == 'user':
                    result += '<|im_end|>\n<|im_start|>assistant\n'

            elif model == 'deepseek':
                if message['role'] == 'user':
                    result += 'User:' + message['content'] + '\n\n'
                elif message['role'] == 'assistant':
                    result += 'Assistant' + message['content'] + '<｜end▁of▁sentence｜>'
                elif message['role'] == 'system':
                    result += message['content'] + '\n\n'
                if i + 1 == total_step and message['role'] == 'user':
                    result += 'Assistant:'

            elif model == 'thmllm':
                result += ('<|start_header_id|>' + message['role'] + '<|end_header_id|>' +
                           message['content'] + '<|eot_id|>')
                if i + 1 == total_step and message['role'] == 'user':
                    result += '<|start_header_id|>assistant<|end_header_id|>'
            else:
                raise NotImplementedError
        return result


    def validate(self, code_string, header='', timeout=120) -> tuple[Optional[bool], str]:
        validation = True
        try:
            result = self.validate_one_lean_codestring(code_string, header, timeout)
            result_json = json.loads(result)
            if result_json.get("messages"):
                for msg in result_json.get("messages"):
                    if msg.get("severity") == "error":
                        validation = False
        except Exception as e:
            print(e)
            validation, result = False, str(e)
        return validation, result

    def validate_one_lean_codestring(self, code_string, header, timeout=300):
        command = dict(cmd=header + '\n' + code_string)
        print('command = %s' % command)
        message_str = json.dumps(command, ensure_ascii=False)
        lean_path = self.lean_path
        try:
            with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as temp_file:
                temp_file.write(message_str + "\r\n\r\n")
                temp_file.seek(0)
                outputs = subprocess.run(
                    [conf.config.DEFAULT_LAKE_PATH, "exe", 'repl'],
                    stdin=temp_file,
                    capture_output=True,
                    text=True,
                    cwd=lean_path,
                    timeout=timeout,
                    encoding='utf-8'
                )
        except Exception as _:
            CommonUtil.print("validate_one_lean_code error.....")
            error_info = traceback.format_exc()
            print(error_info)
        else:
            return outputs.stdout

    def batch_validate_item(self, statement_list):
        def validate_item(item):
            validation, result = self.validate(item)
            CommonUtil.print('validation = %s' % validation)
            # print('result = %s' % result)
            return item if validation else None

        max_workers = min(len(statement_list), conf.config.THREAD_CONFIG['lean_build'])
        CommonUtil.print('validate_max_workers = %s' % max_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(validate_item, statement_list))

        # 过滤出有效的结果
        return[item for item in results if item is not None]

