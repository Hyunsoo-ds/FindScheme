# FindScheme

---

 FindScheme is used to find a deeplink that can be lead to Webview Redirection vulnearbility and extract Javascript Interface and methods of respective interface connected to valid deeplink. FindScheme offers features such as APK download automation, static analysis for extracting deeplinks and javascript interfaces and deeplink webview redirection test. These features flow and execute automatically in a ordered manner. 

- Since tool ‘FindScheme’ was developed while project `BoB 12th Team project` , we used FindScheme to select Android apps for identifying WebView logical bugs.
- FindScheme use `Androguard`  for static analysis of APK files.
    
    [GitHub - androguard/androguard: Reverse engineering and pentesting for Android applications](https://github.com/androguard/androguard)
    

---

## How to use?

You need a Android device connected to your computer through `ADB`  to use this tool. Because all the apk installation and deeplink webview redirection test will be processed on Android device through ADB.

1. **Add package names on list.txt**
    - You need to add package name of application you want to analyze on `list.txt`  file.
    - You can add several package names on list.txt. But you need to seperate them with line
    
    ex)
    
    ```
    com.pineapple.fruit.player
    com.mind.logic.games
    ```
    
    - APK file of application will be downloaded automatically by package name you added on `list.txt`

1. **Run main.py**
    
    
    ```
    python3 main.py
    ```
    
    - You need to install `androguard`  module using pip before running main.py
        
        ```
        pip install androguard
        ```
        
2. **Check results**
    - Result of the static analysis will be saved on `result.txt`  file
    
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

## Tips

- The static analysis phase may take some time depending on size of APK.
- After analyzing a specific application of applications in list.txt, the package name will be adde dto analyzed_list.txt.
    - This means that the next time you run [main.py](http://main.py) again, FindScheme won’t analyze applications in `analyzed_list.txt` . Since it is already analyzed.
    - If you want to analyze the application again, you need to delete package name of application in `analyzed_list.txt` .
- If error occur during process, the whole process of the application will be stopped. And next applicaion’s process will begin.
    - Package name of application that occured error will be added to error_while_installing.txt.
    - FindScheme also won’t analyze applications in `error_while_installing.txt`  next time.
    - If you want to analyze the application again, you need to delete package name of application in `error_while_installing.txt` .
