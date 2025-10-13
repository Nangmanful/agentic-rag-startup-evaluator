import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .huggingface import HuggingFaceEmbeddings


_module_lookup = {
    "HuggingFaceEmbeddings": "langchain_teddynote.embeddings.huggingface"
}

from .huggingface import HuggingFaceEmbeddings

def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "HuggingFaceEmbeddings"
]