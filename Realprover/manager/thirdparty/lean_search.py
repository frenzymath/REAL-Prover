import time
import conf.config
from util import StringUtil, HttpUtil

REQUEST_URL = conf.config.API_CONFIG['lean_search']


class LeanSearch:

    @staticmethod
    def get_related_theorem(query: str):
        data = LeanSearch.get_param(query)
        result = HttpUtil.post(url=REQUEST_URL, json=data)
        return result['data'][0] # type: ignore

    @staticmethod
    def get_param(query: str, num: int=conf.config.NUM_QUERYS):
        params = {
            'timestamp': time.time(),
            'query': query,
            'num': num
        }
        params['sign'] = StringUtil.gen_sign(params)
        return params

    @staticmethod
    def get_related_theorem_batch(queries: list[str]):
        data = [LeanSearch.get_param(q) for q in queries]
        result = HttpUtil.post(url=REQUEST_URL, json=data)
        return result['data'] # type: ignore

if __name__ == '__main__':
    # TODO: write tests here!
    pass
