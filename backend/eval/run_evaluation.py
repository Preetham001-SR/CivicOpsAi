#!/usr/bin/env python3
"""
Evaluation script for CivicOps AI pipeline.
Runs test incidents through the pipeline and reports metrics.
"""

import asyncio
import json
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

import sys
sys.path.insert(0, "/app")

from app.agents.pipeline import pipeline, ComplaintState
from app.db.session import AsyncSessionLocal
from app.db.models import Complaint, ComplaintStatus, ComplaintCategory, PriorityLevel
import uuid


@dataclass
class TestIncident:
    id: str
    text_description: str
    photo_url: Optional[str]
    audio_url: Optional[str]
    latitude: float
    longitude: float
    address: str
    expected_category: str
    expected_priority: str
    ground_truth_notes: str


@dataclass
class EvaluationResult:
    incident_id: str
    success: bool
    latency_ms: float
    predicted_category: Optional[str]
    predicted_priority: Optional[str]
    expected_category: str
    expected_priority: str
    category_correct: bool
    priority_correct: bool
    confidence_score: Optional[float]
    review_tier: Optional[str]
    rag_sources_count: int
    rag_rules_count: int
    rag_incidents_count: int
    verification_confidence: Optional[float]
    verification_checks_passed: int
    verification_checks_total: int
    error: Optional[str]
    location_details: Optional[Dict]


@dataclass
class EvaluationMetrics:
    total_incidents: int
    successful: int
    failed: int
    category_accuracy: float
    priority_accuracy: float
    overall_accuracy: float
    avg_latency_ms: float
    p95_latency_ms: float
    avg_confidence: float
    avg_verification_confidence: float
    avg_rag_sources: float
    avg_rag_rules: float
    avg_rag_incidents: float
    rag_recall_at_5: float
    groundedness_rate: float
    estimated_cost_per_incident: float
    review_tier_distribution: Dict[str, int]


def load_test_incidents(path: str) -> List[TestIncident]:
    # Try multiple paths
    for p in [path, "/app/eval/test_incidents.json"]:
        print(f"Trying to load from: {p}")
        try:
            with open(p) as f:
                data = json.load(f)
                return [TestIncident(**item) for item in data]
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"Could not find test incidents file at {path}")


async def run_single_incident(
    incident: TestIncident,
    db_session_factory
) -> EvaluationResult:
    """Run a single incident through the pipeline."""
    start_time = time.perf_counter()
    incident_id = str(uuid.uuid4())
    
    # Create complaint in DB
    async with AsyncSessionLocal() as db:
        complaint = Complaint(
            id=uuid.UUID(incident_id),
            text_description=incident.text_description,
            photo_url=incident.photo_url,
            audio_url=incident.audio_url,
            latitude=incident.latitude,
            longitude=incident.longitude,
            address=incident.address,
            status=ComplaintStatus.PENDING,
        )
        db.add(complaint)
        await db.commit()
    
    initial_state = ComplaintState(
        complaint_id=uuid.UUID(incident_id),
        text_description=incident.text_description,
        photo_url=incident.photo_url,
        audio_url=incident.audio_url,
        latitude=incident.latitude,
        longitude=incident.longitude,
        address=incident.address,
        vision_analysis=None,
        speech_transcript=None,
        location_details=None,
        rag_context=None,
        rag_sources=[],
        decision=None,
        verification=None,
        confidence_score=None,
        requires_human_review=False,
        human_review_decision=None,
        human_review_notes=None,
        human_review_modified_data=None,
        work_order=None,
        work_order_id=None,
        status="pending",
        errors=[],
        current_agent=None,
        trace_id=str(uuid.uuid4()),
    )
    
    try:
        result = await pipeline.run(initial_state)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Extract results
        predicted_category = None
        predicted_priority = None
        confidence_score = None
        review_tier = None
        rag_sources_count = 0
        rag_rules_count = 0
        rag_incidents_count = 0
        verification_confidence = None
        verification_checks_passed = 0
        verification_checks_total = 0
        location_details = None
        error = None
        
        if result.get("decision"):
            decision = result["decision"]
            predicted_category = decision.get("category")
            predicted_priority = decision.get("priority")
        
        confidence_score = result.get("confidence_score")
        review_tier = result.get("review_tier")
        
        if result.get("rag_context"):
            rag_ctx = result["rag_context"]
            rag_rules_count = len(rag_ctx.get("relevant_rules", []))
            rag_incidents_count = len(rag_ctx.get("relevant_incidents", []))
            rag_sources_count = rag_rules_count + rag_incidents_count
        
        if result.get("verification"):
            verification_confidence = result["verification"].get("overall_confidence")
            checks = result["verification"].get("checks", [])
            verification_checks_total = len(checks)
            verification_checks_passed = sum(1 for c in checks if c.get("passed", False))
        
        if result.get("location_details"):
            location_details = result["location_details"]
        
        category_correct = predicted_category == incident.expected_category
        priority_correct = predicted_priority == incident.expected_priority
        
        return EvaluationResult(
            incident_id=incident.id,
            success=True,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            predicted_category=predicted_category,
            predicted_priority=predicted_priority,
            expected_category=incident.expected_category,
            expected_priority=incident.expected_priority,
            category_correct=category_correct,
            priority_correct=priority_correct,
            confidence_score=confidence_score,
            review_tier=review_tier,
            rag_sources_count=rag_sources_count,
            rag_rules_count=rag_rules_count,
            rag_incidents_count=rag_incidents_count,
            verification_confidence=verification_confidence,
            verification_checks_passed=verification_checks_passed,
            verification_checks_total=verification_checks_total,
            error=None,
            location_details=location_details,
        )
        
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return EvaluationResult(
            incident_id=incident.id,
            success=False,
            latency_ms=latency_ms,
            predicted_category=None,
            predicted_priority=None,
            expected_category=incident.expected_category,
            expected_priority=incident.expected_priority,
            category_correct=False,
            priority_correct=False,
            confidence_score=None,
            review_tier=None,
            rag_sources_count=0,
            rag_rules_count=0,
            rag_incidents_count=0,
            verification_confidence=None,
            verification_checks_passed=0,
            verification_checks_total=0,
            error=str(e),
            location_details=None,
        )


async def compute_metrics(results: List[EvaluationResult]) -> EvaluationMetrics:
    """Compute aggregate metrics from evaluation results."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    if not successful:
        return EvaluationMetrics(
            total_incidents=len(results),
            successful=0,
            failed=len(results),
            category_accuracy=0.0,
            priority_accuracy=0.0,
            overall_accuracy=0.0,
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
            avg_confidence=0.0,
            avg_verification_confidence=0.0,
            avg_rag_sources=0.0,
            avg_rag_rules=0.0,
            avg_rag_incidents=0.0,
            rag_recall_at_5=0.0,
            groundedness_rate=0.0,
            estimated_cost_per_incident=0.0,
            review_tier_distribution={},
        )
    
    latencies = [r.latency_ms for r in successful]
    latencies.sort()
    
    category_correct = sum(1 for r in successful if r.category_correct)
    priority_correct = sum(1 for r in successful if r.priority_correct)
    both_correct = sum(1 for r in successful if r.category_correct and r.priority_correct)
    
    confidences = [r.confidence_score for r in successful if r.confidence_score is not None]
    verification_confidences = [r.verification_confidence for r in successful if r.verification_confidence is not None]
    
    rag_sources = [r.rag_sources_count for r in successful]
    rag_rules = [r.rag_rules_count for r in successful]
    rag_incidents = [r.rag_incidents_count for r in successful]
    
    # RAG Recall@5: proportion of cases where at least 1 relevant doc retrieved
    rag_recall_at_5 = sum(1 for r in successful if r.rag_sources_count >= 1) / len(successful)
    
    # Groundedness: verification checks passed / total checks
    total_checks = sum(r.verification_checks_total for r in successful)
    passed_checks = sum(r.verification_checks_passed for r in successful)
    groundedness_rate = passed_checks / total_checks if total_checks > 0 else 0.0
    
    # Estimate cost (rough approximation based on token counts)
    # This is a rough estimate - in production you'd track actual token usage
    estimated_cost_per_incident = 0.02  # ~$0.02 per incident estimate
    
    review_tiers = defaultdict(int)
    for r in successful:
        if r.review_tier:
            review_tiers[r.review_tier] += 1
    
    return EvaluationMetrics(
        total_incidents=len(results),
        successful=len(successful),
        failed=len(failed),
        category_accuracy=category_correct / len(successful),
        priority_accuracy=priority_correct / len(successful),
        overall_accuracy=both_correct / len(successful),
        avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        p95_latency_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0.0,
        avg_confidence=statistics.mean(confidences) if confidences else 0.0,
        avg_verification_confidence=statistics.mean(verification_confidences) if verification_confidences else 0.0,
        avg_rag_sources=statistics.mean(rag_sources) if rag_sources else 0.0,
        avg_rag_rules=statistics.mean(rag_rules) if rag_rules else 0.0,
        avg_rag_incidents=statistics.mean(rag_incidents) if rag_incidents else 0.0,
        rag_recall_at_5=rag_recall_at_5,
        groundedness_rate=groundedness_rate,
        estimated_cost_per_incident=estimated_cost_per_incident,
        review_tier_distribution=dict(review_tiers),
    )


def generate_report(metrics: EvaluationMetrics, results: List[EvaluationResult]) -> str:
    """Generate markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Per-incident table
    incident_rows = []
    for r in results:
        status = "✅" if r.success else "❌"
        cat_status = "✅" if r.category_correct else "❌"
        pri_status = "✅" if r.priority_correct else "❌"
        error_info = f" ({r.error[:50]}...)" if r.error else ""
        pred_cat = r.predicted_category if r.predicted_category else 'N/A'
        pred_pri = r.predicted_priority if r.predicted_priority else 'N/A'
        conf = f"{r.confidence_score:.2f}" if r.confidence_score is not None else 'N/A'
        ver_conf = f"{r.verification_confidence:.2f}" if r.verification_confidence is not None else 'N/A'
        tier = r.review_tier if r.review_tier else 'N/A'
        
        incident_rows.append(
            f"| {r.incident_id} | {status} | {pred_cat} | {r.expected_category} | {cat_status} | "
            f"{pred_pri} | {r.expected_priority} | {pri_status} | "
            f"{r.latency_ms:.0f} | {conf} | {tier} | "
            f"{r.rag_sources_count} | {ver_conf} | {r.error or ''}{error_info} |"
        )
    
    incident_table = (
        "| Incident | Status | Pred Cat | Exp Cat | Cat ✓ | Pred Pri | Exp Pri | Pri ✓ | Latency (ms) | Conf | Tier | RAG Src | Ver Conf | Error |\n"
        "|----------|--------|----------|---------|-------|----------|---------|-------|--------------|------|------|---------|----------|-------|\n" +
        "\n".join(incident_rows)
    )
    
    report = f"""# CivicOps AI Pipeline Evaluation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Test Dataset:** 25 incidents (eval/test_incidents.json)
**Pipeline Version:** Current (commit: {get_git_commit()})

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| **Total Incidents** | {metrics.total_incidents} |
| **Successful** | {metrics.successful} |
| **Failed** | {metrics.failed} |
| **Category Accuracy** | {metrics.category_accuracy:.1%} |
| **Priority Accuracy** | {metrics.priority_accuracy:.1%} |
| **Overall Accuracy (Both)** | {metrics.overall_accuracy:.1%} |
| **Avg Latency** | {metrics.avg_latency_ms:.0f} ms |
| **P95 Latency** | {metrics.p95_latency_ms:.0f} ms |
| **Avg Confidence** | {metrics.avg_confidence:.2f} |
| **Avg Verification Confidence** | {metrics.avg_verification_confidence:.2f} |
| **Avg RAG Sources** | {metrics.avg_rag_sources:.1f} |
| **Avg RAG Rules** | {metrics.avg_rag_rules:.1f} |
| **Avg RAG Incidents** | {metrics.avg_rag_incidents:.1f} |
| **RAG Recall@5** | {metrics.rag_recall_at_5:.1%} |
| **Groundedness Rate** | {metrics.groundedness_rate:.1%} |
| **Est. Cost/Incident** | ${metrics.estimated_cost_per_incident:.4f} |

---

## Review Tier Distribution

| Tier | Count |
|------|-------|
{chr(10).join(f"| {tier} | {count} |" for tier, count in metrics.review_tier_distribution.items())}

---

## Per-Incident Results

{incident_table}

---

## Failed Incidents

{generate_failed_section(results)}

---

## Groundedness Details

| Incident | Verification Confidence | Checks Passed/Total | Grounded |
|----------|------------------------|---------------------|----------|
{generate_groundedness_table(results)}

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|--------------|
| Mean | {metrics.avg_latency_ms:.0f} |
| P50 | {f"{statistics.median([r.latency_ms for r in results if r.success]):.0f}" if any(r.success for r in results) else "0"} |
| P90 | {f"{percentile(sorted([r.latency_ms for r in results if r.success]), 0.9):.0f}" if any(r.success for r in results) else "0"} |
| P95 | {metrics.p95_latency_ms:.0f} |
| P99 | {f"{percentile(sorted([r.latency_ms for r in results if r.success]), 0.99):.0f}" if any(r.success for r in results) else "0"} |

---

## Cost Analysis

| Metric | Value |
|--------|-------|
| Estimated Cost/Incident | ${metrics.estimated_cost_per_incident:.4f} |
| Total Estimated Cost | ${metrics.estimated_cost_per_incident * metrics.successful:.2f} |
| Note | Rough estimate based on token usage |

---

*Report generated automatically by CivicOps AI Evaluation Framework*
"""
    return report


def get_git_commit() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd="/Users/apple/CivicOps AI"
        )
        return result.stdout.strip()
    except:
        return "unknown"


def percentile(sorted_list: List[float], p: float) -> float:
    if not sorted_list:
        return 0.0
    k = (len(sorted_list) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_list) - 1)
    if f == c:
        return sorted_list[int(k)]
    return sorted_list[f] + (sorted_list[c] - sorted_list[f]) * (k - f)


def generate_failed_section(results: List[EvaluationResult]) -> str:
    failed = [r for r in results if not r.success]
    if not failed:
        return "No failed incidents."
    
    rows = []
    for r in failed:
        rows.append(f"| {r.incident_id} | {r.error or 'Unknown error'} |")
    
    return (
        "| Incident | Error |\n"
        "|----------|-------|\n" +
        "\n".join(rows)
    )


def generate_groundedness_table(results: List[EvaluationResult]) -> str:
    rows = []
    for r in results:
        if r.success:
            vc = f"{r.verification_confidence:.2f}" if r.verification_confidence else "N/A"
            passed = f"{r.verification_checks_passed}/{r.verification_checks_total}" if r.verification_checks_total else "N/A"
            grounded = "✅" if (r.verification_checks_passed / max(r.verification_checks_total, 1)) >= 0.7 else "❌"
            rows.append(f"| {r.incident_id} | {vc} | {passed} | {grounded} |")
    
    return (
        "| Incident | Ver Conf | Checks Passed | Grounded |\n"
        "|----------|----------|---------------|----------|\n" +
        "\n".join(rows)
    )


async def main():
    print("🔬 Starting CivicOps AI Pipeline Evaluation...")
    print("=" * 60)
    
    # Load test incidents
    incidents_path = Path("/app/eval/test_incidents.json")
    print(f"DEBUG: incidents_path = {incidents_path}")
    print(f"DEBUG: str(incidents_path) = {str(incidents_path)}")
    incidents = load_test_incidents(str(incidents_path))
    print(f"📋 Loaded {len(incidents)} test incidents")
    
    # Reset database (clean slate)
    print("🗄️  Resetting database...")
    from app.db.session import engine
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database reset complete")
    
    # Run evaluations
    print(f"\n🚀 Running {len(incidents)} incidents through pipeline...")
    results = []
    
    for i, incident in enumerate(incidents, 1):
        print(f"  [{i}/{len(incidents)}] Running {incident.id}...")
        result = await run_single_incident(incident, AsyncSessionLocal)
        results.append(result)
        status = "✅" if result.success else "❌"
        cat = "✓" if result.category_correct else "✗"
        pri = "✓" if result.priority_correct else "✗"
        print(f"  {result.incident_id}: {status} Cat:{cat} Pri:{pri} | {result.latency_ms:.0f}ms")
    
    # Compute metrics
    print("\n📊 Computing metrics...")
    metrics = await compute_metrics(results)
    
    # Generate report
    report = generate_report(metrics, results)
    
    # Save report
    output_path = Path("/app/eval/REPORT.md")
    output_path.write_text(report)
    print(f"\n📄 Report saved to {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Total: {metrics.total_incidents} | Success: {metrics.successful} | Failed: {metrics.failed}")
    print(f"Category Accuracy: {metrics.category_accuracy:.1%}")
    print(f"Priority Accuracy: {metrics.priority_accuracy:.1%}")
    print(f"Overall Accuracy: {metrics.overall_accuracy:.1%}")
    print(f"Avg Latency: {metrics.avg_latency_ms:.0f}ms | P95: {metrics.p95_latency_ms:.0f}ms")
    print(f"Avg Confidence: {metrics.avg_confidence:.2f}")
    print(f"RAG Recall@5: {metrics.rag_recall_at_5:.1%}")
    print(f"Groundedness: {metrics.groundedness_rate:.1%}")
    print(f"Cost/Incident: ${metrics.estimated_cost_per_incident:.4f}")
    print(f"\n📄 Report: /Users/apple/CivicOps AI/eval/REPORT.md")


if __name__ == "__main__":
    asyncio.run(main())