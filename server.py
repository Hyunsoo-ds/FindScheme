import os
import subprocess
from glob import glob
from flask import Flask, request
import time
import hashlib
import multiprocessing
import functools
import logging

SERVER_ADDR =  "192.168.6.77"  # 현재 자신의 ip 주소에 맞게 주소를 설정해 해줘야지 서버가 정상적으로 작동 됩니다

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True

@app.route("/redirect/<hash>")
def redirect(hash):
    temp = app.config["shm"][hash]
    temp["redirect"] = True
    app.config["shm"][hash] = temp
    print(request.headers)
    return "THIS IS A REDIRECT PAGE...!!!"
    

@app.route("/fetch/<hash>")
def fetch(hash):
    res = "<html><script>\n"
    for jsif in app.config["shm"][hash]["addJsIfs"]:
        for method in app.config["shm"][hash]["methods"]:
            data = (str(time.time())+jsif+method).encode()
            new_hash = hashlib.sha1(data).hexdigest()
            app.config["shm"][new_hash] = {
            "deeplink": app.config["shm"][hash]["deeplink"],
            "param": app.config["shm"][hash]["param"],
            "jsif": jsif,
            "method": method
            } 
            res += "try{fetch(`/isfunc/%s?ret=`+window.%s.%s);}catch{}\n" % (new_hash, jsif, method)
    res += "</script></html>"
    return res
@app.route("/isfunc/<hash>")
def isfunc(hash):
    if request.args.get('ret') != "undefined":
        app.config["shm"]["jsif_func"] += [hash]
    return ""
@app.route("/exec/<hash>")
def exec(hash):
    jsif = app.config["shm"][hash]["jsif"]
    method = app.config["shm"][hash]["method"]
    new_hash = hashlib.sha1((str(time.time())+jsif+method).encode()).hexdigest()
    app.config["shm"][new_hash] = {"jsif": jsif, "method": method}
    res = "<html><script>try{fetch(`/return/%s?ret=`+window.%s.%s());}catch(e){fetch(`/return/%s?err=`+e)}</script></html>" % (new_hash, jsif, method, new_hash)
    return res
@app.route("/return/<hash>")

def run_server(shm):
    app.config["shm"] = shm
    app.run(host=SERVER_ADDR, port=8012)


if __name__ == "__main__":
    manager = multiprocessing.Manager()
    shm = manager.dict()
    p = multiprocessing.Process(target=functools.partial(run_server, shm))
    p.start()
  