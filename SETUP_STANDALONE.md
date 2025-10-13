# Market Analysis Agent - 독립 실행 가이드

이 문서는 `market-analysis-agent`를 **skala-gai 프로젝트 외부**에서 독립적으로 실행하는 방법을 설명합니다.

---

## 📋 필요한 것들

### 1. Python 환경
- **Python 3.11** (권장: 3.11.9 또는 3.11.11)
- pip 또는 Poetry

### 2. 필수 파일 (모두 포함됨)
```
market-analysis-agent/
├── agents/              ✅
├── prompts/             ✅
├── utils/               ✅
├── data/                ✅ (비어있음 - PDF 넣을 곳)
├── outputs/             ✅ (비어있음 - 결과 저장)
├── market_analyst.py    ✅
├── test_agent.py        ✅
├── requirements.txt     ✅
├── .env.example         ✅
└── README.md            ✅
```

### 3. API 키 (필수)
- **OPENAI_API_KEY**: OpenAI API 키 (필수)
- **TAVILY_API_KEY**: Tavily 웹 검색 API 키 (선택)
- **LANGCHAIN_API_KEY**: LangSmith 트레이싱 API 키 (선택)

---

## 🚀 설치 및 실행 방법

### Step 1: 폴더 복사
```bash
# market-analysis-agent 폴더를 원하는 위치로 복사
cp -r market-analysis-agent /path/to/your/location/
cd /path/to/your/location/market-analysis-agent
```

---

### Step 2: 가상 환경 생성 (권장)
```bash
# Python 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

---

### Step 3: 의존성 설치
```bash
# pip로 설치
pip install -r requirements.txt

# 또는 전체 skala-gai requirements.txt 사용 (더 많은 패키지 포함)
# pip install -r /path/to/skala-gai/requirements.txt
```

**필수 패키지 목록**:
- `langchain` (0.2.15+)
- `langchain-openai` (0.1.23+)
- `langchain-community` (0.2.15+)
- `langchain-text-splitters` (0.2.2+)
- `langgraph` (0.0.69+)
- `langchain-teddynote` (0.0.28+)
- `faiss-cpu` (1.8.0+)
- `pypdf` (4.3.1+)
- `python-dotenv` (1.0.1+)

---

### Step 4: 환경 변수 설정
```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집
# Windows:
notepad .env
# Mac/Linux:
nano .env
```

**.env 파일 내용**:
```bash
# 필수
OPENAI_API_KEY=your_openai_api_key_here

# 선택 (웹 검색 Fallback)
TAVILY_API_KEY=your_tavily_api_key_here

# 선택 (LangSmith 트레이싱)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=market-analysis-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key_here
```

---

### Step 5: PDF 준비
분석할 스타트업 IR 자료를 `data/` 폴더에 넣습니다:

```bash
# 예시
market-analysis-agent/
└── data/
    ├── qure_ai_ir.pdf
    ├── upstage_ir.pdf
    └── sample.pdf
```

---

### Step 6: 실행
```bash
# 테스트 스크립트 실행
python test_agent.py
```

**선택지**:
- **옵션 1**: Qure.ai 테스트 (data/qure_ai_ir.pdf 필요)
- **옵션 2**: 샘플 PDF 테스트 (독립 실행 시 `test_agent.py` 수정 필요)

---

## ⚠️ 독립 실행 시 주의사항

### 1. 샘플 PDF 경로 수정
`test_agent.py` 파일의 67-71번째 줄을 확인하세요:

```python
# 옵션 2를 주석 해제하고 샘플 PDF를 data/ 폴더에 복사
sample_pdf = "data/sample.pdf"
```

### 2. 상대 경로 문제
독립 실행 시 `../16-AgenticRAG/data/...` 경로는 작동하지 않습니다.
직접 PDF를 `data/` 폴더에 넣어주세요.

---

## 🧪 테스트

### 기본 테스트
```bash
python test_agent.py
# 옵션 1 선택 후 data/qure_ai_ir.pdf에 샘플 PDF 준비
```

### Python 코드로 직접 실행
```python
from market_analyst import market_analyst_agent

result = market_analyst_agent(
    startup_name="Qure.ai",
    document_path="data/qure_ai_ir.pdf"
)

print(result["scorecard_method"]["market_score"])  # 시장성 점수
```

---

## 🐛 문제 해결

### 1. ModuleNotFoundError
```bash
# 의존성 재설치
pip install -r requirements.txt --upgrade
```

### 2. OPENAI_API_KEY 오류
```bash
# .env 파일 확인
cat .env

# 환경 변수 로딩 테스트
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY')[:10])"
```

### 3. PDF 로딩 실패
```bash
# PDF 파일 경로 확인
ls data/

# 절대 경로 사용
python -c "import os; print(os.path.abspath('data/your_file.pdf'))"
```

---

## 📦 skala-gai와의 차이점

| 항목 | skala-gai 내부 | 독립 실행 |
|------|----------------|-----------|
| **환경 변수** | 루트의 `.env` 사용 | 자체 `.env` 필요 |
| **의존성** | 루트 `requirements.txt` | 자체 `requirements.txt` |
| **샘플 PDF** | `../16-AgenticRAG/data/` 참조 | `data/` 폴더에 직접 복사 |
| **실행 위치** | `skala-gai/market-analysis-agent/` | 어디서든 가능 |

---

## 📞 문제 발생 시

1. Python 버전 확인: `python --version` (3.11 권장)
2. 패키지 버전 확인: `pip list | grep langchain`
3. 환경 변수 확인: `.env` 파일이 올바른 위치에 있는지
4. PDF 파일 확인: `data/` 폴더에 PDF가 있는지

---

**Last Updated**: 2025-10-12
**Version**: 0.2.1
