# -*- coding: utf-8 -*-
################################################################################
#
# Copyright (c) 2018 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
This module provide string process manager.

"""
import os
import hashlib
import random
import time

import conf.config


class StringUtil(object):
    """
    字符串处理有关
    """

    @staticmethod
    def check_param_valid(params):
        """
        参数校验
        :param params:
        :return:
        """
        if not params or 'timestamp' not in params:
            return False, "Missing param 'timestamp'"

        if not StringUtil.check_timestamp_valid(params['timestamp']):
            return False, "timestamp timeout"

        if not StringUtil.check_api_token(params=params):
            return False, "sign check fail"

        return True, ''



    @staticmethod
    def check_api_token(params):
        """
        参数校验
        :param params:
        :return:
        """
        check_str = f"{conf.config.SALT}-{params['timestamp']}"
        return StringUtil.get_str_md5(check_str) == params['sign']

    @staticmethod
    def check_timestamp_valid(timestamp):
        """
        校验timestamp是否超时
        :param timestamp:
        :return:
        """
        return (time.time() - int(timestamp)) < conf.config.EXPIRE_TIME

    @staticmethod
    def gen_sign(params):
        """
        参数校验
        :param params:
        :return:
        """
        check_str = f"{conf.config.SALT}-{params['timestamp']}"
        return StringUtil.get_str_md5(check_str)

    @staticmethod
    def get_str_md5(ustr):
        """
        获取字符串md5
        :param ustr:
        :return:
        """
        m2 = hashlib.md5()
        m2.update(ustr.encode('utf-8'))
        return m2.hexdigest()

    @staticmethod
    def generate_shortcut():
        """

        :return:
        """
        temp_str = StringUtil.gen_random_str(16)
        temp_md5 = StringUtil.get_str_md5(temp_str)
        return temp_md5[0:8]

    @staticmethod
    def gen_random_str(str_len=6):
        """
        生成随机字符串，最长不超过62位
        :return:
        """
        if str_len > 62:
            str_len = 62
        return ''.join(random.sample('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', str_len))

    @staticmethod
    def gen_success_data(data):
        return {
            'error': False,
            'msg': '',
            'data': data
        }

    @staticmethod
    def gen_fail_data(message):
        return {
            'error': True,
            'msg': message,
            'data': {}
        }
