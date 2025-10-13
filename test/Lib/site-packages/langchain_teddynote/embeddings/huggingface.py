from __future__ import annotations

import asyncio
import logging
from typing import Any, List, Optional, Union

import aiohttp
import requests
from langchain_core.embeddings import Embeddings
from langchain_core.utils import from_env, secret_from_env
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from typing_extensions import Self

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddings(BaseModel, Embeddings):
    """HuggingFace embedding model integration.

    Setup:
        Install required packages. Set environment variable ``HF_TOKEN`` or ``HUGGINGFACE_API_KEY`` if using private models.

        .. code-block:: bash

            pip install requests aiohttp
            # Optional: For private models only
            export HF_TOKEN="your-api-key"
            # or
            export HUGGINGFACE_API_KEY="your-api-key"

    Key init args — embedding params:
        model_name: str = ""
            Name of HuggingFace model to use. Not required when using custom api_url.
        api_url: Optional[str] = None
            Custom API URL. If not provided, uses HuggingFace Inference API.

    Key init args — client params:
        api_key: Optional[SecretStr] = None
            HuggingFace API key. Optional for public models.
        max_retries: int = 3
            Maximum number of retries to make when generating.
        request_timeout: Optional[float] = None
            Timeout for requests to HuggingFace API

    Instantiate:
        .. code-block:: python

            from langchain_teddynote.embeddings import HuggingFaceEmbeddings

            # Using default inference API with model name
            embed = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Using custom endpoint (no model_name or api_key required for public endpoints)
            embed = HuggingFaceEmbeddings(
                api_url="https://your-endpoint.us-east4.gcp.endpoints.huggingface.cloud"
            )
            
            # Using custom endpoint with API key for private models
            embed = HuggingFaceEmbeddings(
                api_url="https://your-private-endpoint.huggingface.cloud",
                api_key="your-api-key"
            )

    Embed single text:
        .. code-block:: python

            input_text = "The meaning of life is 42"
            vector = embed.embed_query(input_text)
            print(len(vector))

    Embed multiple texts:
        .. code-block:: python

            texts = ["hello", "goodbye"]
            vectors = embed.embed_documents(texts)
            print(len(vectors))

    Async:
        .. code-block:: python

            await embed.aembed_query(input_text)
            await embed.aembed_documents(texts)

    """

    model_name: str = ""
    """Name of HuggingFace model to use for embeddings. Not required when using custom api_url."""
    
    api_url: Optional[str] = None
    """Custom API URL. If not provided, uses HuggingFace Inference API.
    For custom endpoints, provide the full URL (e.g., 'https://your-endpoint.huggingface.cloud')."""
    
    api_key: Optional[SecretStr] = Field(
        default_factory=secret_from_env(["HF_TOKEN", "HUGGINGFACE_API_KEY"], default=None)
    )
    """HuggingFace API key. Automatically inferred from env var ``HF_TOKEN`` or ``HUGGINGFACE_API_KEY`` if not provided."""
    
    max_retries: int = 3
    """Maximum number of retries to make when generating."""
    
    request_timeout: Optional[float] = 60.0
    """Timeout for requests to HuggingFace API in seconds."""
    
    chunk_size: int = 100
    """Maximum number of texts to embed in each batch"""
    
    show_progress_bar: bool = False
    """Whether to show a progress bar when embedding."""

    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, protected_namespaces=()
    )

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        """Validate environment setup. API key is optional for public models."""
        return self

    @property
    def _api_url(self) -> str:
        """Get the API URL for the model."""
        if self.api_url:
            return self.api_url
        if not self.model_name:
            raise ValueError(
                "Either api_url or model_name must be provided. "
                "For custom endpoints, set api_url. For HuggingFace models, set model_name."
            )
        return f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"

    @property
    def _headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        return headers

    def _make_request(self, texts: List[str]) -> List[List[float]]:
        """Make synchronous request to HuggingFace API."""
        payload = {
            "inputs": texts,
            "parameters": {
                "wait_for_model": True,
                "use_cache": True,
            }
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self._api_url,
                    headers=self._headers,
                    json=payload,
                    timeout=self.request_timeout,
                )
                response.raise_for_status()
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list):
                    if len(result) > 0 and isinstance(result[0], list):
                        # Direct embeddings format
                        return result
                    elif len(result) > 0 and isinstance(result[0], dict):
                        # If response contains nested structure
                        return [item.get("embeddings", item) for item in result]
                
                # Fallback for single embedding
                if isinstance(result, dict) and "embeddings" in result:
                    return [result["embeddings"]]
                
                raise ValueError(f"Unexpected response format: {type(result)}")
                
            except requests.RequestException as e:
                if attempt == self.max_retries:
                    raise ValueError(f"Error making request to HuggingFace API: {e}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                continue

    async def _amake_request(self, texts: List[str]) -> List[List[float]]:
        """Make asynchronous request to HuggingFace API."""
        payload = {
            "inputs": texts,
            "parameters": {
                "wait_for_model": True,
                "use_cache": True,
            }
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.request_timeout)) as session:
                    async with session.post(
                        self._api_url,
                        headers=self._headers,
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        # Handle different response formats
                        if isinstance(result, list):
                            if len(result) > 0 and isinstance(result[0], list):
                                # Direct embeddings format
                                return result
                            elif len(result) > 0 and isinstance(result[0], dict):
                                # If response contains nested structure
                                return [item.get("embeddings", item) for item in result]
                        
                        # Fallback for single embedding
                        if isinstance(result, dict) and "embeddings" in result:
                            return [result["embeddings"]]
                        
                        raise ValueError(f"Unexpected response format: {type(result)}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries:
                    raise ValueError(f"Error making request to HuggingFace API: {e}")
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                continue

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs.
        
        Args:
            texts: The list of texts to embed.
            
        Returns:
            List of embeddings, one for each text.
        """
        if not texts:
            return []
            
        all_embeddings: List[List[float]] = []
        
        if self.show_progress_bar:
            try:
                from tqdm.auto import tqdm
                chunks = tqdm(
                    [texts[i:i + self.chunk_size] for i in range(0, len(texts), self.chunk_size)],
                    desc="Embedding texts"
                )
            except ImportError:
                chunks = [texts[i:i + self.chunk_size] for i in range(0, len(texts), self.chunk_size)]
        else:
            chunks = [texts[i:i + self.chunk_size] for i in range(0, len(texts), self.chunk_size)]
        
        for chunk in chunks:
            embeddings = self._make_request(chunk)
            all_embeddings.extend(embeddings)
            
        return all_embeddings

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs asynchronously.
        
        Args:
            texts: The list of texts to embed.
            
        Returns:
            List of embeddings, one for each text.
        """
        if not texts:
            return []
            
        all_embeddings: List[List[float]] = []
        
        chunks = [texts[i:i + self.chunk_size] for i in range(0, len(texts), self.chunk_size)]
        
        for chunk in chunks:
            embeddings = await self._amake_request(chunk)
            all_embeddings.extend(embeddings)
            
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed query text.
        
        Args:
            text: The text to embed.
            
        Returns:
            Embedding for the text.
        """
        return self.embed_documents([text])[0]

    async def aembed_query(self, text: str) -> List[float]:
        """Embed query text asynchronously.
        
        Args:
            text: The text to embed.
            
        Returns:
            Embedding for the text.
        """
        embeddings = await self.aembed_documents([text])
        return embeddings[0]