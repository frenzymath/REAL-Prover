from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
import re
import json
from openai import AsyncOpenAI
import asyncio
import concurrent.futures
import conf.config


class BackHandler(object):
    """
    lean 语言 => 自然语言   &&  比对informal_statement
    """
    def __init__(self):
        """

        """
        self.model = None
        self.bt_tokenizer = None
        self.sampling_params = None
        self.tp_size = 1

        # self._init_model()


    def _init_model(self):
        if self.model is None:
            self.bt_tokenizer = AutoTokenizer.from_pretrained(conf.config.MODEL_CONFIG['back_trans'], use_fast=False,
                                                              trust_remote_code=True)
            self.model = LLM(
                model=conf.config.MODEL_CONFIG['back_trans'], tensor_parallel_size=self.tp_size, trust_remote_code=True,
                dtype="bfloat16")

    def release_model(self):
        self.model = None
        self.bt_tokenizer = None

    def _init_sampling_params(self):
        if self.sampling_params is None:
            self.sampling_params = SamplingParams(
                temperature=0.1,
                max_tokens=1024,
                stop=['[UNUSED_TOKEN_146]', '[UNUSED_TOKEN_145]', '<|im_end|>'])

    def get_query_backtrans_intern(self, problem):
        output = problem['formal_statement']
        output = '[UNUSED_TOKEN_146]user\nConvert the formal statement into natural language:\n```lean\n' + output + '\n```[UNUSED_TOKEN_145]\n[UNUSED_TOKEN_146]assistant\n'
        problem['prompt_backtranslate'] = output
        return problem

    def back_compare_filter_old(self, data_list):
        """
        反翻译并比对，失败的过滤掉
        """
        result_list = []
        for index, row_data in enumerate(data_list):
            print('back_compare: index = %s' % index)
            row_data['back_translate'] = self.get_back_tran(row_data)
            same_str = asyncio.run(self.compare(row_data))
            row_data['same_result'] = same_str
            if same_str == "same":
                result_list.append(row_data)
        return result_list

    def back_compare_filter(self, data_list):
        """
        反翻译并比对，失败的过滤掉
        """
        if len(data_list) == 0:
            return []
        self._init_model()
        for row_data in data_list:
            row_data['back_translate'] = self.get_back_tran(row_data)

        def process_row(row_data):
            print(f"back_compare: index = {data_list.index(row_data)}")
            # row_data['back_translate'] = self.get_back_tran(row_data)
            same_str = asyncio.run(self.compare(row_data))
            row_data['same_result'] = same_str
            return row_data if same_str == "same" else None

        max_workers = min(len(data_list), conf.config.THREAD_CONFIG['same_check'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_row, data_list))

        # 过滤掉 None 值，仅保留匹配的行
        result_list = [row for row in results if row is not None]
        return result_list

    def get_back_tran(self, data):
        self._init_sampling_params()
        data = self.get_query_backtrans_intern(data)
        outputs = self.model.generate(data['prompt_backtranslate'], sampling_params=self.sampling_params)
        print('***outputs***')
        print(outputs)
        result = outputs[0].outputs[0].text
        return result



    def get_query_nil_apichat(self, problem):
        sys_prompt = 'Please check the following two math problems are the same or different? Please consider each statement in the two problems; they are different if any statement is different. Please point out any differences you found. Please reply ||same|| or ||different|| in the final sentence with "||" format.'
        problem_origin = problem['informal_statement']
        problem_back = problem['back_translate']
        prompt = 'Problem 1:\n' + problem_origin + '\nProblem 2:\n' + problem_back
        problem["prompt"] = json.dumps([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ])
        return problem

    async def compare(self, data):
        """
        返回值为 same or different
        """
        data = self.get_query_nil_apichat(data)
        messages = json.loads(data['prompt'])
        nil_client = AsyncOpenAI(
            base_url=conf.config.NIM_CONFIG['url'],
            api_key=conf.config.NIM_CONFIG['key'],
            timeout=600
        )
        response = await nil_client.chat.completions.create(
            model=conf.config.MODEL_CONFIG['compare'],
            messages=messages,
            max_tokens=1024,
            temperature=0.01,
            top_p=0.7,
            extra_body={'repetition_penalty': 1},
            stream=False
        )
        if not response or not response.choices:
            return 'null'
        result = response.choices[0].message.content
        print("***check-same-response result***")
        print(result)

        ret = self.extract_bold_text(result)
        print("***check-same-ret***: %s" % ret)
        return ret


    def extract_bold_text(self, output):
        # 使用正则表达式提取**之间的内容
        match = re.search(r'\|\|(.*?)\|\|', output)
        if match:
            return match.group(1)
        return 'null'
