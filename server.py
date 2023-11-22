import multiprocessing
import functools
import time
import os
import requests
from init import SERVER_ADDR, USERNAME, AWS_url
from flask import Flask, request, render_template


app = Flask(__name__)

@app.route('/t3')
def test2():
    return render_template('test2.html')

@app.route('/test-res2', methods=['POST'])
def result():

    connect = app.config["JSItest"]
    APKNAME = connect["APKNAME"]
    deeplink = connect["deeplink"]
    file_name = f'./JSI_test/Result_{APKNAME}.txt'
    
    
    data_from_client = str(request.json.get('data')).replace('<br>',('\n'))
    write_data = f"DEEPLINK : {deeplink}\n{data_from_client}\n"

    if os.path.isfile(file_name):
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(write_data)
    else:
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(write_data)
    print(data_from_client)


    res = divide_info(data_from_client)
    res['APKNAME'] = APKNAME
    res['User'] = USERNAME
    res['redir_url'] = deeplink
    send_to_aws(AWS_url,res)

    connect["connect"] = True
    app.config["JSItest"] = connect

    return 'dd'

@app.route("/redirect/<hash>")
def redirect(hash):
    temp = app.config["shm"][hash]
    temp["redirect"] = True
    app.config["shm"][hash] = temp
    print(request.headers)
    return "THIS IS A REDIRECT PAGE...!!!"

def divide_info(data_from_client):
    result = {}
    lines = data_from_client.split('\n')
    interface = None
    methods = []

    for line in lines:
        line = line.strip()
        if line.startswith("APPinterface list"):
            interface = "APPinterface"
            methods = []
        elif line.startswith("Method"):
            if interface:
                result[interface] = methods
            interface = line.replace("Method ", "").strip()
            methods = []
        elif line and not line.startswith("="):
            methods.extend(line.split())
    if interface:
        result[interface] = methods
    return result

def send_to_aws(url,result):

    response = requests.post(url, json=result)

    if response.status_code == 200:
        data = response.json()
        print(data)
    else:
        print('Failed to send data to the server')


def server_start():
    manager = multiprocessing.Manager()
    shm = manager.dict()
    JSItest = manager.dict()
    JSItest["connect"]=False
    p = multiprocessing.Process(target=functools.partial(run_server, shm, JSItest))
    p.start()

    time.sleep(3)

    
    return p, shm, JSItest

def run_server(shm,JSItest):
    app.config["shm"] = shm
    app.config["JSItest"] = JSItest
    app.run(host=SERVER_ADDR, port=8012)

