from androguard.misc import *
import time
import multiprocessing
from flask import Flask, request, render_template
import os
import subprocess
import hashlib
import logging
import functools
import socket
import gc
import requests
import etc_util as JW
import xml.etree.ElementTree as ET
import re
from rich import print as pprint
import datetime
import shutil

SHOW_PATH = False
AWS_url = 'http://43.200.177.231:5000/add_data'
RECURSION_DEPTH = 10
SERVER_ADDR = socket.gethostbyname(socket.gethostname())
print("[*]Hosting server:", SERVER_ADDR)
ADB_ADDR = "adb" # adb 사용할 거면 자신의 컴퓨터의 adb.exe의 경로에 맞게 경로를 수정해줘야함!!!

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.disabled = True

class Node:
    total_node = 0

    def __init__(self, activity, deeplink):
        self.activity = activity
        self.deeplink = deeplink
        self.query = []
        self.path = dict()
        Node.total_node += 1

    def compare_activity(self, current_activity):
        
        if(self.activity == current_activity):
            return True
        else:
            return False
        
    def show(self,f):
        print('-'*50)
        f.write('-'*50 + '\n')
        print(f'[deeplink]: {self.deeplink}\n')
        f.write(f'[deeplink]: {self.deeplink}\n')
        print(f'\t->[activity]: {self.activity}\n')
        f.write(f'\t->[activity]: {self.activity}\n')

        if self.query:
            print(f'\t\t->[query]: {self.query}')
            f.write(f'\t\t->[query]: {self.query}\n')
            if SHOW_PATH:
                for query in self.path:
                    for idx in range(len(self.path[query])):
                        f.write(f'[{query}]\n{self.path[query][idx]}' + '\n')


    def addQuery(self, q):
        if q not in self.query:
            self.query.append(q)

    def addPath(self, p, q):
        if q not in self.path:
            self.path[q] = [p]
        else:
            self.path[q].append(p)

@app.route('/t3')
def test2():
    return render_template('test2.html')

@app.route('/test-res2', methods=['POST'])
def result():

    connect = app.config["JSItest"]
    APKNAME = connect["APKNAME"]
    deeplink = connect["deeplink"]
    file_name = f'./JSI_test/Result_{APKNAME}.txt'
    now_time = time.localtime()
    
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
    res['User'] = 'yosimich'
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

def run_server(shm,JSItest):
    app.config["shm"] = shm
    app.config["JSItest"] = JSItest
    app.run(host=SERVER_ADDR, port=8012)

def convert_smali_to_java(smali_string):
    if smali_string.startswith("L") and smali_string.endswith(";"):
        smali_string = smali_string[1:-1].replace("/", ".")
        
    if '$' in smali_string:
        smali_string = smali_string.split('$')[0]

    return smali_string
    
def parse_strings_xml(androguard_apk_obj):
    strings_dict ={}
    strings_xml = androguard_apk_obj.get_android_resources().get_resolved_strings()
    for string_key, string_values in strings_xml.items():
        for string_id in string_values['DEFAULT']:
            #name = androguard_apk_obj.get_android_resources().get_resource_xml_name(string_id).split(':string/')[1]
            value = string_values['DEFAULT'][string_id]
            strings_dict[string_id] = value
    return strings_dict

def fn_get_class_method_desc_from_string(input_string):
    #  separated using '->'.
    if '->' in input_string:
        # There must be some string fragment after the '->'.
        split_string = input_string.split('->')
        if ((len(split_string) != 2) or (split_string[1] == '')):
            print('error!')

        # The class part is easy: it's the part preceding the '->'.
        class_part = split_string[0]

        # The part following the '->' may comprise the method *and* descriptor.
        method_desc_part = split_string[1]

        # However, it's possible that the descriptor part is not specified.
        # If the descriptor *is* included, it will begin with an
        #  opening parenthesis.
        if '(' in method_desc_part:
            method_part = method_desc_part.split('(')[0]
            desc_part = '(' + method_desc_part.split('(')[1]
        # If no opening parenthesis exists, we assume the descriptor hasn't
        #  been provided, i.e., the entire string is the method name.
        else:
            method_part = method_desc_part
            desc_part = '.'
    # If there is no "->" then assume that the entire string is the
    #  class name.
    else:
        class_part = input_string

    if desc_part != '.':
        desc_part = re.escape(desc_part)
    class_part = re.escape(class_part)
    method_part = re.escape(method_part)

    return [class_part, method_part, desc_part]
        

        
def method_to_smali_string(method):
    return f"{method.get_class_name()}->{method.get_name()}{method.get_descriptor()}".replace(" ","")

def parse_xml(android_manifest,strings_dict):
    result = set()

    try:
        for activity in android_manifest.iter("activity"):
            for key in activity.attrib.keys():
                if 'name' in key:
                    for data in activity.iter("data"):
                        deeplink = ''
                        for attr in data.attrib.keys(): 
                            if 'scheme' in attr:
                                scheme = data.attrib[attr]

                                if "@" in scheme:
                                    scheme = strings_dict[int(scheme.split("@")[1],16)]
                                deeplink += scheme + '://'

                            if 'host' in attr:
                                host = data.attrib[attr]

                                if "@" in host:
                                    host = strings_dict[int(host.split("@")[1],16)]

                                if deeplink[-3:] == '://':
                                    deeplink += host
                                else:
                                    print('ERROR! host before scheme')
                        if(deeplink):
                            class_name = activity.attrib[key]
                            result.add(Node(class_name, deeplink))
    except:
        print('Error occured while parsing xml file.')

    return list(result)

def parse_method_and_params(target, androguard_dx,n,loc): # target이 list로 받아짐, list의 길이가 2이상인 경우에는 해당 순서를 만족하는 경우에만 파라미터 저장
    sequence = 0


    class_part, method_part, desc_part = fn_get_class_method_desc_from_string(target[sequence])

    methods = []

    for m in target:
        methods.append(fn_get_class_method_desc_from_string(m)[1])

    
    method_objs = []


    for method in androguard_dx.find_methods(class_part, method_part, desc_part):
        method_objs.append(method)

    param = list()
    for method_obj in remove_duplicate(method_objs[0].get_xref_from()):
        local_reg = dict()

        byte_code = method_obj[1].get_code() # DalvikCode
        if byte_code != None:
            byte_code = byte_code.get_bc() # DCode
            idx = 0
            for i in byte_code.get_instructions():
                ins_name = i.get_name()
                ins_var = i.get_output().replace(" ", "")

                if ins_name == 'const-string': # const-string v4, 'edit'
                    first_comma_index = ins_var.find(',')
                    if first_comma_index != -1:
                        reg = ins_var[:first_comma_index]
                        val= ins_var[first_comma_index+2:-1].strip()
                    local_reg[reg] = val
                
                elif any(keyword in ins_var for keyword in methods):
                #method_part in ins_var: # {p1, v0}, Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;
                    current = 0
                    #print('sequence:', sequence)
                    for m in range(len(methods)):
                        if methods[m] in ins_var:
                            current = m
                    #print('current:', current)
                    #print('current_method:', methods[current])
                    #print(draw_line('.'))
                    
                    if sequence == len(target) - 1 and current == len(target) - 1:
                        #print('Foudn!!')
                        var = ins_var.split(method_part)[0].split(',')[:-1]

                        if len(var) == n+1:
                            key = var[loc]
                        else:
                            continue
                        if key in local_reg:
                            #print('[query]:', local_reg[key])
                            param.append({'query':local_reg[key], 'method': method_obj[1]})  # 파라미터와 메소드를 같이 매치해서 저장
                        sequence = 0
                        #input()
                    
                    if current < sequence:
                        sequence = current+1
                    elif current == sequence:
                        sequence +=1 % len(target)
                        
                idx += i.get_length()

    return param

def synchronize_with_node(deeplink_list, params):
    for param in params:
        class_name = convert_smali_to_java(param['method'].get_class_name())
        for node in deeplink_list:
            if node.compare_activity(class_name):
                node.addQuery(param['query'])

def remove_duplicate(xrefs):
    result = list()
    for method_obj in xrefs:
        exist = False
        for method_obj_result in result:
            if method_obj[1].get_class_name()+method_obj[1].get_name() == method_obj_result[1].get_class_name()+method_obj_result[1].get_name():
                exist = True
        if not exist:
            result.append(method_obj)

    return result

def recursive_search(androguard_dx, deeplink_list,  param, n,path):

    current_class = convert_smali_to_java(param['method'].get_class_name())
    current_path = f"{param['method'].get_class_name()}->{param['method'].get_name()}{param['method'].get_descriptor()}"
    path += '\n>>'+str(n) + ' ' + current_path

    for node in deeplink_list:
        if node.compare_activity(current_class):
            node.addQuery(param['query'])
            node.addPath(path,param['query'])

    if n <= 1:
        return 0
    
    xrefs = androguard_dx.get_method_analysis(param['method']).get_xref_from()
    xrefs = remove_duplicate(xrefs)

    if xrefs:
        for method_obj in xrefs:
            recursive_search(androguard_dx, deeplink_list, {'query':param['query'],'method': method_obj[1]}, n-1,path)
    else:
        return 0

def get_deeplink_len(deeplink_list):
    s = 0
    for node in deeplink_list:
        s += len(node.query)+1
    
    return s

def draw_line(title):
    num = (50 - len(title))//2
    return '-'*num + title + '-' * num

def p_write(text, f):
    print(text)
    f.write(text + '\n')

def parse_info(res,APKNAME):
    PORT = 8012
    SCHEME = res['deeplink']
    PARAM = res['param']
    package = APKNAME[:-4]
    redir_url = f"{SCHEME}?{PARAM}"
    deeplink = f"{redir_url}=http://{SERVER_ADDR}:{str(PORT)}/t3"
    return package,redir_url,deeplink

def parse_txt(line):
    
    parts = line.strip().split()
    
    deeplink = parts[1].split("'")[1]  # 딥링크 정보 추출
    param = parts[3].split("'")[1]  # 파라미터 정보 추출
    current_app = {
        'deeplink': deeplink,
        'param': param,
    }
    

    return current_app


def analyze_apk(APK_NAME,sess):
    global SHOW_PATH

    manager = multiprocessing.Manager()
    shm = manager.dict()
    JSItest = manager.dict()
    JSItest["connect"]=False
    
    JW.print_now()
    

    p = multiprocessing.Process(target=functools.partial(run_server, shm, JSItest))
    p.start()

    time.sleep(3)

    addr = SERVER_ADDR+":8012"

    start = time.time()
    apk = "./apks/"+APK_NAME

    decompile_dir, _ = os.path.splitext(apk)
    print('[*]Decompile_dir:',decompile_dir)
    print('[*]Analyzing APK...')

    try:
        androguard_apk_obj, androguard_d_array, androguard_dx= AnalyzeAPK(apk,session = sess)
    except:
        print('Error occured while analyzing apk while using androguard AnalyzeAPK()')
        with open('./error_while_installing.txt','a') as f2:
            f2.write(APK_NAME+', ')
        p.terminate()
        sess.reset()
        return "Fail"
    
    print('[*]APK Analyze completed..')

    package = androguard_apk_obj.get_package() # package 이름 가져오기
    print ("[*}package name:", package)

    if len(adb("shell pm list packages %s" % package)) == 0: #스마트폰에 앱 설치
        if(adb("install %s" % (apk))  == b'DEEP'):
            print('Error occured while installing apk into the device.')
            with open('./error_while_installing.txt','a') as f2:
                f2.write(APK_NAME+', ')

            p.terminate()
            sess.reset()
            return "Fail"

    start_parse = time.time()           # xml, smali 분석
    strings_dict = parse_strings_xml(androguard_apk_obj)
    print('[*]Parsing string.xml')
    deeplink_list = parse_xml(androguard_apk_obj.get_android_manifest_xml(),strings_dict)
    print('[*]ParsingAndroidManifest.xml')

    target_to_find1 = ["Landroid/app/Activity;->getIntent()Landroid/content/Intent;",
                    "Landroid/content/Intent;->getData()Landroid/net/Uri;", 
                    "Landroid/net/Uri;->toString()Ljava/lang/String;", 
                    "Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;"]

    target_to_find2 = ['Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;']

    target_to_find3 = ['Landroid/app/Activity;->getIntent()Landroid/content/Intent;',
                    'Landroid/content/Intent;->getDataString()Ljava/lang/String;',
                    'Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;']
    print('[*]Parsing Smali code')
    try:
        params = list()
        params1 = parse_method_and_params(target_to_find2, androguard_dx,1,1)
        params += params1

        params2 = parse_method_and_params(target_to_find1, androguard_dx,2,1)
        for i in params2: 
            i['query'] = i['query'].split('?')[1][:-1]
        params += params2

        params3 = parse_method_and_params(target_to_find3, androguard_dx, 2, 1)
        for i in params3: 
            i['query'] = i['query'].split('?')[1][:-1]
        params += params3
    except :
        print('[!]Error occured while parsing smali')

    
    for param in params:
        recursive_search(androguard_dx, deeplink_list, param, RECURSION_DEPTH,target_to_find1)

    with open(f'./output/{APK_NAME}.txt','w') as f:

        print(draw_line('<Analysis Result>'))
        f.write(draw_line('<Analysis Result>') + '\n')

        SHOW_PATH = False
        for node in deeplink_list:
            node.show(f)

        end = time.time()

        total_length = get_deeplink_len(deeplink_list)

        print(draw_line('<time>'))
        f.write(draw_line('<time>') + '\n')

        print(f'[*]Duration: {end - start}s')
        f.write(f'[*]Duration: {end - start}s\n')

        print(f'[*]Time Duration for Parsing: {end - start_parse}s')
        f.write(f'[*]Time Duration for Parsing: {end - start_parse}s\n')

        print(f'[*]Esimated numbers of deeplink to test: {total_length}')
        f.write(f'[*]Esimated numbers of deeplink to test: {total_length}\n')

        print(draw_line('<Redirect Test>'))
        f.write(draw_line('<Redirect Test>')+'\n')

    adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
    time.sleep(2)

    blacklist_keywords = {"firebase","mailto","fb","recaptcha","smsto","fbconnect", "http", "kakao", "https"}
    must_keywords = {"url","openurl","linkurl"}

    tested_number  = 0

    for node in deeplink_list:

        #node.addQuery('url')

        deeplink = node.deeplink
        if any(keyword in deeplink for keyword in blacklist_keywords):
            tested_number += len(node.query) + 1
            continue
        data = (str(time.time())+deeplink).encode()
        hash = hashlib.sha1(data).hexdigest()
        shm[hash] = {"deeplink": deeplink, "param": "", "redirect": False}
        
        dl = "{}/http://{}/redirect/{}".format(deeplink, addr, hash)
        tested_number +=1
        print(f'[{round(tested_number/total_length*100,2)}%]deeplink:{dl}')
        open_deeplink(dl)

        for q in must_keywords:
            if q not in node.query:
                data = (str(time.time())+deeplink).encode()
                hash = hashlib.sha1(data).hexdigest()
                shm[hash] = {"deeplink": deeplink, "param": q, "redirect": False}
                dl = "{}?{}=http://{}/redirect/{}".format(deeplink, q, addr, hash)
                print(f'[MUST]deeplink:{dl}')
                open_deeplink(dl)
        count = 0

        for param in node.query:
            data = (str(time.time())+deeplink+param).encode()
            hash = hashlib.sha1(data).hexdigest()
            shm[hash] = {"deeplink": deeplink, "param": param, "redirect": False}
            dl = "{}?{}=http://{}/redirect/{}".format(deeplink, param, addr, hash)
            tested_number +=1
            print(f'[{round(tested_number/total_length*100,2)}%]deeplink+query:{dl}')

            skip = False
            if(open_deeplink(dl)):
                count +=1
                if(count >= 4):
                    print('[!]Skipping current Scheme from the database!!')
                    skip = True
            if(skip):
                break

    redirect_found = []
    for key in shm:
        if shm[key]['redirect']:
            redirect_found.append(f'[{key}]{shm[key]}')

    if(redirect_found):
        JW.apk_copy(APK_NAME)
        with open('./result.txt','a') as f:
            f.write('-'*40+'\n')
            f.write(f'[{APK_NAME}]\n')
            for i in redirect_found:
                f.write(i+'\n')
            
                res = parse_txt(i)
            
                package_name, redir_url,deeplink = parse_info(res,APK_NAME)
                JSItest["APKNAME"]=package_name
                JSItest["deeplink"]=redir_url
        
                print(f"Trying this deeplink : {deeplink}")
                adb("shell am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d \"%s\"" % (deeplink))
                print ("waiting for Response...")
                timeout_seconds = 15
                count = 1
                while True:
                    print(f"Time Passed: {count}sec")
                    count += 1
                    if JSItest["connect"]:
                        JSItest["connect"] = False
                        break
                    elif count > timeout_seconds:
                        print(f"Timeout: {timeout_seconds} 초 동안 요청이 오지 않았습니다.")
                        file_name ='JSItest_fail.txt'
                        write_data = APK_NAME+'\n'
                        if os.path.isfile(file_name):
                            with open(file_name, "a", encoding="utf-8") as file:
                                file.write(write_data)
                        else:
                            with open(file_name, "w", encoding="utf-8") as file:
                                file.write(write_data)
                        break
                    time.sleep(1)
            
        
        print("Parsing JSInterface, Method Name Done")
    
    with open('./analyzed_list.txt','a') as f:
        f.write(APK_NAME+'\n')

    adb('shell am force-stop '+package)
    adb('uninstall '+ package)
    p.terminate()
    sess.reset()
    print(draw_line('<END>') + '\n\n\n')

CACHE_DIR = 'apks'
APK_PACKAGE_NAME_LIST = 'list.txt'
complete = 'complete'
total_path ='complete\\downloadcomplete.txt'
error_path='complete\\errordownload.txt'
def get_bounds_as_coordinates(bounds):
    numbers = [int(num) for num in re.findall(r'\d+', bounds)]
    return (numbers[0] + numbers[2]) // 2, (numbers[1] + numbers[3]) // 2

def dump_ui_hierarchy(retries=5):
    for _ in range(retries):
        result = subprocess.run("adb shell uiautomator dump /sdcard/screen.xml", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if "UI hierchary dumped to: /sdcard/screen.xml" in result.stdout.decode():
            break
        else:
            print('Failed to dump UI hierarchy. Retrying...')
            time.sleep(1)
    else:
        print('Failed to dump UI hierarchy after retries. Exiting...')
        return False
    os.system("adb pull /sdcard/screen.xml")
    return True

def dump_screen_and_get_root():
    res = dump_ui_hierarchy()

    if res == False:
        return res
    return ET.parse('screen.xml').getroot()

def open_play_store_page(package_name):
    os.system(f"adb shell am start -a android.intent.action.VIEW -d 'market://details?id={package_name}'")
    time.sleep(3)

def check_apk_cache(package_name):
    return os.path.isfile(f"{CACHE_DIR}/{package_name}.apk")


def find_apk_size_and_install_button(root):
    size_pattern = re.compile(r'\b\d+(\.\d+)?\s+MB\b')

    apk_size = None
    install_button_bounds = None
    for node in root.iter('node'):
        content_desc = node.get('content-desc', '')
        if not apk_size and 'MB' in content_desc:
            size_match = size_pattern.search(content_desc)
            if size_match:
                apk_size = float(size_match.group().split()[0])
        
        if "이 휴대전화는 앱과 호환되지 않습니다." == content_desc:
            raise('Incompatiable package for this device')
        if "콘텐츠 등급: 18세 이상"== content_desc:
            raise('Adult only')
        if '설치' == content_desc:
            install_button_bounds = node.get('bounds')
    
    return apk_size, install_button_bounds

def find_apk_size_and_cancel_button(root):
    size_pattern = re.compile(r'\b\d+(\.\d+)?\s+MB\b')

    apk_size = None
    cancel_button_bounds = None
    for node in root.iter('node'):
        content_desc = node.get('content-desc', '')
        if not apk_size and 'MB' in content_desc:
            size_match = size_pattern.search(content_desc)
            if size_match:
                apk_size = float(size_match.group().split()[0])
        
        if "This phone isn't compatible with this app." == content_desc:
            raise('Incompatiable package for this device')
        if "Content rating Rated for 18+" == content_desc:
            raise('Adult only')
        if 'Cancel' == content_desc:
            cancel_button_bounds = node.get('bounds')
    
    return apk_size, cancel_button_bounds

def tap_install_button(install_button_bounds):
    x, y = get_bounds_as_coordinates(install_button_bounds)
    os.system(f"adb shell input tap {x} {y}")
    print(f'Installing...')

def tap_cancel_button(cancel_button_bounds):
    x, y = get_bounds_as_coordinates(cancel_button_bounds)
    os.system(f"adb shell input tap {x} {y}")
    print(f'canceling...')
    
def wait_for_installation():
    cnt = 0
    while True:
        root = dump_screen_and_get_root()
        print(cnt)
        cnt += 1
        if(cnt ==200):
            os.system('adb shell am force-stop com.android.vending')
            time.sleep(3)
            return False
        if not root:
            return False
        done_button_found = any(('제거' == node.get('content-desc', '')) for node in root.iter('node'))
        if done_button_found:
            print('Installation finished.')
            return True
        time.sleep(3)


def extract_and_uninstall(package_name):
    os.system(f"adb shell pm path {package_name} > path.txt")
    with open("path.txt") as f:
        apk_paths = f.read()
        apk_path = apk_paths.split("\n")[0].split(":")[-1]
    os.system(f"adb pull {apk_path} {CACHE_DIR}/{package_name}.apk")
    os.system(f"adb shell pm uninstall {package_name}")
    print("write sucess.txt")
    return True

def process_package(package_name):
    if check_apk_cache(package_name):
        print(f"Package {package_name} already present in cache.")
        return True


    open_play_store_page(package_name)
    root = dump_screen_and_get_root()
    try:
        apk_size, install_button_bounds = find_apk_size_and_install_button(root)
    except:
        pprint("[yellow]Exception occurred trying to find size and install button[/yellow]")
        return False

    if install_button_bounds:
        tap_install_button(install_button_bounds)
        res = wait_for_installation()
        if not res:
            return False
        
        return extract_and_uninstall(package_name)
    else:
        print(f"Couldn't find the install button for {package_name}.")

def main(package_name):

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    OVERSIZED_PACKAGES_FILE = 'OVERSIZED_PACKAGES_FILE.txt'
    if not os.path.isfile(OVERSIZED_PACKAGES_FILE):
        with open(OVERSIZED_PACKAGES_FILE, 'w'):
            pass

    res = process_package(package_name)

    if not res:
        pprint(f"[yellow]Package : {package_name} failed[/yellow]")
        with open(error_path, "a", encoding="utf-8") as file:
            file.write(package_name + '\n')
        with open('./error_while_installing.txt','a') as f2:
            f2.write(package_name+', ')
        print("write error.txt")
        return False
    else:
        pprint(f"[green]Package : {package_name} success[/green]")
        with open(total_path, "a", encoding="utf-8") as file:
            file.write(package_name + '\n')
        return True
        



if __name__ == "__main__":
    
    source_folder = CACHE_DIR
    target_folder = "complete\\analyze_apks"
    folder_items = os.listdir('./apks/')
    file_names=[]
    session = get_default_session()

    with open(APK_PACKAGE_NAME_LIST,"r") as file:
        package_name_list= file.readlines()

    package_names = [l.strip() for l in package_name_list]
    
    with open('./analyzed_list.txt','r') as file:
        analyzed_apks = file.read()
    
    with open('./error_while_installing.txt') as file:
        error_apks = file.read()

    with open(total_path,'r') as file:
        download_apks = file.read()
    i = 0
    for package_name in package_names:
        i +=1
        if not(package_name in analyzed_apks or package_name in error_apks):
            print(f'[*]{i}/{len(package_names)}: {package_name}')
            if not (package_name in download_apks):
                keepgoing = main(package_name)
            else:
                keepgoing = True
            if keepgoing:
                package_name += ".apk"
                analyze_apk(package_name,session)
            #print('while:', gc.get_count())
                gc.collect()
                file_path = os.path.join(source_folder, package_name)
                shutil.move(file_path, target_folder)

                
    
    print('done!!!')