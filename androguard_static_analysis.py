from androguard.misc import *

class Node:
    total_node = 0

    def __init__(self, activity, deeplink):
        self.activity = activity
        self.deeplink = deeplink
        self.query = []
        self.path = []
        Node.total_node += 1

    def compare_activity(self, current_activity):
        
        if(self.activity == current_activity):
            return True
        else:
            return False
        
    def show(self):
        print('-'*100)
        print(f'[deeplink]: {self.deeplink}')
        print(f'\t->[activity]: {self.activity}')
        if self.query:
            print(f'\t\t->[query]: {self.query}')
            for idx in range(0,len(self.path)):
                print(f'\t\t->[path][{idx}]: {self.path[idx]}')

    def addQuery(self, q):
        if q not in self.query:
            self.query.append(q)

    def addPath(self, p):
        if p not in self.path:
            self.path.append(p)



def convert_smali_to_java(smali_string):
    # "L"로 시작하고 ";"로 끝나는 경우만 변환
    if smali_string.startswith("L") and smali_string.endswith(";"):
        # "L" 제거하고 "/"를 "."로 대체
        java_string = smali_string[1:-1].replace("/", ".")
        return java_string
    else:
        # 변환할 필요 없는 경우 원래 문자열 반환
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
    for method_obj in method_objs[0].get_xref_from():
        local_reg = dict()
        #print(f'[[clas]: {method_obj[1].get_class_name()}')
        #print(f'[method]: {method_obj[1].get_name(),method_obj[1].get_descriptor()}')  
        byte_code = method_obj[1].get_code() # DalvikCode
        if byte_code != None:
            byte_code = byte_code.get_bc() # DCode
            idx = 0
            for i in byte_code.get_instructions():
                ins_name = i.get_name()
                ins_var = i.get_output().replace(" ", "")

                #print(ins_name,'|',ins_var)

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

def recursive_search(androguard_dx, deeplink_list,  param, n,path):
    print(f"[depth]:{n}")
    print(f"[path]:{path}")
    print(f"[current]:{param['method']}")
    input()
    if n <= 0:
        print('The End...')
        return 0
    
    xrefs = androguard_dx.get_method_analysis(param['method']).get_xref_from()
    
    if xrefs:
        print('Going in ...')
        for method_obj in xrefs:
            #print(method_obj[1])
            for node in deeplink_list:
                current_class = convert_smali_to_java(method_obj[1].get_class_name())
                current_path = f"{method_obj[1].get_class_name()}->{method_obj[1].get_name()}{method_obj[1].get_descriptor()}"
                path += '\n>>'+str(n) + ' ' + current_path
                print(f'[current_path]:{current_path}')
                
                if node.compare_activity(current_class):
                    print('Found...!!')
                    node.addQuery(param['query'])
                    node.addPath(path)
                
                recursive_search(androguard_dx, deeplink_list, {'query':param['query'],'method': method_obj[1]}, n-1,path)
    else:
        print('No more XREF!!!')
        return 0



if __name__ == '__main__':
    apk = "apks/com.popmart.byapps.apk"
    androguard_apk_obj, androguard_d_array, androguard_dx= AnalyzeAPK(apk,session = None)
    print('[*]APK Analyzed completed..')

    strings_dict = parse_strings_xml(androguard_apk_obj)
    print('[*]Parsing string.xml')
    deeplink_list = parse_xml(androguard_apk_obj.get_android_manifest_xml(),strings_dict)
    print('[*]ParsingAndroidManifest.xml')


    # for node in deeplink_list:
    #     node.show()
    target_to_find = 'Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;'
    params = parse_method_and_params(target_to_find, androguard_dx)
    print('[*]Parsing Smali code')
    # for i in params:
    #     print('[query]',i['query'],':', i['method'].get_class_name())
    #     print('[method]:', i['method'])
    #     print(f"{i['method'].get_class_name()}->{i['method'].get_name()}{i['method'].get_descriptor()}".replace(" ",""))

    synchronize_with_node(deeplink_list, params)
    print('[*]Synchronizing....')


    for param in params:
        recursive_search(androguard_dx, deeplink_list, param, 3,target_to_find)

    for node in deeplink_list:
        node.show()