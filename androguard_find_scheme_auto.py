from androguard.misc import *
import time
import multiprocessing
from flask import Flask, request
import os
import subprocess
import hashlib
import logging
import functools
import socket

SHOW_PATH = False
RECURSION_DEPTH = 20
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
        p_write('-'*50,f)
        p_write(f'[deeplink]: {self.deeplink}',f)
        p_write(f'\t->[activity]: {self.activity}',f)

        if self.query:
            p_write(f'\t\t->[query]: {self.query}',f)
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

@app.route("/redirect/<hash>")
def redirect(hash):
    temp = app.config["shm"][hash]
    temp["redirect"] = True
    app.config["shm"][hash] = temp
    print(request.headers)
    return "THIS IS A REDIRECT PAGE...!!!"

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
    return [class_part, method_part, desc_part]
        
def method_to_smali_string(method):
    return f"{method.get_class_name()}->{method.get_name()}{method.get_descriptor()}".replace(" ","")

def parse_xml(android_manifest,strings_dict):
    result = set()

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

    return list(result)

def parse_method_and_params(target, androguard_dx):
    class_part, method_part, desc_part = fn_get_class_method_desc_from_string(target)
    
    method_objs = []

    if desc_part != '.':
        desc_part = re.escape(desc_part)
    class_part = re.escape(class_part)
    method_part = re.escape(method_part)

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
                elif 'getQueryParameter' in ins_var: # {p1, v0}, Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;
                    
                    var = ins_var.split('getQueryParameter')[0].split(',')[:-1]

                    if len(var) == 2:
                        key = var[1]
                    else:
                        continue
                    if key in local_reg:
                        param.append({'query':local_reg[key], 'method': method_obj[1]})  # 파라미터와 메소드를 같이 매치해서 저장
            
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

def analyze_apk(APK_NAME):
    global SHOW_PATH

    manager = multiprocessing.Manager()
    shm = manager.dict()

    p = multiprocessing.Process(target=functools.partial(run_server, shm))
    p.start()

    time.sleep(3)

    addr = SERVER_ADDR+":8012"

    start = time.time()
    apk = "./apks/"+APK_NAME

    decompile_dir, _ = os.path.splitext(apk)
    print('[*]Decompile_dir:',decompile_dir)
    print('[*]Analyzing APK...')
    androguard_apk_obj, androguard_d_array, androguard_dx= AnalyzeAPK(apk,session = None)
    print('[*]APK Analyze completed..')

    package = androguard_apk_obj.get_package() # package 이름 가져오기
    print ("[*}package name:", package)

    if len(adb("shell pm list packages %s" % package)) == 0: #스마트폰에 앱 설치
        if(adb("install %s" % (apk))  == b'DEEP'):
            f2 = open('./error_while_installing.txt','a')
            f2.write(APK_NAME+', ')
            f2.close()
            p.terminate()

            return "Fail"

    start_parse = time.time()           # xml, smali 분석
    strings_dict = parse_strings_xml(androguard_apk_obj)
    print('[*]Parsing string.xml')
    deeplink_list = parse_xml(androguard_apk_obj.get_android_manifest_xml(),strings_dict)
    print('[*]ParsingAndroidManifest.xml')

    target_to_find = 'Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;'
    params = parse_method_and_params(target_to_find, androguard_dx)
    print('[*]Parsing Smali code')
    for param in params:
        recursive_search(androguard_dx, deeplink_list, param, RECURSION_DEPTH,target_to_find)



    f = open(f'./output/{APK_NAME}.txt','w')

    p_write(draw_line('<Analysis Result>'),f)

    SHOW_PATH = False
    for node in deeplink_list:
        node.show(f)
    f.write(draw_line('<Path Analysis Result>') + '\n')
    SHOW_PATH = True
    for node in deeplink_list:
        node.show(f)


    end = time.time()

    total_length = get_deeplink_len(deeplink_list)

    p_write(draw_line('<time>'),f)
    p_write(f'[*]Duration: {end - start}s',f)
    p_write(f'[*]Time Duration for Parsing: {end - start_parse}s',f)
    p_write(f'[*]Esimated numbers of deeplink to test: {total_length}',f)
    print(draw_line('<Redirect Test>'))

    f.close()

    adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
    time.sleep(2)

    blacklist_keywords = {"firebase","mailto","fb","recaptcha","smsto","fbconnect", "http", "kakao", "https"}

    tested_number  = 0

    for node in deeplink_list:
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
        f = open('./result.txt','a')
        f.write('-'*40+'\n')
        f.write(f'[{APK_NAME}]\n')
        for i in redirect_found:
            f.write(i+'\n')
    f.close()

    f = open('./analyzed_list.txt','a')
    f.write(APK_NAME+'\n')
    f.close()

    adb('shell am force-stop '+package)
    adb('uninstall '+ package)
    p.terminate()
    print(draw_line('<END>') + '\n\n\n')

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
            print('[*]apk:',apk[:-4])
            analyze_apk(apk)
    
    print('done!!!')
