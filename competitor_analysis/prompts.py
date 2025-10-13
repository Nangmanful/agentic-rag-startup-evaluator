# ------------------------------------------------------------
# prompts.py
# 프롬프트 템플릿 정의
# ------------------------------------------------------------

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate


# -----------------------------
# 경쟁사 정보 충분성 평가 프롬프트
# -----------------------------
GRADE_COMPETITOR_INFO_TEMPLATE = """
You are evaluating whether sufficient competitor information has been gathered for competitive analysis.

**Target Startup:**
Name: {startup_name}
Category: {category}
Technology Summary: {tech_summary}

**Gathered Competitor Information:**
{competitor_info}

**Evaluation Criteria:**
Assess if we have enough information to perform a comprehensive competitive analysis:

1. ✓ At least 3 main competitors identified with company names
2. ✓ Technology/product details for each competitor
3. ✓ Market position information (funding, market share, customer base)
4. ✓ Regulatory approvals or certifications (FDA, CE, etc.) if applicable
5. ✓ Partnerships or key achievements

**Decision:**
- Respond 'yes' if at least criteria 1, 2, and 3 are satisfied
- Respond 'no' if more detailed information is needed

Provide your decision (yes/no) and brief reasoning.
"""

GRADE_COMPETITOR_INFO_PROMPT = PromptTemplate(
    template=GRADE_COMPETITOR_INFO_TEMPLATE,
    input_variables=["startup_name", "category", "tech_summary", "competitor_info"],
)


# -----------------------------
# 추가 검색 요청 프롬프트
# -----------------------------
SEARCH_MORE_TEMPLATE = """
You need to gather more competitor information.

**Current Situation:**
- Target Startup: {startup_name}
- Category: {category}
- Information Gap: {gap_description}

**Action Required:**
{search_instruction}

Formulate a clear search query or request to fill the information gap.
"""

SEARCH_MORE_PROMPT = PromptTemplate(
    template=SEARCH_MORE_TEMPLATE,
    input_variables=["startup_name", "category", "gap_description", "search_instruction"],
)


# -----------------------------
# 경쟁사 비교 분석 프롬프트
# -----------------------------
COMPETITOR_ANALYSIS_TEMPLATE = """
You are a venture capital analyst performing competitive analysis for startup investment evaluation.

**Target Startup:**
Name: {startup_name}
Category: {category}
Technology Summary: {tech_summary}

**Competitor Information Gathered:**
{competitor_info}

**Industry Context (from RAG):**
{rag_context}

---

**Analysis Framework:**
Compare the target startup against competitors across these 6 dimensions with their respective weights:

**1. Technology Differentiation (30%)**
   - Unique technical capabilities and innovations
   - Technology barriers to entry
   - Patents and proprietary algorithms
   - R&D capabilities

**2. Market Entry Barriers (25%)**
   - Regulatory approvals (FDA 510(k), CE Mark, etc.)
   - Intellectual property portfolio
   - Network effects and ecosystem lock-in
   - First-mover advantages

**3. Funding & Growth (20%)**
   - Total funding raised and funding rounds
   - Growth trajectory (revenue, users, deployments)
   - Financial runway and stability
   - Investor quality and backing

**4. Partnerships & Ecosystem (15%)**
   - Strategic partnerships (hospitals, healthcare providers)
   - Customer base size and quality
   - Geographic market penetration
   - Integration with existing healthcare systems

**5. Validation & Certification (5%)**
   - Clinical validation studies
   - Peer-reviewed publications
   - Real-world evidence and outcomes
   - Industry awards and recognitions

**6. Brand Recognition (5%)**
   - Market presence and visibility
   - Industry reputation
   - Thought leadership
   - Media coverage

---

**Required Output Format:**

### Competitive Positioning
[Provide overall assessment: Leader/Strong Challenger/Competitive/Weak/Very Weak]

### Key Competitive Advantages
[List 3-5 specific advantages with evidence]
- Advantage 1: [description + evidence]
- Advantage 2: [description + evidence]
- ...

### Key Competitive Disadvantages
[List 3-5 specific disadvantages with evidence]
- Disadvantage 1: [description + evidence]
- Disadvantage 2: [description + evidence]
- ...

### Dimension-by-Dimension Analysis
**Technology Differentiation (30%):**
[Comparative assessment vs competitors]

**Market Entry Barriers (25%):**
[Comparative assessment vs competitors]

**Funding & Growth (20%):**
[Comparative assessment vs competitors]

**Partnerships & Ecosystem (15%):**
[Comparative assessment vs competitors]

**Validation & Certification (5%):**
[Comparative assessment vs competitors]

**Brand Recognition (5%):**
[Comparative assessment vs competitors]

### Competitive Summary
[2-3 sentence summary of competitive position and outlook]

---

**Important:**
- Be objective and evidence-based
- Cite specific facts and numbers when available
- Compare directly with named competitors
- Consider both current position and future potential
"""

COMPETITOR_ANALYSIS_PROMPT = ChatPromptTemplate.from_template(COMPETITOR_ANALYSIS_TEMPLATE)


# -----------------------------
# 분석 결과 파싱 프롬프트
# -----------------------------
PARSE_ANALYSIS_TEMPLATE = """
Parse the competitive analysis below and extract key information in a structured format.

**Competitive Analysis:**
{analysis}

---

**Task:**
Extract and structure the following information from the analysis:

1. **Competitive Positioning**:
   State the overall market position as one of: Leader/Strong Challenger/Competitive/Weak/Very Weak

2. **Competitive Advantages**:
   List 3-5 key competitive advantages with evidence (as mentioned in the analysis)

3. **Competitive Disadvantages**:
   List 3-5 key competitive disadvantages with evidence (as mentioned in the analysis)

4. **Competitive Summary**:
   Provide a 2-3 sentence summary of the competitive position and outlook

Be objective and base your extraction directly on the analysis provided.
"""

PARSE_ANALYSIS_PROMPT = PromptTemplate(
    template=PARSE_ANALYSIS_TEMPLATE,
    input_variables=["analysis"],
)


# -----------------------------
# RAG 검색 쿼리 생성 프롬프트
# -----------------------------
RAG_QUERY_TEMPLATE = """
Generate an effective search query to retrieve relevant industry context from our knowledge base.

**Target Startup:** {startup_name}
**Category:** {category}
**Analysis Focus:** {focus_area}

Generate a concise search query (1-2 sentences) to find relevant information about:
- Industry trends and competitive landscape
- Evaluation frameworks and benchmarks
- Regulatory requirements and standards
- Investment criteria in this sector

Search Query:
"""

RAG_QUERY_PROMPT = PromptTemplate(
    template=RAG_QUERY_TEMPLATE,
    input_variables=["startup_name", "category", "focus_area"],
)
