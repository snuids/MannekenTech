from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__)

@app.route('/api/v1/status',methods=['GET'])
def status():
    return jsonify({'status':'ok','version':'1'})

app.run()
