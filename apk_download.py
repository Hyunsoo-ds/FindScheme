from rich import print as pprint
import os
import time
import subprocess
from init import CACHE_DIR
from etc_util import folderchk
import xml.etree.ElementTree as ET
import re

def download_apk(package_name):
    folderchk(CACHE_DIR)
    res = process_package(package_name)

    if not res:
        pprint(f"[yellow]Package : {package_name} failed[/yellow]")
        with open('./error_while_installing.txt','a',encoding="utf-8") as f2:
            f2.write(package_name+'\n')
        print("write error.txt")
        return False
    else:
        pprint(f"[green]Package : {package_name} success[/green]")
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
    
def check_apk_cache(package_name):
    return os.path.isfile(f"{CACHE_DIR}/{package_name}.apk")

def open_play_store_page(package_name):
    os.system(f"adb shell am start -a android.intent.action.VIEW -d 'market://details?id={package_name}'")
    time.sleep(3)

def dump_screen_and_get_root():
    res = dump_ui_hierarchy()

    if res == False:
        return res
    return ET.parse('screen.xml').getroot()

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
        if(cnt ==100):
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
    return True

def get_bounds_as_coordinates(bounds):
    numbers = [int(num) for num in re.findall(r'\d+', bounds)]
    return (numbers[0] + numbers[2]) // 2, (numbers[1] + numbers[3]) // 2

def dump_ui_hierarchy(retries=15):
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