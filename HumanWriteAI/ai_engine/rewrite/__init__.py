"""
Rewrite module for HumanWriteAI.

Provides academic writing quality improvement:
- Detects awkward sentences and stylistic issues
- Suggests clear, concise improvements while preserving meaning
- Protects citations, numbers, and scientific terminology from modification

Usage:
    from ai_engine.rewrite import improve_writing, analyze_sentence

    result = improve_writing("The experiment was conducted by the researchers...")
    for issue in result["issues"]:
        print(issue["sentence"])
        print(issue["suggestion"])
"""

from .main import improve_writing, analyze_sentence

__all__ = ["improve_writing", "analyze_sentence"]