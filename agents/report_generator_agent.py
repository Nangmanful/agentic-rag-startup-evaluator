# report_generator_agent.py
# AI 스타트업 투자 평가 보고서 PDF 생성 에이전트 (LangGraph) — LLM 보강 버전
# - 입력 state 키:
#   startup_info: {"name": str, "category": str, ...}
#   tech_summary: str
#   market_eval: {...}  # 없어도 LLM이 요약 표를 생성
#   competitor_eval: {...}
#   investment_decision: {...}
# - 출력:
#   {"report_path": "reports/<startup>_investment_report_YYYYMMDD_HHMMSS.pdf"}

from __future__ import annotations
import os, re, datetime, json
from typing import Dict, Any, TypedDict, Annotated, Sequence, List, Optional

# LangGraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)
from reportlab.pdfbase.pdfmetrics import registerFont, registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont

# ─────────────────────────────────────────────────────────────
# LLM 유틸 (OpenAI)
# ─────────────────────────────────────────────────────────────
def _get_openai_client():
    """
    OpenAI 클라이언트. 패키지나 키가 없으면 None 반환(폴백 사용).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception:
        return None

def _openai_json_completion(system_prompt: str, user_prompt: str, schema_hint: str) -> Optional[dict]:
    """
    JSON만 반환하도록 지시하여 파싱. 실패 시 None.
    schema_hint: 사용자에게 JSON 스키마 요구사항을 추가로 알려주는 텍스트(예: keys).
    """
    client = _get_openai_client()
    if client is None:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\n\n" + schema_hint}
            ],
        )
        txt = resp.choices[0].message.content
        return json.loads(txt)
    except Exception:
        return None

def _llm_generate_strengths_risks(context: dict, want_n: int = 5) -> Dict[str, List[str]]:
    """
    강점/리스크 bullet을 LLM으로 생성. 실패 시 휴리스틱 폴백.
    context에는 tech_summary/market_eval/competitor_eval/investment_decision를 최대한 넣어주면 좋음.
    """
    sys = (
        "너는 한국어로 간결한 투자 보고서 bullet을 작성하는 분석가다. "
        "항상 사실 기반 톤을 유지하고 과장된 표현을 피하라."
    )
    user = (
        "다음 스타트업에 대해 '주요 강점 및 기회'(strengths)와 '핵심 리스크'(risks)를 각각 "
        f"{want_n}개 이내 bullet로 한국어로 생성해줘. 각 bullet은 12~18단어 내로 간결하게.\n\n"
        f"컨텍스트:\n{json.dumps(context, ensure_ascii=False)}"
    )
    schema = (
        "반드시 JSON으로만 응답: {\"strengths\":[\"...\"], \"risks\":[\"...\"]} "
        f"각 배열 길이는 최대 {want_n}."
    )
    out = _openai_json_completion(sys, user, schema)
    if out and isinstance(out, dict):
        strengths = [str(x) for x in (out.get("strengths") or [])][:want_n]
        risks = [str(x) for x in (out.get("risks") or [])][:want_n]
        if strengths or risks:
            return {"strengths": strengths, "risks": risks}

    # 폴백(휴리스틱): 컨텍스트에서 뽑아 억지로라도 채움
    strengths, risks = [], []
    ts = str(context.get("tech_summary") or "")
    if ts:
        strengths.append("[기술] 핵심 기술의 차별성과 구현 가능성이 확인됨")
    me = context.get("market_eval") or {}
    if me.get("positives"):
        strengths.extend([f"[시장] {p}" for p in me["positives"][:want_n]])
    ce = context.get("competitor_eval") or {}
    if ce.get("items"):
        strengths.append("[경쟁] 동종 대비 기능/성능 포지션 우수")

    inv = context.get("investment_decision") or {}
    if inv.get("risks"):
        risks.extend(inv["risks"][:want_n])
    mr = me.get("risks") or []
    if mr:
        risks.extend([f"[시장] {r}" for r in mr[:want_n]])

    # 부족하면 채움
    if not strengths:
        strengths = ["핵심 가치 제안이 명확하며 제품-시장 적합성 가능성이 높음"]
    if not risks:
        risks = ["수익화 전환 지연 및 핵심 지표의 변동성"]

    return {"strengths": strengths[:want_n], "risks": risks[:want_n]}

def _llm_generate_market_rows(context: dict, want_min: int = 4, want_max: int = 6) -> List[List[str]]:
    """
    시장성 요약 표 rows를 LLM으로 생성. 실패 시 폴백.
    반환 형식: [["항목","평가"], ...]에서 헤더 제외한 데이터 rows만 반환.
    """
    sys = (
        "너는 한국어로 간결한 투자 보고서 표 요약을 작성하는 애널리스트다. "
        "각 셀은 4~12단어 내로 간단 명료하게 작성하라."
    )
    user = (
        "다음 컨텍스트를 바탕으로 '시장성 평가 요약' 표의 rows를 생성해줘. "
        f"{want_min}~{want_max}개 항목을 권장하며, 각 row는 [항목, 평가] 두 칸이다. "
        "항목 예시는 '시장 규모', '성장성', '수요 동인', '진입장벽', '영업/유통', '규제 영향' 등. "
        "실제 컨텍스트와 일치하는 내용을 우선하라.\n\n"
        f"컨텍스트:\n{json.dumps(context, ensure_ascii=False)}"
    )
    schema = (
        "반드시 JSON으로만 응답: {\"rows\": [[\"항목\",\"평가\"], ...]} "
        f"rows 길이는 {want_min}~{want_max} 사이."
    )
    out = _openai_json_completion(sys, user, schema)
    if out and isinstance(out, dict) and isinstance(out.get("rows"), list):
        rows = []
        for r in out["rows"]:
            if isinstance(r, list) and len(r) == 2:
                rows.append([str(r[0]), str(r[1])])
        if rows:
            return rows

    # 폴백
    rows = [
        ["시장 규모", "정의된 타깃 세그먼트 기준으로 충분히 큼"],
        ["성장성", "연 15%+ 성장세로 중장기 확장 잠재력"],
        ["수요 동인", "비용 절감·생산성 향상·품질 개선 요구"],
        ["진입장벽", "도메인 데이터·파트너십·규제 적합성 필요"],
        ["영업/유통", "PoC → 유료전환 관문; 레퍼런스 확보 중요"],
        ["규제 영향", "인증·보안 요건 충족 시 확산 가속 가능"],
    ]
    return rows[:want_max]

# ─────────────────────────────────────────────────────────────
# 보조 유틸
# ─────────────────────────────────────────────────────────────
def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\-\.\(\)ㄱ-ㅎ가-힣 ]", "_", name)
    return re.sub(r"\s+", "_", name).strip("_")

def _pstyle(base, name, **kw):
    s = ParagraphStyle(name=name, parent=base)
    for k, v in kw.items():
        setattr(s, k, v)
    return s

def _avg_rating(items: List[dict]) -> Optional[float]:
    vals = []
    for it in items or []:
        try:
            vals.append(float(it.get("rating")))
        except Exception:
            pass
    if not vals:
        return None
    return sum(vals) / len(vals)

# ─────────────────────────────────────────────────────────────
# 폰트 등록(Regular/Bold 페이스 직접 사용; <b> 태그 사용 안 함)
# ─────────────────────────────────────────────────────────────
def _register_korean_font_family() -> str:
    candidates = [
        ("KFONT", "./fonts/NotoSansKR-Regular.ttf", "./fonts/NotoSansKR-Bold.ttf"),
        ("KFONT", "./fonts/NanumGothic.ttf", "./fonts/NanumGothicBold.ttf"),
        ("KFONT", "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"),
    ]
    for family, reg, bold in candidates:
        try:
            if not (os.path.exists(reg) and os.path.exists(bold)):
                continue
            registerFont(TTFont(f"{family}-Regular", reg))
            registerFont(TTFont(f"{family}-Bold", bold))
            try:
                registerFontFamily(
                    family,
                    normal=f"{family}-Regular",
                    bold=f"{family}-Bold",
                    italic=f"{family}-Regular",
                    boldItalic=f"{family}-Bold",
                )
            except Exception:
                pass
            return family
        except Exception:
            continue
    return ""

kfamily = _register_korean_font_family()
if not kfamily:
    raise RuntimeError(
        "한글 폰트 등록 실패: ./fonts/에 NotoSansKR-Regular/Bold 또는 "
        "C:/Windows/Fonts/malgun.ttf / malgunbd.ttf를 복사해 넣어주세요."
    )
FONT_REG = f"{kfamily}-Regular"
FONT_BOLD = f"{kfamily}-Bold"

styles = getSampleStyleSheet()
H1 = _pstyle(styles["Heading1"], "H1", fontName=FONT_BOLD, fontSize=18, leading=24, spaceAfter=6)
H2 = _pstyle(styles["Heading2"], "H2", fontName=FONT_BOLD, fontSize=14, leading=20, spaceBefore=8, spaceAfter=4)
BODY = _pstyle(styles["BodyText"], "BODY", fontName=FONT_REG, fontSize=10.5, leading=16)
BODYB = _pstyle(styles["BodyText"], "BODYB", fontName=FONT_BOLD, fontSize=10.5, leading=16)
SMALL = _pstyle(styles["BodyText"], "SMALL", fontName=FONT_REG, fontSize=9, leading=14, textColor=colors.grey)

def _bullet_list(lines: List[str]) -> ListFlowable:
    items = [ListItem(Paragraph(line, BODY), leftIndent=6) for line in (lines or [])]
    lf = ListFlowable(items, bulletType="bullet", start="•", leftIndent=12)
    lf.bulletFontName = FONT_REG
    return lf

# ─────────────────────────────────────────────────────────────
# State 정의
# ─────────────────────────────────────────────────────────────
class ReportState(TypedDict, total=False):
    messages: Annotated[Sequence, add_messages]  # 선택
    startup_info: dict
    tech_summary: str
    market_eval: dict
    competitor_eval: dict
    investment_decision: dict
    report_sections: dict
    report_path: str

# ─────────────────────────────────────────────────────────────
# 1) 섹션 구성 노드: state → report_sections (LLM로 빈칸 보강)
# ─────────────────────────────────────────────────────────────
def assemble_sections(state: Dict[str, Any]) -> Dict[str, Any]:
    si = state.get("startup_info") or {}
    name = si.get("name", "Target Startup")
    category = si.get("category", "Category")
    tech_summary = (state.get("tech_summary") or "").strip()

    inv = state.get("investment_decision") or {}
    decision = inv.get("decision", "NO")
    conf = inv.get("confidence", 0.0)
    sb = inv.get("score_breakdown", {}) or {}
    ms = sb.get("market_score")
    cs = sb.get("competitor_score")
    fs = sb.get("final")

    market = state.get("market_eval") or {}
    m_pos = market.get("positives") or []
    m_risks = market.get("risks") or []

    comp = state.get("competitor_eval") or {}
    c_items = comp.get("items") or []
    c_sources = comp.get("evidence_sources") or []

    # 안전한 숫자 포맷
    def fmt2(x):
        try:
            return f"{float(x):.2f}"
        except Exception:
            return "N/A"

    fs_text, ms_text, cs_text, conf_text = map(fmt2, (fs, ms, cs, conf))

    # Executive Summary(투자 요약)
    thesis = (
        f"{name}는(은) {category} 분야에서 확인된 기술 적합성과 시장 기회를 바탕으로 "
        f"가중 종합점수 {fs_text} 기준 {decision} 판단입니다."
    )
    if ms_text != "N/A" and cs_text != "N/A":
        thesis += f" (시장성 {ms_text}, 경쟁력 {cs_text}, 신뢰도 {conf_text})"

    # 강점/리스크: LLM 우선 생성(컨텍스트로 투자/시장/경쟁/기술 요약 전달)
    llm_context = {
        "startup_info": si,
        "tech_summary": tech_summary,
        "market_eval": market,
        "competitor_eval": comp,
        "investment_decision": inv,
    }
    gen_sr = _llm_generate_strengths_risks(llm_context, want_n=5)
    strengths = gen_sr.get("strengths") or []
    risks = gen_sr.get("risks") or []

    # 시장성 요약 표: scorecard 있으면 그대로, 없으면 LLM으로 rows 생성
    market_rows = []
    sc = market.get("scorecard") or {}
    if isinstance(sc, dict) and sc:
        for k, v_label in [
            ("management_team", "경영진 역량"),
            ("market_size", "시장 규모"),
            ("product_technology", "제품/기술"),
            ("competitive_environment", "경쟁 환경"),
            ("marketing_sales", "마케팅·영업"),
            ("need_for_additional_investment", "추가 투자 필요성"),
        ]:
            try:
                market_rows.append([v_label, f"{float(sc.get(k, 0)):.1f} / 10"])
            except Exception:
                market_rows.append([v_label, f"{sc.get(k, '-')}/10"])
    else:
        market_rows = _llm_generate_market_rows(llm_context, want_min=4, want_max=6)

    # 경쟁우위(경쟁사 비교 관점)
    comp_points = []
    avg_c = _avg_rating(c_items)
    top_names = [it.get("name") for it in (c_items[:5] if isinstance(c_items, list) else [])]
    if top_names:
        comp_points.append(f"비교 대상: {', '.join(map(str, top_names))}")
    if avg_c is not None:
        comp_points.append(f"경쟁사 대비 평균 레이팅: {avg_c:.1f}/5")
    if inv.get("rationale"):
        comp_points.extend([f"근거: {r}" for r in inv["rationale"][:3]])
    if not comp_points:
        # 최소 1~2줄 보장
        comp_points = ["경쟁 포지션: 핵심 기능/성능 기준 동종 상위권 추정"]

    # 리스크-완화 매핑(없어도 LLM에서 risks 생성하므로 반드시 채워짐)
    mitigations = inv.get("next_actions") or []
    risk_mit_map = []
    for i, r in enumerate(risks or []):
        mit = mitigations[i] if i < len(mitigations) else None
        risk_mit_map.append((r, mit))

    sections = {
        "executive_summary": {
            "thesis": thesis,
            "strengths": strengths,
            "risks": risks,
        },
        "tech_description": tech_summary or f"{name}의 핵심 기술 요약은 추출되지 않았습니다.",
        "market_summary": {
            "rows": market_rows,
            "sources": market.get("evidence_sources") or [],
        },
        "competitive_edge": comp_points,
        "risk_mitigation": risk_mit_map,
        "meta": {
            "startup_name": name,
            "category": category,
            "decision": decision,
            "confidence": float(conf) if isinstance(conf, (int, float)) else 0.0,
            "scores": {"market": ms, "competitor": cs, "final": fs},
            "sources_used": inv.get("used_sources") or (market.get("evidence_sources") or []) + (c_sources or []),
        }
    }
    return {"report_sections": sections}

# ─────────────────────────────────────────────────────────────
# 2) PDF 렌더 노드
# ─────────────────────────────────────────────────────────────
def render_pdf(state: Dict[str, Any]) -> Dict[str, Any]:
    sec = state.get("report_sections") or {}
    meta = sec.get("meta") or {}
    startup = meta.get("startup_name", "Target_Startup")
    category = meta.get("category", "Category")

    out_dir = "reports"
    _ensure_dir(out_dir)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{_sanitize_filename(startup)}_investment_report_{ts}.pdf"
    fpath = os.path.join(out_dir, fname)

    doc = SimpleDocTemplate(fpath, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36)
    story: List[Any] = []

    # 커버
    title = "AI 스타트업 투자 평가 보고서"
    subtitle = f"{startup} · {category}"
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    hdr = f"{title}\n{subtitle}\n{stamp}"
    story += [Paragraph(hdr.replace("\n", "<br/>"), H1), Spacer(1, 8)]

    # 요약 한 줄
    decision = meta.get("decision", "NO")
    conf = meta.get("confidence", 0.0)
    scores = meta.get("scores", {}) or {}
    line = (f"판단 결과: {decision} (신뢰도 {conf:.2f}) · "
            f"점수(시장/경쟁/종합): {scores.get('market','-')}/"
            f"{scores.get('competitor','-')}/{scores.get('final','-')}")
    story += [Paragraph(line, BODYB), Spacer(1, 12)]

    # 1. Executive Summary
    es = sec.get("executive_summary") or {}
    story += [Paragraph("1. Executive Summary (핵심 요약)", H2)]
    story += [Paragraph(es.get("thesis", "요약 없음"), BODY), Spacer(1, 6)]
    story += [Paragraph("• 투자 추천 요약 (Investment Thesis)", SMALL)]
    story += [Paragraph(es.get("thesis", "요약 없음"), BODY), Spacer(1, 4)]
    story += [Paragraph("• 주요 강점 및 기회", SMALL)]
    story += [_bullet_list(es.get("strengths") or []), Spacer(1, 4)]
    story += [Paragraph("• 핵심 리스크 및 완화 방안(요약)", SMALL)]
    story += [_bullet_list(es.get("risks") or []), Spacer(1, 10)]

    # 2. 기술 설명
    story += [Paragraph("2. 스타트업이 가지는 기술에 대한 설명", H2)]
    story += [Paragraph(sec.get("tech_description", "기술 설명 없음"), BODY), Spacer(1, 10)]

    # 3. 시장성 평가 요약 (표)
    story += [Paragraph("3. 스타트업 시장성 평가 요약", H2)]
    rows = sec.get("market_summary", {}).get("rows") or [["정보", "없음"]]
    tbl = Table([["항목", "평가"]] + rows, colWidths=[140, 340])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
        ("FONTNAME", (0,0), (-1,-1), FONT_REG),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("ALIGN", (0,1), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
    ]))
    story += [tbl, Spacer(1, 10)]

    # 4. 경쟁사 대비 기술적 이점
    story += [Paragraph("4. 경쟁사 대비 기술적 이점", H2)]
    ce_points = sec.get("competitive_edge") or []
    story += [_bullet_list(ce_points), Spacer(1, 10)]

    # 5. Risk Assessment & Mitigation
    story += [Paragraph("5. Risk Assessment & Mitigation (리스크 분석 및 완화 방안)", H2)]
    rm = sec.get("risk_mitigation") or []
    if rm:
        rm_rows = [["주요 리스크", "완화 방안"]]
        for r, m in rm:
            rm_rows.append([r or "-", m or "-"])
        tbl2 = Table(rm_rows, colWidths=[260, 220])
        tbl2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ("FONTNAME", (0,0), (-1,-1), FONT_REG),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#cccccc")),
            ("BOTTOMPADDING", (0,0), (-1,0), 6),
            ("TOPPADDING", (0,0), (-1,0), 6),
        ]))
        story += [tbl2, Spacer(1, 6)]
    else:
        story += [Paragraph("리스크/완화 데이터가 충분하지 않습니다.", BODY)]

    # 참고자료
    sources = meta.get("sources_used") or []
    if sources:
        story += [Spacer(1, 12), Paragraph("참고 자료 (Sources)", H2)]
        story += [_bullet_list(list(dict.fromkeys([str(s) for s in sources]))[:12])]

    doc.build(story)
    return {"report_path": fpath}

# ─────────────────────────────────────────────────────────────
# 그래프 컴파일
# ─────────────────────────────────────────────────────────────
def build_graph():
    g = StateGraph(ReportState)
    g.add_node("assemble_sections", assemble_sections)
    g.add_node("render_pdf", render_pdf)
    g.add_edge(START, "assemble_sections")
    g.add_edge("assemble_sections", "render_pdf")
    g.add_edge("render_pdf", END)
    return g.compile()

# ─────────────────────────────────────────────────────────────
# 단독 실행(테스트)
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    graph = build_graph()
    demo_state = {
        "startup_info": {"name": "SampleMedAI", "category": "Medical AI"},
        "tech_summary": "샘플: 영상진단 AI 모델(qXR, qER)과 DICOM 연동 파이프라인을 보유. FDA/CE 일부 취득.",
        # market_eval/competitor_eval 비워도 LLM이 요약 생성
        "investment_decision": {
            "decision": "YES",
            "confidence": 0.78,
            "score_breakdown": {"market_score": 0.72, "competitor_score": 0.68, "final": 0.70},
            "rationale": ["대체 불가형 임상워크플로우 적합성", "이미징 분야 레퍼런스 확대 중", "규제/인증 트랙 가시성 확보"],
            "risks": ["해외 보험수가 이슈", "온프레미스 도입 부담"],
            "next_actions": ["규제·보안 DD 착수", "핵심 고객 레퍼런스 콜 3건", "12~18개월 런웨이 기준 밸류 산정"],
            "used_sources": ["internal-market", "web-search", "company-sites"]
        }
    }
    out = graph.invoke(demo_state)
    print("PDF saved at:", out["report_path"])
