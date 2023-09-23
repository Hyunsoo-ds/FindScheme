import os
from glob import glob

class Node:
    total_node = 0

    def __init__(self, activity, deeplink):
        self.activity = activity
        self.deeplink = deeplink
        self.query = []
        Node.total_node += 1
    
    def addquery(self,q):
        self.query.append(q)

    def compare_activity(self, current_activity):
        #print('self.activity:',self.activity )
        #print('parsed_activity', current_activity)
        if(self.activity == current_activity):
            return True
        else:
            return False
    
def parse_class(line):
    parsed = ''
    for i in line.split(' '):
        if('/' in i):
            parsed = i   
    parsed  = parsed[1:-1].replace('/','.')       

    return parsed

def parse_smali(decompile_dir,target_activity):
    params = set()

    for diretory in glob( os.path.join(decompile_dir, "smali*") ):
        for path, dirs, files in os.walk(diretory):
            for file in files:
                f = os.path.join(path, file)
                param = parse_smali_file(f,target_activity)
                if len(param) > 0: params.update(param)
    
    return list(params)

def parse_smali_file(file_path,target_activity):
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except: 
        print('no smali founded. Exit')
        return [], [], [], [], []
    
    local_register = dict()
    param = set()

    for line in lines:
        line = line.strip()
        if not line: continue
        
        words = line.split(" ")
        if words[0] == ".class":
            
            class_name = parse_class(line)
            
            if class_name not in target_activity:
                break
            print('class_name:', class_name)
        elif words[0] == ".method":
            method_name = line
        try:
            if "const-string" in line:
                local_register[words[1][:-1]] = words[2].split("\"")[1]
            elif "getQueryParameter(" in line:
                if "}" not in line: 
                    continue
                var = line.split("}")[0].split()[-1]
                if var in local_register:
                    param.add(local_register[var])
                    for node in deeplinks:  # deeplinks에 있는 객체 중 동일한 activity에 query를 추가
                        if(node.compare_activity(class_name)):
                            node.addquery(local_register[var])
 
        except Exception as e:
            print('Error occured.. While Extracting Deeplink.')
            print(file_path, line)
            print(e)
            exit()
    return list(param)
 
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
    
    activity = ""
    for line in manifest_file:
        line = line.strip()
        if not line: continue
        deeplink = ""
        
        if "activity" in line and "/activity" not in line and 'alias' not in  line:
            activity = (line.split("android:name=")[1].split("\"")[1])

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
            elif "android:pathPrefix=" in line:
                path = (line.split("android:pathPrefix=")[1].split("\"")[1])
                if "@string/" in path:
                    path = strings_xml[path.split("@string/")[1]]
                deeplink += path
            if(activity):
                result.add(Node(activity, deeplink))
    
    return list(result)

 
    

if __name__ == "__main__":
    apk = "C:\\FindScheme\\FindScheme\\apks\\무신사.3.63.1.apk"
    decompile_dir, _ = os.path.splitext(apk)
    print('decompile_dir:',decompile_dir)

    if not os.path.isdir(decompile_dir):
        print("java -jar apktool.jar d %s -f --output %s" % (apk, decompile_dir))
        os.system("java -jar apktool.jar d %s -f --output %s" % (apk, decompile_dir))
    with open(os.path.join(decompile_dir, "AndroidManifest.xml"), encoding="UTF8") as f:
        package = f.read().split("package=\"")[1].split("\"")[0]
    print ("package name:", package)


    deeplinks = parse_scheme(decompile_dir)
    
    target_activity = []

    for i in range(len(deeplinks)):
        #print(f'[{i}][activity]:{deeplinks[i].activity} \n \t->[deeplink]:{deeplinks[i].deeplink}')
        target_activity.append(deeplinks[i].activity)
    
    target_activity = list(set(target_activity))
    print('target_activity:\n',target_activity)
    
    params = parse_smali(decompile_dir,target_activity)
    
    
    for node in deeplinks:
        print(f'[activity]: {node.activity}')
        print(f'\t->[deeplink]: {node.deeplink}')
        for q in node.query:
            print(f'\t\t->[query]: {q}')
