# -*- coding: utf-8 -*-
################################################################################

################################################################################
import requests


class HttpUtil(object):

    @staticmethod
    def get(url, params=None, headers=None):
        """
        发送 GET 请求

        :param url: 请求的 URL
        :param params: 查询参数，字典类型
        :param headers: 请求头，字典类型
        :return: 响应的 JSON 数据（如果响应内容为 JSON），否则返回响应对象
        """
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()  # 检查请求是否成功
            return response.json() if response.headers.get('Content-Type') == 'application/json' else response
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
        except Exception as err:
            print(f"An error occurred: {err}")

    @staticmethod
    def post(url, data=None, json=None, headers=None):
        """
        发送 POST 请求

        :param url: 请求的 URL
        :param data: 表单数据，字典类型
        :param json: JSON 数据，字典类型
        :param headers: 请求头，字典类型
        :return: 响应的 JSON 数据（如果响应内容为 JSON），否则返回响应对象
        """
        try:
            response = requests.post(url, data=data, json=json, headers=headers, timeout=30)
            response.raise_for_status()  # 检查请求是否成功
            return response.json() if response.headers.get('Content-Type') == 'application/json' else response
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
        except Exception as err:
            print(f"An error occurred: {err}")


