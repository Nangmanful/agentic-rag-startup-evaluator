# ------------------------------------------------------------
# rag_builder.py
# RAG 파이프라인 구축 - Vector Store 생성 및 검색
# ------------------------------------------------------------

import os
from typing import List, Optional
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class CompetitorRAGBuilder:
    """경쟁사 분석을 위한 RAG 파이프라인 빌더"""

    def __init__(
        self,
        data_dir: str = "competitor_analysis/data",
        vector_store_path: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        RAG 빌더 초기화

        Args:
            data_dir: PDF 문서가 저장된 디렉토리
            vector_store_path: Vector Store 저장 경로 (None이면 메모리에만 저장)
            embedding_model: OpenAI Embedding 모델명
            chunk_size: 청크 크기 (토큰 수)
            chunk_overlap: 청크 오버랩
        """
        self.data_dir = Path(data_dir)
        self.vector_store_path = vector_store_path
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.vectorstore: Optional[FAISS] = None

    def load_documents(self) -> List[Document]:
        """
        데이터 디렉토리에서 PDF 문서 로드

        Returns:
            로드된 문서 리스트
        """
        if not self.data_dir.exists():
            print(f"⚠️  데이터 디렉토리가 존재하지 않습니다: {self.data_dir}")
            print(f"📁 디렉토리를 생성합니다...")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            return []

        pdf_files = list(self.data_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"⚠️  {self.data_dir}에 PDF 파일이 없습니다.")
            return []

        print(f"📚 {len(pdf_files)}개의 PDF 파일을 로드합니다...")

        documents = []
        for pdf_file in pdf_files[:4]:  # 최대 4개 제한
            try:
                loader = PyPDFLoader(str(pdf_file))
                docs = loader.load()
                print(f"   ✓ {pdf_file.name}: {len(docs)} 페이지")
                documents.extend(docs)
            except Exception as e:
                print(f"   ✗ {pdf_file.name} 로드 실패: {e}")

        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        문서를 청크로 분할

        Args:
            documents: 원본 문서 리스트

        Returns:
            분할된 청크 리스트
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        splits = text_splitter.split_documents(documents)
        print(f"✂️  {len(documents)} 문서를 {len(splits)}개 청크로 분할했습니다.")

        return splits

    def build_vectorstore(self, documents: List[Document]) -> FAISS:
        """
        Vector Store 구축

        Args:
            documents: 분할된 문서 청크

        Returns:
            FAISS Vector Store
        """
        if not documents:
            print("⚠️  문서가 없어 빈 Vector Store를 생성합니다.")
            # 빈 벡터 스토어 생성 (더미 문서 사용)
            dummy_doc = Document(
                page_content="No industry reports available. Using web search only.",
                metadata={"source": "dummy"}
            )
            vectorstore = FAISS.from_documents([dummy_doc], self.embeddings)
        else:
            print(f"🔨 Vector Store를 구축합니다... (임베딩 생성 중)")
            vectorstore = FAISS.from_documents(documents, self.embeddings)
            print(f"✅ Vector Store 구축 완료: {len(documents)} 청크")

        self.vectorstore = vectorstore
        return vectorstore

    def save_vectorstore(self):
        """Vector Store를 디스크에 저장"""
        if self.vectorstore is None:
            print("⚠️  저장할 Vector Store가 없습니다.")
            return

        if self.vector_store_path is None:
            print("⚠️  저장 경로가 지정되지 않았습니다. 메모리에만 유지합니다.")
            return

        save_path = Path(self.vector_store_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        self.vectorstore.save_local(str(save_path))
        print(f"💾 Vector Store 저장 완료: {save_path}")

    def load_vectorstore(self) -> Optional[FAISS]:
        """저장된 Vector Store 로드"""
        if self.vector_store_path is None:
            return None

        load_path = Path(self.vector_store_path)
        if not load_path.exists():
            print(f"⚠️  저장된 Vector Store가 없습니다: {load_path}")
            return None

        try:
            vectorstore = FAISS.load_local(
                str(load_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"✅ Vector Store 로드 완료: {load_path}")
            self.vectorstore = vectorstore
            return vectorstore
        except Exception as e:
            print(f"❌ Vector Store 로드 실패: {e}")
            return None

    def build_or_load(self, force_rebuild: bool = False) -> FAISS:
        """
        Vector Store를 빌드하거나 로드

        Args:
            force_rebuild: True면 기존 Vector Store를 무시하고 재빌드

        Returns:
            FAISS Vector Store
        """
        # 기존 Vector Store 로드 시도
        if not force_rebuild and self.vector_store_path:
            vectorstore = self.load_vectorstore()
            if vectorstore is not None:
                return vectorstore

        # 새로 빌드
        print("🏗️  Vector Store를 새로 빌드합니다...")
        documents = self.load_documents()

        if documents:
            splits = self.split_documents(documents)
            vectorstore = self.build_vectorstore(splits)

            # 저장
            if self.vector_store_path:
                self.save_vectorstore()
        else:
            # 문서가 없으면 더미 Vector Store
            vectorstore = self.build_vectorstore([])

        return vectorstore

    def retrieve_context(
        self,
        query: str,
        k: int = 3,
        score_threshold: float = 0.5
    ) -> str:
        """
        쿼리에 대한 관련 컨텍스트 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            score_threshold: 유사도 임계값 (0-1)

        Returns:
            검색된 컨텍스트 문자열
        """
        if self.vectorstore is None:
            print("⚠️  Vector Store가 초기화되지 않았습니다.")
            return "No industry context available."

        try:
            # 유사도 검색
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query, k=k
            )

            # 임계값 필터링
            relevant_docs = [
                doc for doc, score in docs_with_scores
                if score >= score_threshold
            ]

            if not relevant_docs:
                return "No highly relevant industry context found."

            # 컨텍스트 결합
            context = "\n\n---\n\n".join([
                f"[Source: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}"
                for doc in relevant_docs
            ])

            return context

        except Exception as e:
            print(f"❌ 검색 중 오류 발생: {e}")
            return "Error retrieving industry context."


# -----------------------------
# 유틸리티 함수
# -----------------------------
def initialize_rag(
    data_dir: str = "competitor_analysis/data",
    force_rebuild: bool = False
) -> CompetitorRAGBuilder:
    """
    RAG 시스템 초기화 (간편 함수)

    Args:
        data_dir: 데이터 디렉토리
        force_rebuild: 강제 재빌드 여부

    Returns:
        초기화된 RAG Builder
    """
    base_dir = Path(__file__).resolve().parent
    data_dir = Path(data_dir or "data")
    if not data_dir.is_absolute():
        data_dir = (base_dir / data_dir).resolve()

    vector_store_path = data_dir / "vector_store" / "faiss_index"

    rag_builder = CompetitorRAGBuilder(
        data_dir=data_dir,
        vector_store_path=vector_store_path,
        chunk_size=500,
        chunk_overlap=50
    )

    # Vector Store 빌드 또는 로드
    rag_builder.build_or_load(force_rebuild=force_rebuild)

    return rag_builder


# -----------------------------
# 테스트 코드
# -----------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("="*80)
    print("🔧 RAG 파이프라인 테스트")
    print("="*80 + "\n")

    # RAG 초기화
    rag_builder = initialize_rag(force_rebuild=False)

    # 테스트 쿼리
    test_query = "What are the key factors for evaluating medical AI startups?"
    print(f"\n🔍 테스트 쿼리: {test_query}")
    print("-"*80)

    context = rag_builder.retrieve_context(test_query, k=2)
    print(f"\n📄 검색 결과:\n{context}\n")

    print("="*80)
    print("✅ RAG 테스트 완료")
    print("="*80)
