import re
import json
from openai import AsyncOpenAI
import conf.config


class BackHttpHandler(object):
    """
    lean 语言 => 自然语言   &&  比对informal_statement
    """

    def __init__(self):
        """

        """
        # self.model_name = 'deepseek-ai/DeepSeek-V2.5'
        self.model_name = conf.config.MODEL_CONFIG['compare']  # 翻译和反翻译都使用此模型

    async def back_compare_filter(self, data_list):
        """

        """
        if len(data_list) == 0:
            return []

        for index, row_data in enumerate(data_list):
            print(f"back_compare_filter_index = {index}")
            row_data['back_translate'] = await self.get_back_tran(row_data)
            same_str = await self.compare(row_data)
            row_data['same_result'] = same_str

        result_list = [row for row in data_list if row['same_result'] == 'same']
        return result_list

    async def get_back_tran(self, data):
        sys_prompt = 'Convert the formal statement into natural language: '
        prompt = data['formal_statement']
        message_str = json.dumps([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ])
        messages = json.loads(message_str)
        # back_tran_str = self.execute_request(messages=messages)
        back_tran_str = await self.request_model(messages=messages)
        # TODO 生成的数据是否需要处理呢
        data['back_translate'] = back_tran_str
        return back_tran_str

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
        generate_data = await self.request_model(messages=messages)
        ret = self.extract_bold_text(generate_data)
        print("***check-same-ret***: %s" % ret)
        data['same_result'] = ret
        return ret

    async def request_model(self, messages):
        """
        请求大模型
        """
        nil_client = AsyncOpenAI(
            base_url=conf.config.NIM_CONFIG['url'],
            api_key=conf.config.NIM_CONFIG['key'],
            timeout=600
        )
        response = await nil_client.chat.completions.create(
            model=self.model_name,
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
        print("*** request_model_response result ***")
        print(result)
        return result

    def extract_bold_text(self, output):
        # 使用正则表达式提取**之间的内容
        match = re.search(r'\|\|(.*?)\|\|', output)
        if match:
            return match.group(1)
        return 'null'
