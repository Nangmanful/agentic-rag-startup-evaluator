"""
프롬프트 템플릿 모듈
"""

from jm.prompts.bessemer_questions import get_bessemer_questions
from jm.prompts.query_rewrite_prompt import get_query_rewrite_prompt
from jm.prompts.scorecard_prompt import get_scorecard_prompt

__all__ = [
    "get_bessemer_questions",
    "get_query_rewrite_prompt",
    "get_scorecard_prompt"
]
