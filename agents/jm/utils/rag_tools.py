"""
RAG 파이프라인 구축 유틸리티
Reference: 15-RAG/01-Basic-PDF.ipynb, 16-AgenticRAG/01-NaiveRAG.ipynb
"""

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.retrievers import BaseRetriever


def format_docs(docs) -> str:
    """문서 리스트를 문자열로 포맷팅"""
    return "\n\n".join([doc.page_content for doc in docs])


def setup_rag_pipeline(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> BaseRetriever:
    """
    RAG 파이프라인 구축 (1회만 실행)

    Args:
        pdf_path: PDF 파일 경로
        chunk_size: 청크 크기
        chunk_overlap: 청크 오버랩

    Returns:
        BaseRetriever: FAISS 기반 retriever
    """

    print(f"📄 [RAG Setup] PDF 로딩: {pdf_path}")

    # 1. PDF 로딩
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    print(f"✅ [RAG Setup] {len(documents)}개 페이지 로드 완료")

    # 2. 텍스트 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    splits = text_splitter.split_documents(documents)

    print(f"✅ [RAG Setup] {len(splits)}개 청크로 분할 완료")

    # 3. 임베딩 생성 및 FAISS 벡터 스토어 구축
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(splits, embeddings)

    print(f"✅ [RAG Setup] FAISS 벡터 스토어 구축 완료")

    # 4. Retriever 생성
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}  # 상위 5개 문서 검색
    )

    print(f"🚀 [RAG Setup] Retriever 준비 완료 (검색 k=5)")

    return retriever


def retrieve_with_sources(retriever: BaseRetriever, query: str) -> tuple[str, list]:
    """
    문서 검색 및 출처 추출

    Args:
        retriever: FAISS Retriever
        query: 검색 질문

    Returns:
        tuple: (포맷팅된 문서 내용, 출처 리스트)
    """

    # 문서 검색
    docs = retriever.invoke(query)

    # 문서 내용 포맷팅
    formatted_docs = format_docs(docs)

    # 출처 추출 (페이지 번호)
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "unknown")
        sources.append(f"{source} (page {page})")

    # 중복 제거
    unique_sources = list(set(sources))

    return formatted_docs, unique_sources
