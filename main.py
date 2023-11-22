import etc_util as JW
import time
from deeplink_test import test_deeplink, JSI_test
from androguard.misc import get_default_session
from apk_download import download_apk
from init import set_apk_list, init_file_check
from server import server_start
from analyze_deeplink import *
import gc

if __name__ == "__main__":
    
    if init_file_check():
        exit()

    session = get_default_session()

    package_names = set_apk_list()
    if not len(package_names):
        print('You should write (new) package name in [list.txt]')
        exit()

    
    for i, package_name in enumerate(package_names):
        print(f'[*]{i}/{len(package_names)}: {package_name}')
        
        if download_apk(package_name):
            package_name += ".apk"
            
            try:
                p, shm, JSItest= server_start()
                start = time.time()
                
                androguard_apk_obj,androguard_dx,package = analyze_apk(package_name,session,p)
                start_parse,deeplink_list=analyze_xml(androguard_apk_obj)
                analyze_smali(androguard_dx,deeplink_list)
                total_length = write_output(package_name,deeplink_list,start,start_parse)
                redirect_found = test_deeplink(package,deeplink_list,total_length,shm)
                JSI_test(redirect_found,package_name,JSItest)
                
                adb('shell am force-stop '+package)
                adb('uninstall '+ package)

                p.terminate()
                session.reset()

                print(draw_line('<END>') + '\n\n\n')

            except Exception as e:
                p.terminate()
                gc.collect()
                JW.file_write('something_error.txt',f'{package_name} Error with {e}')
                pass   
        gc.collect()
        adb('shell input keyevent KEYCODE_HOME')
        adb('shell am force-stop com.android.vending')
 
    print('done!!!')