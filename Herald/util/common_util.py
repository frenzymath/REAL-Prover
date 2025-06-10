# -*- coding: utf-8 -*-
################################################################################

################################################################################
"""
This module provide string process service.

"""
import json
import os
from datetime import datetime


class CommonUtil(object):
    """
    通用处理类
    """
    @staticmethod
    def load_json(config_file):
        """load json"""
        params = None
        if os.path.exists(config_file):
            f = open(config_file)
            params = json.load(f)
        else:
            raise Exception('Config Error')
        return params

    @staticmethod
    def write_to_json_file(file_path, json_data, ensure_ascii=False):
        """

        """
        with open(file_path, 'w', encoding='utf-8') as dump_f:
            json.dump(json_data, dump_f, ensure_ascii=ensure_ascii)

    @staticmethod
    def write_json_list_to_file(file_path, data_list):
        """

        :param file_path:
        :param data_list:
        :return:
        """
        with open(file_path, mode='w', encoding='utf-8') as f:
            for index, data in enumerate(data_list):
                json.dump(data, f, ensure_ascii=False)
                if index < len(data_list) - 1:
                    f.write('\n')

    @staticmethod
    def read_json_list(file_path):
        """

        :param file_path:
        :return:
        """
        data_list = []
        with open(file_path, mode='r') as f:
            for line in f:
                if line:
                    data_list.append(json.loads(line))
        return data_list

    @staticmethod
    def read_list(file_path, skip_first=True):
        """

        :param skip_first:
        :param file_path:
        :return:
        """
        data_list = []
        with open(file_path, mode='r') as fr:
            if skip_first:
                next(fr)
            for line in fr:
                if line:
                    data_list.append(line)
        return data_list

    @staticmethod
    def write_list(file_path, lines_list):
        """

        :param file_path:
        :param lines_list:
        :return:
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines_list)

    @staticmethod
    def build_key_to_data(data_list, key_name, value_key=''):
        """

        :param data_list:
        :param key_name:
        :param value_key:
        :return:
        """
        ret = {}
        for row_data in data_list:
            row_value = row_data[key_name]
            if row_value not in ret:
                ret[row_value] = row_data[value_key] if value_key else row_data
        return ret

    @staticmethod
    def build_key_to_list(data_list, key_name):
        """

        :param data_list:
        :param key_name:
        :return:
        """
        ret = {}
        for row_data in data_list:
            row_value = row_data[key_name]
            if row_value not in ret:
                ret[row_value] = []
            ret[row_value].append(row_data)
        return ret

    @staticmethod
    def get_date_time():
        """

        :return:
        """
        return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    @staticmethod
    def file_exist(file_path):
        """

        :param file_path:
        :return:
        """
        return os.path.isfile(file_path)

    @staticmethod
    def split_list(lst, chunk_size):
        """
        将列表拆分成多个小列表，每个小列表包含chunk_size个元素。

        :param lst: 待拆分的列表
        :param chunk_size: 每个小列表包含的元素数量
        :return: 包含多个小列表的列表
        """
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

    @staticmethod
    def print(string):
        print(f"{CommonUtil.get_date_time()}: {string}")



