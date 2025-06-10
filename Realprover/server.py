from flask import Flask, request, jsonify
from flask_cors import CORS

from manager.service import BaseService

from util import StringUtil, LogUtil

app = Flask(__name__)
log_util = LogUtil()

base_service = BaseService()


@app.route('/step-prover', methods=['POST'])
def prover():
    data = request.get_json()
    # check_result, message = StringUtil.check_param_valid(params=data)
    # log_util.info(f"check_result = {check_result}, message = {message}")
    # if not check_result:
    #     return jsonify(StringUtil.gen_fail_data(message)), 400

    # 判断是否传入了正确的字段
    if not data or 'formal_statement' not in data:
        log_util.info(f"Missing param formal_statement")
        return jsonify(StringUtil.gen_fail_data('Missing param \'formal_statement\'')), 400

    ret = base_service.single_run(formal_statement=data['formal_statement'])

    return jsonify(StringUtil.gen_success_data(data=ret)), 200


@app.route('/test', methods=['GET'])
def test():
    return StringUtil.gen_success_data({'data': 'stepprover is ok'}), 200


CORS(app)
# 启动Web服务
if __name__ == '__main__':
    print('start server on 8080')
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
