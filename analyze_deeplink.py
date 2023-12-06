from androguard.misc import *
from init import *
from server import *
import etc_util as JW
import time
import os
import subprocess

SHOW_PATH = False

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

def analyze_apk(APK_NAME,sess,p):
    
    JW.print_now()
    
    apk = "./apks/"+APK_NAME

    print('[*]Analyzing APK...')

    try:
        androguard_apk_obj, androguard_d_array, androguard_dx= AnalyzeAPK(apk,session = sess)
    except:
        print('Error occured while analyzing apk while using androguard AnalyzeAPK()')
        JW.file_write('error_while_installing.txt',APK_NAME)
        p.terminate()
        sess.reset()
        return "Fail"
    
    print('[*]APK Analyze completed..')

    package = androguard_apk_obj.get_package() # package 이름 가져오기
    print ("[*}package name:", package)


    return androguard_apk_obj, androguard_dx, package
 
def analyze_xml(androguard_apk_obj):
    start_parse = time.time()
    print('[*]Parsing string.xml')          
    strings_dict = parse_strings_xml(androguard_apk_obj)
    print('[*]ParsingAndroidManifest.xml')
    deeplink_list = parse_xml(androguard_apk_obj.get_android_manifest_xml(),strings_dict)

    return start_parse,deeplink_list
    

def analyze_smali(androguard_dx,deeplink_list):
    print('[*]Parsing Smali code')
    try:
        params = list()
        params1 = parse_method_and_params(target_to_find2, androguard_dx,1,1)
        params += params1

        params2 = parse_method_and_params(target_to_find1, androguard_dx,2,1)
        real_params2  = list()
        for i in params2: 
            if '?' in i:
                i['query'] = i['query'].split('?')[1][:-1]
                real_params2.append(i)
        
        params += real_params2

        real_params3 = list()
        params3 = parse_method_and_params(target_to_find3, androguard_dx, 2, 1)
        for i in params3: 
            if '?' in i:
                i['query'] = i['query'].split('?')[1][:-1]
                real_params3.append(i)
        params += real_params3
    except Exception as e:
        print(e)
        print('[!]Error occured while parsing smali')

    
    for param in params:
        recursive_search(androguard_dx, deeplink_list, param, RECURSION_DEPTH,target_to_find1)

def write_output(APK_NAME,deeplink_list,start,start_parse):    
    global SHOW_PATH
    JW.folderchk('output')
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

        return total_length


def parse_strings_xml(androguard_apk_obj):
    strings_dict ={}
    strings_xml = androguard_apk_obj.get_android_resources().get_resolved_strings()
    for string_key, string_values in strings_xml.items():
        for string_id in string_values['DEFAULT']:
            #name = androguard_apk_obj.get_android_resources().get_resource_xml_name(string_id).split(':string/')[1]
            value = string_values['DEFAULT'][string_id]
            strings_dict[string_id] = value
    return strings_dict

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
    except Exception as e:
        print(e)
        print('Error occured while parsing xml file.')

    return list(result)

def parse_method_and_params(target, androguard_dx,n,loc): # target이 list로 받아짐, list의 길이가 2이상인 경우에는 해당 순서를 만족하는 경우에만 파라미터 저장
    sequence = 0


    class_part, method_part, desc_part = fn_get_class_method_desc_from_string(target[sequence])
    print(f"class_part:{class_part}, method_part:{method_part}, desc_part:{desc_part}")

    methods = []

    for m in target:
        methods.append(fn_get_class_method_desc_from_string(m)[1])

    
    method_objs = []

    

    for method in androguard_dx.find_methods(class_part, method_part, desc_part):
        method_objs.append(method)

    print('[DEBUG] method_objs:',method_objs)

    param = list()

    if method_objs:
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
    else:
        param = []

    return param


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
        desc_part = ''
        method_part = ''
    if desc_part :
        if desc_part != '.':
            desc_part = re.escape(desc_part)
    class_part = re.escape(class_part)
    method_part = re.escape(method_part)

    return [class_part, method_part, desc_part]

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
    
def convert_smali_to_java(smali_string):
    if smali_string.startswith("L") and smali_string.endswith(";"):
        smali_string = smali_string[1:-1].replace("/", ".")
        
    if '$' in smali_string:
        smali_string = smali_string.split('$')[0]

    return smali_string

def draw_line(title):
    num = (50 - len(title))//2
    return '-'*num + title + '-' * num

def get_deeplink_len(deeplink_list):
    s = 0
    for node in deeplink_list:
        s += len(node.query)+1
    
    return s

def adb(cmd):
    try:
        JW.check_adb_stat()
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
        time.sleep(sleep_time)
        return True
    elif b'DEEP' in stdout:
        time.sleep(0.5)
        print('[?]Check ADB Status!!')
    else: 
        time.sleep(sleep_time)
 
    adb("shell input keyevent 3")

    
    return False
