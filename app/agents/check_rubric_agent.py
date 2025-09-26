"""Agent: CheckRubricAgent - Evaluates a topic proposal against a 10-criterion rubric."""

import json
import time
from typing import Any, Dict, List

from app.agents.base_agent import BaseAgent, AgentResult


class CheckRubricAgent(BaseAgent):
    """Agent responsible for rubric-based evaluation of a topic proposal."""

    def __init__(self):
        super().__init__("CheckRubricAgent", "gemini-2.0-flash")
        # Define rubric criteria and default equal weights
        self.criteria = [
            {
                "id": "title_alignment",
                "question": "Tên đề tài có phản ánh định hướng nghiên cứu và phát triển sản phẩm?",
                "weight": 0.10,
            },
            {
                "id": "context_defined",
                "question": "Ngữ cảnh nơi sản phẩm triển khai có được xác định cụ thể?",
                "weight": 0.10,
            },
            {
                "id": "problem_clarity",
                "question": "Vấn đề cần giải quyết có được mô tả rõ ràng, là động lực ra đời sản phẩm?",
                "weight": 0.10,
            },
            {
                "id": "actors_identified",
                "question": "Người dùng chính (main actors) có được xác định?",
                "weight": 0.10,
            },
            {
                "id": "flows_usecases",
                "question": "Các luồng xử lý và chức năng chính (use cases) có được mô tả?",
                "weight": 0.10,
            },
            {
                "id": "customers_sponsors",
                "question": "Khách hàng / người tài trợ của đề tài có được xác định?",
                "weight": 0.05,
            },
            {
                "id": "approach_fit",
                "question": "Hướng tiếp cận (lý thuyết), công nghệ áp dụng và deliverables có phù hợp?",
                "weight": 0.15,
            },
            {
                "id": "scope_feasibility",
                "question": "Phạm vi, độ lớn sản phẩm có khả thi cho 3-5 SV trong 14 tuần? Có packages?",
                "weight": 0.15,
            },
            {
                "id": "technical_complexity_fit",
                "question": "Độ phức tạp và tính kỹ thuật có phù hợp chuẩn Capstone SE?",
                "weight": 0.10,
            },
            {
                "id": "applicability_feasibility",
                "question": "Tính ứng dụng thực tế và tính khả thi công nghệ trong giới hạn thời gian?",
                "weight": 0.05,
            },
        ]

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a topic proposal against the rubric.

        Expected input_data keys include:
        - topic_request: {title, description, objectives, methodology, expected_outcomes, requirements, supervisor_id, semester_id, ...}
        - Optional fields such as context, problem_statement, main_actors, main_flows, customers_sponsors, approach_theory, applied_technology,
          main_deliverables, scope, size_of_product, packages_breakdown, complexity, applicability, feasibility, proposal_text
        """
        started_at = time.time()
        try:
            self.log_info("Starting rubric evaluation")

            # Build evaluation prompt
            prompt = self._build_prompt(input_data)

            # Ask the LLM for structured JSON evaluation
            ai_text = await self.generate_text(
                prompt,
                temperature=0.4,
                max_tokens=1800,
                top_p=0.9,
                top_k=40,
            )

            parsed = self._parse_ai_response(ai_text)

            # Normalize and compute overall score using our canonical weights
            normalized = self._normalize_evaluation(parsed)
            normalized["processing_time"] = round(time.time() - started_at, 3)

            return AgentResult(
                success=True,
                data=normalized,
                metadata={
                    "criteria_defined": len(self.criteria),
                    "model": self.model_name,
                },
            ).to_dict()

        except Exception as e:
            self.log_error("Error in rubric evaluation", e)
            # Provide a minimal fallback so API remains resilient
            fallback = self._fallback_result(input_data, processing_time=round(time.time() - started_at, 3))
            return AgentResult(success=True, data=fallback).to_dict()

    def _build_prompt(self, input_data: Dict[str, Any]) -> str:
        tr = input_data.get("topic_request", {}) or {}
        # Optional extended fields
        context = input_data.get("context", "") or ""
        problem = input_data.get("problem_statement", "") or ""
        main_actors = input_data.get("main_actors", []) or []
        main_flows = input_data.get("main_flows", "") or ""
        customers_sponsors = input_data.get("customers_sponsors", "") or ""
        approach_theory = input_data.get("approach_theory", "") or ""
        applied_technology = input_data.get("applied_technology", "") or ""
        deliverables = input_data.get("main_deliverables", "") or ""
        scope = input_data.get("scope", "") or ""
        size = input_data.get("size_of_product", "") or ""
        packages = input_data.get("packages_breakdown", []) or []
        complexity = input_data.get("complexity", "") or ""
        applicability = input_data.get("applicability", "") or ""
        feasibility = input_data.get("feasibility", "") or ""
        proposal_text = input_data.get("proposal_text", "") or ""

        criteria_text = "\n".join(
            [f"- {c['id']}: {c['question']} (weight={c['weight']})" for c in self.criteria]
        )

        main_actors_text = ", ".join(main_actors) if isinstance(main_actors, list) else str(main_actors)
        packages_text = ", ".join(packages) if isinstance(packages, list) else str(packages)

        prompt = f"""
Bạn là giảng viên phản biện đồ án Capstone ngành KTPM. Hãy ĐÁNH GIÁ đề tài dựa trên RUBRIC 10 tiêu chí dưới đây. Trả về KẾT QUẢ DUY NHẤT ở dạng JSON HỢP LỆ.

=== DỮ LIỆU ĐỀ XUẤT ===
Tiêu đề: {tr.get('title','')}
Mô tả: {tr.get('description','')}
Mục tiêu: {tr.get('objectives','')}
Phương pháp: {tr.get('methodology','')}
Kết quả mong đợi: {tr.get('expected_outcomes','')}
Yêu cầu/Kỹ thuật: {tr.get('requirements','')}

Ngữ cảnh triển khai: {context}
Vấn đề cần giải quyết: {problem}
Người dùng chính: {main_actors_text}
Luồng xử lý / Chức năng chính: {main_flows}
Khách hàng / Nhà tài trợ: {customers_sponsors}
Hướng tiếp cận (lý thuyết): {approach_theory}
Công nghệ áp dụng: {applied_technology}
Các deliverables chính: {deliverables}
Phạm vi: {scope}
Độ lớn sản phẩm: {size}
Phân rã packages: {packages_text}
Độ phức tạp kỹ thuật: {complexity}
Tính ứng dụng: {applicability}
Tính khả thi (thời gian/công nghệ): {feasibility}

Toàn văn thuyết minh (nếu có):\n{proposal_text}

=== RUBRIC (0-10 cho mỗi tiêu chí, dùng trọng số như sau) ===
{criteria_text}

YÊU CẦU NGHIÊM NGẶT:
- Chỉ trả về JSON hợp lệ, không có văn bản thừa.
- Mỗi tiêu chí: id, question, score_0_to_10 (0..10), weight, assessment, evidence, recommendations (3-5 ngắn gọn).
- Tính overall.score_0_to_100 bằng tổng có trọng số (mỗi điểm nhân 10 rồi nhân weight). Gán rating: >=85 Excellent, >=70 Good, >=55 Fair, else Poor.
- Cung cấp: missing_fields, risks (ngắn gọn), next_steps (3-5 hành động cụ thể).

MẪU JSON TRẢ VỀ:
{{
  "overall": {{
    "score_0_to_100": 0,
    "rating": "Poor|Fair|Good|Excellent",
    "summary": "..."
  }},
  "criteria": [
    {{
      "id": "title_alignment",
      "question": "...",
      "score_0_to_10": 0,
      "weight": 0.10,
      "assessment": "...",
      "evidence": "...",
      "recommendations": ["..."]
    }}
  ],
  "missing_fields": ["..."],
  "risks": ["..."],
  "next_steps": ["..."]
}}
"""
        return prompt

    def _parse_ai_response(self, ai_text: str) -> Dict[str, Any]:
        text = (ai_text or "").strip()
        if not text:
            return {}
        # Try direct JSON parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Fallback: extract outermost JSON block
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
        except Exception:
            return {}
        return {}

    def _normalize_evaluation(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        # Prepare per-criterion list aligned to our canonical rubric
        evaluated: List[Dict[str, Any]] = []
        parsed_criteria = {c.get("id"): c for c in (parsed.get("criteria") or []) if isinstance(c, dict)}

        for c in self.criteria:
            cid = c["id"]
            pc = parsed_criteria.get(cid, {})
            score = pc.get("score_0_to_10")
            try:
                score = float(score)
            except Exception:
                score = 0.0
            score = max(0.0, min(10.0, score))

            evaluated.append(
                {
                    "id": cid,
                    "question": c["question"],
                    "score": score,
                    "weight": float(c["weight"]),
                    "assessment": pc.get("assessment") or "",
                    "evidence": pc.get("evidence") or "",
                    "recommendations": list(pc.get("recommendations") or [])[:5],
                }
            )

        # Compute weighted overall score (0..100)
        overall = 0.0
        for item in evaluated:
            overall += (item["score"] * 10.0) * item["weight"]
        overall = round(overall, 2)

        if overall >= 85:
            rating = "Excellent"
        elif overall >= 70:
            rating = "Good"
        elif overall >= 55:
            rating = "Fair"
        else:
            rating = "Poor"

        summary = (
            (parsed.get("overall") or {}).get("summary")
            or "Đánh giá tổng quan theo 10 tiêu chí rubric về tính phù hợp, khả thi và giá trị ứng dụng."
        )

        return {
            "overall_score": overall,
            "overall_rating": rating,
            "summary": summary,
            "criteria": evaluated,
            "missing_fields": list(parsed.get("missing_fields") or []),
            "risks": list(parsed.get("risks") or []),
            "next_steps": list(parsed.get("next_steps") or []),
        }

    def _fallback_result(self, input_data: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        # Minimal safe default with zero scores but still informative
        evaluated = [
            {
                "id": c["id"],
                "question": c["question"],
                "score": 0.0,
                "weight": float(c["weight"]),
                "assessment": "Không đủ dữ liệu để đánh giá.",
                "evidence": "",
                "recommendations": [
                    "Bổ sung mô tả rõ ràng cho tiêu chí này",
                ],
            }
            for c in self.criteria
        ]

        return {
            "overall_score": 0.0,
            "overall_rating": "Poor",
            "summary": "Không thể chấm tự động do thiếu dữ liệu hoặc lỗi hệ thống.",
            "criteria": evaluated,
            "missing_fields": [
                "title", "description", "objectives", "methodology", "context", "problem_statement"
            ],
            "risks": ["Thiếu thông tin đầu vào"],
            "next_steps": [
                "Bổ sung mô tả ngữ cảnh triển khai",
                "Làm rõ vấn đề và người dùng chính",
                "Xác định luồng xử lý và deliverables",
            ],
            "processing_time": processing_time,
        }


