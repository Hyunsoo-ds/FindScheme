import socket
from etc_util import folderchk, filechk

USERNAME = 'TEST'
AWS_url = 'http://YOUR_AWS_ADDRESS:PORT/add_data' # Add your AWS Address
RECURSION_DEPTH = 10
CACHE_DIR = 'apks'
APK_PACKAGE_NAME_LIST = 'list.txt'
SERVER_ADDR = socket.gethostbyname(socket.gethostname())
ADB_ADDR = "adb" 
addr = SERVER_ADDR+":8012"
blacklist_keywords = {"firebase","mailto","fb","recaptcha","smsto","fbconnect", "http", "kakao", "https"}
must_keywords = {"url","openurl","linkurl"}

target_to_find1 = ["Landroid/app/Activity;->getIntent()Landroid/content/Intent;",
                "Landroid/content/Intent;->getData()Landroid/net/Uri;", 
                "Landroid/net/Uri;->toString()Ljava/lang/String;", 
                "Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;"]

target_to_find2 = ['Landroid/net/Uri;->getQueryParameter(Ljava/lang/String;)Ljava/lang/String;']

target_to_find3 = ['Landroid/app/Activity;->getIntent()Landroid/content/Intent;',
                'Landroid/content/Intent;->getDataString()Ljava/lang/String;',
                'Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;']

def init_file_check():
    folderchk('JSI_test')
    folderchk('apks')
    folderchk('templates')
    folderchk('success_apk')
    folderchk('output')
    filechk('error_while_installing.txt')
    filechk('analyzed_list.txt')
    if filechk('list.txt'):
        print('You should write package name in [list.txt]')
        return 1
    else:
        return 0


def set_apk_list():
    with open(APK_PACKAGE_NAME_LIST,"r") as file:
        package_name_list= file.readlines()

    package_names = [l.strip() for l in package_name_list]

    apk_list = []
    with open('analyzed_list.txt','r') as file:
        analyzed_apks = file.read()
      
    
    with open('error_while_installing.txt','r') as file:
        error_apks = file.read()
        
    for pk_name in package_names:
        
        if pk_name not in analyzed_apks and pk_name not in error_apks:
            apk_list.append(pk_name)

    return apk_list
