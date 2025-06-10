import time
import aiohttp
import asyncio
import conf.config
from util import HttpUtil, StringUtil


class ProverHandler(object):
    """
    stepprover: 通过API接口调用
    """

    def __init__(self):
        """

        """
        self.request_url = conf.config.API_CONFIG['step_prover']

    def batch_gen_proof(self, formal_statement_list):
        return asyncio.run(self._batch_run_request(formal_statement_list))

    async def _batch_run_request(self, formal_statement_list):
        """

        """
        ret = {}
        # 创建一个 aiohttp 客户端会话

        max_workers = min(len(formal_statement_list), conf.config.THREAD_CONFIG['proof'])
        max_workers = 1
        connector = aiohttp.TCPConnector(limit=max_workers)  # 设置最大并发连接数
        async with aiohttp.ClientSession(connector=connector) as session:
            # 创建任务列表
            tasks = [self._send_post_request(session, data) for data in formal_statement_list]

            # 并发运行所有任务并收集结果
            results = await asyncio.gather(*tasks)

        # 输出结果
        for i, result in enumerate(results):
            print(f"Request {i + 1} result: {result}")
            ret[i] = result['data'] if isinstance(result, dict) else result
        return ret

    async def _send_post_request(self, session, data):
        try:
            json_data = self._gen_request_param(data)
            async with session.post(self.request_url, json=json_data) as response:
                return await response.json()
        except Exception as e:
            return f"Error: {e}"

    def get_one_prover_result(self, formal_statement):
        """

        """
        data = self._gen_request_param(formal_statement)
        res_json = HttpUtil.post(url=self.request_url, json=data)

        return res_json

    def _gen_request_param(self, formal_statement):
        params = {
            'timestamp': time.time(),
            'formal_statement': formal_statement,
        }
        params['sign'] = StringUtil.gen_sign(params)
        return params
