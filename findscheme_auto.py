import os
import subprocess
from glob import glob
from flask import Flask, request
import time
import hashlib
import multiprocessing
import functools
import logging

SERVER_ADDR =  "192.168.6.48"  # 현재 자신의 ip 주소에 맞게 주소를 설정해 해줘야지 서버가 정상적으로 작동 됩니다
ADB_ADDR = "C:\\adb\\platform-tools\\adb.exe" # adb 사용할 거면 자신의 컴퓨터의 adb.exe의 경로에 맞게 경로를 수정해줘야함!!!

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
            print('Error occured.. While Extracting Deeplink.\n Please Check ADB status!!!')
            print(file_path, line)
            print(e)
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
        print('Parsing Completed:',diretory)
 
    return list(params),list(addURIs),list(UriParses),list(addJsIfs),list(methods)

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
def ret(hash):
    if request.args.get('ret'):
        print(request.args.get('ret'))
    elif request.args.get('err'):
        print(request.args.get('err'))
    return ""
deeplinks = []
def adb(cmd):
    try:
        return subprocess.check_output(
        ADB_ADDR+" %s" % cmd, 
        shell=True,
        stderr=subprocess.STDOUT
        )
    except:
        print('[!]Error Occured while executing deeplink command')
        print('[!]Command:',cmd )
        return b'DEEP'
def open_deeplink(deeplink, sleep_time=3):
    stdout = adb("shell am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d \"%s\"" % (deeplink))
    if b"Error" in stdout:
        time.sleep(0.5)
        print('[->]No Reaction')
        return True
    elif b"Warning" in stdout:
        time.sleep(0.5)
        return True
    elif b'DEEP' in stdout:
        time.sleep(0.5)
        print('[?]Check ADB Status!!')
    else: 
        time.sleep(sleep_time)
 
    adb("shell input keyevent 3")
    
    return False
def run_server(shm):
    app.config["shm"] = shm
    app.run(host=SERVER_ADDR, port=8012)

def analyze_apk(apk_name):
    manager = multiprocessing.Manager()
    shm = manager.dict()

    p = multiprocessing.Process(target=functools.partial(run_server, shm))
    p.start()

    time.sleep(3)

    addr = SERVER_ADDR+":8012"
    apk = f'.\\apks\\{apk_name}'    # APK 경로는 여기에서 설정!!!
    decompile_dir, _ = os.path.splitext(apk)
    print('decompile_dir:',decompile_dir)
    if not os.path.isdir(decompile_dir):
        os.system("java -jar apktool.jar d %s -f --output %s" % (apk, decompile_dir))
    with open(os.path.join(decompile_dir, "AndroidManifest.xml"), encoding="UTF8") as f:
        package = f.read().split("package=\"")[1].split("\"")[0]    
    print ("package name:", package)
    if len(adb("shell pm list packages %s" % package)) == 0:
        if(adb("install %s" % (apk))  == b'DEEP'):
            f2 = open('./error_while_installing.txt','a')
            f2.write(apk_name+', ')
            f2.close()
            return "Fail"
        
    try:
        deeplinks = parse_scheme(decompile_dir)
        params, addURIs, UriParses, addJsIfs, methods = parse_smali(decompile_dir)
    except:
        f2 = open('./error_while_installing.txt','a')
        f2.write(apk_name+', ')
        f2.close()
        return "Fail"

    f = open(f'./output/{apk_name}.txt','w')

    print('[*]deeplink:',deeplinks)
    f.write(f'[*]deeplink:{deeplinks}\n')
    print('[*]params:',params)
    f.write(f'[*]params:{params}\n')
    print('[*]addURIs',addURIs)
    f.write(f'[*]addURIs:{addURIs}\n')
    print('[*]UriParses',UriParses)
    f.write(f'[*]UriParses:{UriParses}\n')
    print('[*]addJsIfs',addJsIfs)
    f.write(f'[*]addJsIfs:{addJsIfs}\n')
    print('[*]methods',methods)
    f.write(f'[*]methods{methods}\n')
    
    blacklist_keywords = {"firebase","mailto","fb","recaptcha","smsto","fbconnect", "http", "kakao", "naver"}

    for deeplink in deeplinks:
        if any(keyword in deeplink for keyword in blacklist_keywords):
            continue
        data = (str(time.time())+deeplink).encode()
        hash = hashlib.sha1(data).hexdigest()
        shm[hash] = {"deeplink": deeplink, "param": "", "redirect": False}
        dl = "{}=http://{}/redirect/{}".format(deeplink, addr, hash)
        print('[*]deeplink:',dl)
        open_deeplink(dl)
        count = 0
        for param in params:
            data = (str(time.time())+deeplink+param).encode()
            hash = hashlib.sha1(data).hexdigest()
            shm[hash] = {"deeplink": deeplink, "param": param, "redirect": False}
            dl = "{}?{}=http://{}/redirect/{}".format(deeplink, param, addr, hash)
            print('[*]deeplink+query:', dl)

            skip = False

            if(open_deeplink(dl)):
                count +=1
                if(count >= 4):
                    print('[!]Skipping current Scheme from the database!!')
                    skip = True
            if(skip):
                print('break!')
                break
    
    print('[*]<shared_memory>\n',shm)
    f.writelines(f'\n\n[*]<shared_memory>\n{shm}')
    f.close()

    redirect_found = []
    for key in shm:
        if shm[key]['redirect']:
            redirect_found.append(f'[{key}]{shm[key]}')
  
    if(redirect_found):
        f = open('./result.txt','a')
        f.write('-'*40+'\n')
        f.write(f'[{apk_name}]\n')
        for i in redirect_found:
            f.write(i+'\n')
    f.close()

    f = open('./analyzed_list.txt','a')
    f.write(apk_name+'\n')
    f.close()

    adb('shell am force-stop '+package)
    adb('uninstall '+ package)

    p.terminate()

if __name__ == "__main__":

    
    folder_items = os.listdir('./apks/')
    file_names=[]

    for item in folder_items:
        item_path = os.path.join('./apks', item)
        if os.path.isfile(item_path):
            file_names.append(item)
    
    with open('./analyzed_list.txt','r') as file:
        analyzed_apks = file.read()

    for apk in file_names:
        if not(apk[:-4] in analyzed_apks):
            print('apk:',apk[:-4])
            analyze_apk(apk)
    
    print('done!!!')
