"""
Evidence-grounded answer generation.

Rules enforced by system prompt and post-processing:
1. Every repository-specific claim must cite retrieved evidence.
2. If evidence is insufficient → explicit "insufficient evidence" response.
3. Never invent file paths, functions, line numbers, or dependencies.
4. Separate CONFIRMED_FROM_CODE / INFERRED_FROM_CODE / NOT_FOUND.
5. Structured response format based on detected query intent.
"""
from __future__ import annotations

import json

from app.core.enums import EvidenceKind, QueryIntent
from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMResponse
from app.retrieval.engine import RetrievalResult

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are SYNTERA, an expert Codebase Intelligence Assistant.

You ONLY answer questions based on the retrieved code evidence provided in the context.

RULES — MANDATORY:
1. Every repository-specific claim MUST be supported by a specific source location from the context.
2. Never invent file paths, function names, class names, line numbers, or dependencies.
3. If the retrieved context does not contain enough evidence, say exactly:
   "INSUFFICIENT EVIDENCE: I could not find enough evidence in the indexed repository to answer this confidently."
4. Always include source references in the format: `SymbolName @ file_path:start_line-end_line`
5. Separate claims into:
   - CONFIRMED_FROM_CODE: directly visible in retrieved source
   - INFERRED_FROM_CODE: reasonable inference from retrieved context
   - NOT_FOUND: explicitly state what was not found
6. For FLOW questions: produce a numbered step-by-step chain with source citations at each step.
7. For IMPACT questions: label all results as "POTENTIAL IMPACT" — never claim guaranteed breakage.
8. For ONBOARDING questions: provide a structured overview grounded in discovered modules.
9. Keep answers focused. Cite precisely. Do not pad with generic programming knowledge.
10. If answer involves code, quote the exact retrieved snippet — do not paraphrase code.
"""


def build_user_message(context: str, question: str, intent: str) -> str:
    intent_instructions = {
        QueryIntent.FLOW: "Produce a numbered flow with citations at each step.",
        QueryIntent.ARCHITECTURE: "Produce: OVERVIEW, MAIN MODULES, ENTRY POINTS, DATA FLOW, DEPENDENCIES. Cite evidence for each.",
        QueryIntent.IMPACT: "Produce: TARGET, DIRECT_DEPENDENTS, INDIRECT_DEPENDENTS, RELATED_TESTS, POTENTIAL_IMPACT. Label all as potential.",
        QueryIntent.ONBOARDING: "Produce: PROJECT_SUMMARY, MAIN_LANGUAGES, IMPORTANT_MODULES, ENTRY_POINTS, RECOMMENDED_READING_ORDER.",
        QueryIntent.LOCATION: "Produce: ANSWER, PRIMARY_LOCATION, FUNCTION/CLASS, LINE_RANGE, RELATED_FILES.",
        QueryIntent.SYMBOL_LOOKUP: "Produce: SYMBOL, FILE, LINE_RANGE, SIGNATURE, DESCRIPTION, CALLERS (if in context).",
        QueryIntent.CONFIGURATION: "Produce: ANSWER, CONFIG_FILES, ENVIRONMENT_VARIABLES (if found), NOTES.",
    }
    instruction = intent_instructions.get(
        intent,
        "Answer clearly with specific source citations from the retrieved context.",
    )

    return f"""{context}

---
QUESTION: {question}

INSTRUCTION: {instruction}

Answer grounded in the retrieved evidence above. Include source references for every claim.
"""


class AnswerGenerator:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def generate(
        self,
        retrieval: RetrievalResult,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """Generate an evidence-grounded answer.

        Returns a dict with: answer, citations, intent, confidence, stats.
        """
        citations = retrieval.citations()

        if not citations:
            return {
                "answer": (
                    "INSUFFICIENT EVIDENCE: No relevant code was found in the indexed repository "
                    "for this question. The repository may not contain this functionality, "
                    "or the relevant files may not have been indexed."
                ),
                "citations": [],
                "intent": retrieval.analysis.intent,
                "confidence": EvidenceKind.NOT_FOUND,
                "retrieval_stats": retrieval.stats,
            }

        user_msg = build_user_message(
            context=retrieval.context,
            question=retrieval.analysis.original,
            intent=retrieval.analysis.intent,
        )

        # Add conversation history as additional context if provided
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content'][:500]}"
                for m in conversation_history[-4:]  # last 2 exchanges
            )
            user_msg = f"CONVERSATION HISTORY:\n{history_text}\n\n{user_msg}"

        try:
            response: LLMResponse = self._llm.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_message=user_msg,
                temperature=0.05,  # Low temperature for factual grounding
                max_tokens=2048,
            )
            answer_text = response.content
        except Exception as exc:
            logger.error("llm_generation_failed", extra={"error": str(exc)})
            # Graceful degradation: return retrieved evidence without LLM answer
            evidence_lines = []
            for c in citations[:8]:
                evidence_lines.append(
                    f"• {c['symbol_name']} @ {c['file_path']}:{c['start_line']}-{c['end_line']}"
                )
            answer_text = (
                f"LLM generation failed: {exc}\n\n"
                f"Retrieved evidence:\n" + "\n".join(evidence_lines)
            )
            response = LLMResponse(content=answer_text, model="none")

        # Determine evidence kind from answer content
        answer_lower = answer_text.lower()
        if "insufficient evidence" in answer_lower or "not found" in answer_lower:
            evidence_kind = EvidenceKind.NOT_FOUND
        elif "inferred" in answer_lower or "likely" in answer_lower:
            evidence_kind = EvidenceKind.INFERRED
        else:
            evidence_kind = EvidenceKind.CONFIRMED

        return {
            "answer": answer_text,
            "citations": citations,
            "intent": retrieval.analysis.intent,
            "confidence": evidence_kind,
            "retrieval_stats": {
                **retrieval.stats,
                "llm_model": response.model,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
            },
        }
