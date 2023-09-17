# FindScheme

- findscheme_test.py를 python을 이용해서 실행시키면 코드를 실행시킬 수 있습니다.
- 뒤에 deeplink를 동적으로 실행하는 부분은 아직 코드를 설정하지 않았기 때문에 오류가 발생하는 것은 일반적입니다.
- 콘솔 출력에서 추출된 scheme,host,path,query등을 확인할 수 있습니다.

### 만약 com.nhn.android.search.apk가 아닌 다른 apk를 분석하기 위해서는 apk를 추가한 뒤 코드에서 경로를 바꿔 줘야 합니다.

- 파일 설명
  - findscheme_test.py -> 가장 기본 파일
  - findscheme_auto.py -> 여러 apk 파일에 대해서 자동으로 분석해주게 업그레이드한 버전
    - apks 폴더에 분석하고 싶은 apk들을 넣는다.
    - python findscheme_auto.py로 실행시킨다.
    - output 폴더에 각각의 apk에 대한 실행결과가 저장된다.
    - result.txt에서 유효한 redirect되는 deeplink들을 확인할 수 있다.
  - analyzed_list.txt -> 분석한 apk들이 저장되어 있다.
    - 이미 분석된 apk가 다시 분석되는 걸 막기 위함
    - 만약 분명히 apks 폴더에 apk를 넣었는데 분석되지 않는다면 analyzed_list.txt에 해당 apk가 존재하지 않는지 확인해 보자!!
