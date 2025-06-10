import conf.config


class ModelManage(object):

    @staticmethod
    def contain_local(model_list):
        """

        """
        return conf.config.MODEL_TYPE_LOCAL in model_list

    @staticmethod
    def contain_gemini(model_list):
        """

        """
        return conf.config.MODEL_TYPE_GEMINI in model_list
