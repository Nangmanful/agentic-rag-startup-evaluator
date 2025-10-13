# Resources

`agents/resources/` 폴더는 에이전트 실행에 필요한 정적 자산을 보관합니다.

## Directory

```
agents/resources/
├── docs/   # 기술 요약·시장 분석용 참고 PDF (IR, 보고서 등)
└── fonts/  # ReportLab에서 사용할 한글 폰트 파일
```

### docs/
- `health.pdf`, `Lunit_IR_2025.pdf` 등 기술 요약과 시장 분석에서 참조할 PDF를 넣어두는 곳입니다.
- Tech Summary/Market Analyst 에이전트는 이 경로를 자동으로 스캔하여 RAG 입력으로 사용합니다.

### fonts/
- `malgun.ttf`, `malgunbd.ttf` 등 한글 폰트를 저장합니다.
- Report Generator 에이전트가 PDF 생성 시 우선적으로 이 폴더를 참조합니다.

> 필요에 따라 파일을 교체하거나 추가할 수 있으며, 경로는 코드에서 동적으로 참조됩니다.
