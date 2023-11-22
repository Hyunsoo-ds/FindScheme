import shutil
import os
import datetime
import requests

def log_error(e):
    file_write('something_error.txt',e)

def folderchk(folder_dir):
    if not os.path.exists(folder_dir):
        os.mkdir(folder_dir)

def apk_copy(apkname):
    try:
        foldername = 'success_apk'
        folderchk(foldername)
        source_file = './apks/'+apkname
        destination_file = f'./{foldername}/{apkname}'
        shutil.copy(source_file, destination_file)
    except Exception as e:
        log_error(e)
        print(f"fail to copy apk casue : {e}")
        
def print_now():
    current_time = datetime.datetime.now()
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"현재 시간: {current_time_str}")

def file_write(file_name,write_data):
    write_data = write_data+'/n'
    if os.path.isfile(file_name):
        with open(file_name, "a", encoding="utf-8") as file:
            file.write(write_data)
    else:
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(write_data)

def upload_apk_to_AWS():
    foldername = 'success_apk'
    upload_url = 'http://43.200.177.231:5000/upload'
    folderchk(foldername)
    apklist = os.listdir(foldername)
    if(len(apklist)):
        for apk in apklist:
            print(apk)
            file_path = f'{foldername}/{apk}'
            with open(file_path, 'rb') as file:
                files = {'file': (f'{apk}', file)}
                response = requests.post(upload_url, files=files)
                print(response.text)

if __name__ == '__main__':
    upload_apk_to_AWS()
