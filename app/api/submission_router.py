"""Submission gating endpoints using rubric evaluation."""

from fastapi import APIRouter, HTTPException
from typing import List

from app.agents.check_rubric_agent import CheckRubricAgent
from app.schemas.schemas import (
    RubricEvaluationResponse,
    SubmissionSubmitRequest,
    SubmissionSubmitResponse,
    SubmissionResubmitRequest,
    SubmissionResubmitResponse,
    BlockingCriterion,
)

router = APIRouter(
    prefix="/api/v1/submissions",
    tags=["📝 Submissions (Rubric Gate)"],
)

rubric_agent = CheckRubricAgent()


def _check_gate(rubric: RubricEvaluationResponse, gate) -> (bool, List[BlockingCriterion]):
    """Return (allowed, blocking_criteria)."""
    blocking: List[BlockingCriterion] = []
    # Overall score gate
    if rubric.overall_score < gate.min_overall_score:
        # Not a per-criterion block, but keep reason at top-level
        pass

    # Per-criterion minimums (scores are 0..10)
    min_map = gate.min_criterion_scores or {}
    if min_map:
        for c in rubric.criteria:
            req_min = min_map.get(c.id)
            if req_min is not None and c.score < req_min:
                blocking.append(BlockingCriterion(
                    id=c.id,
                    question=c.question,
                    score=c.score,
                    required_min=float(req_min),
                ))

    allowed = rubric.overall_score >= gate.min_overall_score and len(blocking) == 0
    return allowed, blocking


@router.post("/submit", response_model=SubmissionSubmitResponse, summary="Gate submit by rubric")
async def submit_with_rubric(req: SubmissionSubmitRequest) -> SubmissionSubmitResponse:
    try:
        result = await rubric_agent.process(req.rubric_request.dict())
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rubric evaluation failed"))
        data = RubricEvaluationResponse(**result.get("data", {}))

        allowed, blocking = _check_gate(data, req.gate)
        reason = (
            "Passed rubric gate"
            if allowed
            else (
                f"Overall {data.overall_score} < min {req.gate.min_overall_score}"
                if data.overall_score < req.gate.min_overall_score
                else "One or more criteria below required minimum"
            )
        )

        suggestions: List[str] = []
        # Suggest actions from rubric next_steps if blocked
        if not allowed:
            suggestions = list(data.next_steps or [])

        return SubmissionSubmitResponse(
            allowed=allowed,
            decision_reason=reason,
            overall_score=data.overall_score,
            overall_rating=data.overall_rating,
            blocking_criteria=blocking,
            rubric=data,
            suggestions=suggestions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resubmit", response_model=SubmissionResubmitResponse, summary="Gate resubmit by rubric improvement")
async def resubmit_with_rubric(req: SubmissionResubmitRequest) -> SubmissionResubmitResponse:
    try:
        result = await rubric_agent.process(req.rubric_request.dict())
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rubric evaluation failed"))
        data = RubricEvaluationResponse(**result.get("data", {}))

        improvement = round(data.overall_score - req.previous_overall_score, 2)
        allowed_by_improvement = improvement >= req.improvement_threshold
        allowed_by_gate, blocking = _check_gate(data, req.gate)
        allowed = allowed_by_improvement and allowed_by_gate

        if allowed:
            reason = f"Improved by {improvement} >= {req.improvement_threshold} and passed gate"
        else:
            if not allowed_by_improvement:
                reason = f"Improvement {improvement} < required {req.improvement_threshold}"
            elif data.overall_score < req.gate.min_overall_score:
                reason = f"Overall {data.overall_score} < min {req.gate.min_overall_score}"
            else:
                reason = "One or more criteria below required minimum"

        suggestions: List[str] = []
        if not allowed:
            suggestions = list(data.next_steps or [])

        return SubmissionResubmitResponse(
            allowed=allowed,
            decision_reason=reason,
            overall_score=data.overall_score,
            overall_rating=data.overall_rating,
            improvement=improvement,
            blocking_criteria=blocking,
            rubric=data,
            suggestions=suggestions,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


