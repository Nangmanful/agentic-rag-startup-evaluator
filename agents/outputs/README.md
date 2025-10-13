# Generated Outputs

`agents/outputs/`는 에이전트 실행 결과물을 보관하는 저장소입니다.

## Structure

```
agents/outputs/
└── reports/   # Report Generator가 생성한 PDF 투자 보고서 저장 위치
```

### reports/
- 파일명 패턴: `<startup>_investment_report_<YYYYMMDD_HHMMSS>.pdf`
- `agents/core/report_generator_agent.py`가 실행될 때 자동으로 이 폴더를 생성하고 파일을 기록합니다.
- 필요 시 버전 관리에 포함하지 않거나 별도 저장소로 이동해도 됩니다.
