# FindScheme

---

FindScheme is used to find a deeplink that can be lead to Webview Redirection vulnearbility and extract Javascript Interface and methods of respective interface connected to valid deeplink. 

FindScheme offers features such as APK download automation, static analysis for extracting deeplinks and javascript interfaces and deeplink webview redirection test. These features flow and execute automatically in a ordered manner.

- Since tool `FindScheme` was developed while project `BoB 12th Team project` , we used FindScheme to select Android apps for identifying WebView logical bugs.
- FindScheme use `Androguard` for static analysis of APK files.
    
    [GitHub - androguard/androguard: Reverse engineering and pentesting for Android applications](https://github.com/androguard/androguard)
    

---

## How to use?

You need a Android device connected to your computer through `ADB`  to use this tool. Because all the apk installation and deeplink webview redirection test will be processed on Android device through ADB.

1. **Add package names on list.txt**
    - You need to add package name of application you want to analyze on `list.txt` file.
    - You can add several package names on list.txt. But you need to seperate them with line
    
    ex)
    
    ```
    com.pineapple.fruit.player
    com.mind.logic.games
    
    ```
    
    - APK file of application will be downloaded automatically by package name you added on `list.txt`
2. **Run [main.py](http://main.py/)**
    
    ```
    python3 main.py
    
    ```
    
    - You need to install `androguard` module using pip before running [main.py](http://main.py/)
        
        ```
        pip install androguard
        
        ```
        
3. **Check results**
    - Result of the static analysis will be saved on `result.txt` file
    
    ex)
    
    ```
    ----------------------------------------
    [com.pineapple.fruit.player]
    [d0ba46aba791f7f629265c5dca32dd28a434955dc]{'deeplink': 'fruit_webview://redirect', 'param': 'link', 'redirect': True}
    
    ```
    
    - If FindScheme find a valid deeplink that can be lead to Webview Redirection
        - package name of application and deeplink will be added to result.txt
    - FindScheme also extract valid param for deeplink.
        - So, the full set of valid deeplink will be like below
        
        ```
        fruit_webview://redirect?link={URL_I_WANT_TO_REDIRECT}
        
        ```
        
- FindScheme also have a feature to send result of analysis to the Database.

---

## How it works?

### Problem

- FindScheme extract deeplink and Javascript interfaces from APK using static analysis.
    - Deeplink consists of four major components
    
    ```
    scheme://host/path?param=...
    ```
    
    - `scheme`  and `host`  can be extracted easily by parsing AndroidManifest.xml
    - However `path`  and `param` are not specified in a unique file like AndroidManifest.xml.
        - We need to analyze application’s whole code to parase valid `param` .
            - Since there can be a false-positive param, we need to test every combination of `param` , `path`  and `scheme://host`
            - It requires lots of time to test all of the combinations.

### How we handled the problem

- We derived the relationship between `scheme://host`  and `path` , `params`  through static analysis.
    - We used `recursive search`  to efficiently find a valid pairs of `scheme://host`  and `path` , `param`
        - `Androguard`  was used to get call graph of methods.
            - So we can search recursively through call graph of related methods.
        - The purpose of recursive search is to check weather `param` is actually used in the Android activity connected to the deeplink.
    - By using the method above, we were able to significantly reduce the number of deeplinks that needed to be tested.
        - The `number of deeplinks` needed to be tested decreased `92.24%` on average compared to old method that test deeplink of every combinations.
        - The `time` required for analysis and deeplink test also decreased `84.43%` on average.

---

## Tips

- The static analysis phase may take some time depending on size of APK.
- After analyzing a specific application of applications in list.txt, the package name will be adde dto analyzed_list.txt.
    - This means that the next time you run [main.py](http://main.py/) again, FindScheme won’t analyze applications in `analyzed_list.txt` . Since it is already analyzed.
    - If you want to analyze the application again, you need to delete package name of application in `analyzed_list.txt` .
- If error occur during process, the whole process of the application will be stopped. And next applicaion’s process will begin.
    - Package name of application that occured error will be added to error_while_installing.txt.
    - FindScheme also won’t analyze applications in `error_while_installing.txt` next time.
    - If you want to analyze the application again, you need to delete package name of application in `error_while_installing.txt` .
