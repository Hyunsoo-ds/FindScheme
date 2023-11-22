import os
import time
import hashlib
import subprocess
import etc_util as JW
from init import *
from analyze_deeplink import draw_line


def test_deeplink(package,deeplink_list,total_length,shm):
    adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
    time.sleep(2)

    

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
    
    return redirect_found
def JSI_test(redirect_found,APK_NAME,JSItest):
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
    
    JW.file_write('analyzed_list.txt',APK_NAME)

   

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
        time.sleep(sleep_time)
        return True
    elif b'DEEP' in stdout:
        time.sleep(0.5)
        print('[?]Check ADB Status!!')
    else: 
        time.sleep(sleep_time)
 
    adb("shell input keyevent 3")

    return False

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