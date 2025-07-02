from flask import Flask, request, jsonify
from worker import PremiseSelector
from util import RequestUtil

app = Flask(__name__)

premise_selector = PremiseSelector()
premise_selector.init_model()

@app.route('/retrieve_premises', methods=['POST'])
def to_formal_statement():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify(RequestUtil.gen_fail_data('Missing param \'query\'')), 400
    num = data.get('num', 5)
    related_theorems = premise_selector.retrieve(data['query'], num=num)
    return jsonify(RequestUtil.gen_success_data(related_theorems)), 200

# Start http server
if __name__ == '__main__':
    print('start server on 8080')
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
