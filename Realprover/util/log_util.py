import logging
import os

import logging
import os


class LogUtil:
    _instance = None  # 类变量，用于保存唯一实例

    def __new__(cls, *args, **kwargs):
        """保证只创建一个实例"""
        if not cls._instance:
            # 创建唯一的实例
            cls._instance = super(LogUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_file='logs/app.log', log_level=logging.DEBUG, log_format=None):
        """初始化日志工具类"""
        if hasattr(self, '_initialized'):  # 避免重复初始化
            return

        # 标记初始化已经完成
        self._initialized = True

        # 默认日志格式
        if log_format is None:
            log_format = '%(asctime)s - %(levelname)s - %(message)s'

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        # 创建日志输出格式
        formatter = logging.Formatter(log_format)

        # 创建文件处理器
        if not os.path.exists(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file))

        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)

        # 创建控制台输出处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # 添加处理器到日志器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message):
        """记录调试级别的日志"""
        self.logger.debug(message)

    def info(self, message):
        """记录信息级别的日志"""
        self.logger.info(message)

    def warning(self, message):
        """记录警告级别的日志"""
        self.logger.warning(message)

    def error(self, message):
        """记录错误级别的日志"""
        self.logger.error(message)

    def critical(self, message):
        """记录严重错误级别的日志"""
        self.logger.critical(message)

    def exception(self, message):
        """记录异常信息"""
        self.logger.exception(message)


