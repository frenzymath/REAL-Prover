class RequestUtil(object):
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
