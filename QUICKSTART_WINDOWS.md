# Windows 빠른 시작 가이드

Poetry 오류가 발생하셨나요? 이 가이드를 따라하세요!

## 문제: Poetry could not find a pyproject.toml file

이 오류는 **현재 디렉토리가 잘못되었다**는 의미입니다.

## 해결 방법

### 1단계: 프로젝트 폴더 찾기

다운로드한 프로젝트 폴더를 찾으세요. 예:
```
C:\Users\YourName\Downloads\announcerAI
```

### 2단계: 명령 프롬프트 열기

프로젝트 폴더에서:
1. 폴더 안에서 **Shift + 우클릭**
2. "여기에 PowerShell 창 열기" 또는 "명령 프롬프트 열기" 선택

또는 명령 프롬프트를 열고:
```cmd
cd C:\Users\YourName\Downloads\announcerAI
```

### 3단계: 한 번에 모두 시작

```cmd
start_all.bat
```

이 명령어 하나로:
- ✅ TTS 서버 자동 시작
- ✅ Announcer AI 봇 자동 시작
- ✅ 두 개의 창이 자동으로 열림

---

## 수동 시작 (문제가 있을 경우)

### TTS 서버 시작

**명령 프롬프트 창 1**:

```cmd
cd ttsclient-master
start_tts_server.bat
```

**오류가 발생하면**:

1. Poetry 설치 확인:
   ```cmd
   pip install poetry
   ```

2. 다시 시도:
   ```cmd
   cd ttsclient-master
   start_tts_server.bat
   ```

### Announcer AI 봇 시작

**명령 프롬프트 창 2** (새 창):

프로젝트 루트 폴더로 돌아가서:
```cmd
cd ..
run.bat
```

---

## 폴더 구조 확인

프로젝트 폴더가 다음과 같아야 합니다:

```
announcerAI/
├── start_all.bat          ← 전체 시작
├── run.bat                ← 봇 시작
├── ttsclient-master/
│   └── start_tts_server.bat  ← TTS 서버 시작
├── src/
├── config/
└── README.md
```

---

## 체크리스트

시작하기 전에 확인하세요:

- [ ] Python 3.9+ 설치됨 (`python --version`)
- [ ] FFmpeg 설치됨 (`ffmpeg -version`)
- [ ] Poetry 설치됨 (`poetry --version` 또는 `pip install poetry`)
- [ ] `config/config.yaml` 파일 존재
- [ ] Discord Bot Token 설정됨
- [ ] OpenAI 또는 Claude API Key 설정됨

---

## 여전히 안 된다면?

### 1. 현재 위치 확인

```cmd
cd
```

출력이 `C:\Users\YourName\announcerAI` 처럼 프로젝트 폴더여야 합니다.

### 2. 폴더 내용 확인

```cmd
dir
```

`start_all.bat`, `run.bat`, `ttsclient-master` 폴더가 보여야 합니다.

### 3. 상세 가이드 보기

[WINDOWS_SETUP.md](WINDOWS_SETUP.md) 파일을 열어 단계별 설명을 따라하세요.

---

## 가장 간단한 방법

1. 프로젝트 폴더를 **탐색기로 열기**
2. `start_all.bat` 파일을 **더블클릭**
3. 끝!

두 개의 창이 자동으로 열리고, TTS 서버와 봇이 시작됩니다.
