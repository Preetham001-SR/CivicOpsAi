# CivicOps AI Pipeline Evaluation Report

**Generated:** 2026-08-24 07:08:53
**Test Dataset:** 25 incidents (eval/test_incidents.json)
**Pipeline Version:** Current (commit: unknown)

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| **Total Incidents** | 26 |
| **Successful** | 0 |
| **Failed** | 26 |
| **Category Accuracy** | 0.0% |
| **Priority Accuracy** | 0.0% |
| **Overall Accuracy (Both)** | 0.0% |
| **Avg Latency** | 0 ms |
| **P95 Latency** | 0 ms |
| **Avg Confidence** | 0.00 |
| **Avg Verification Confidence** | 0.00 |
| **Avg RAG Sources** | 0.0 |
| **Avg RAG Rules** | 0.0 |
| **Avg RAG Incidents** | 0.0 |
| **RAG Recall@5** | 0.0% |
| **Groundedness Rate** | 0.0% |
| **Est. Cost/Incident** | $0.0000 |

---

## Review Tier Distribution

| Tier | Count |
|------|-------|


---

## Per-Incident Results

| Incident | Status | Pred Cat | Exp Cat | Cat ✓ | Pred Pri | Exp Pri | Pri ✓ | Latency (ms) | Conf | Tier | RAG Src | Ver Conf | Error |
|----------|--------|----------|---------|-------|----------|---------|-------|--------------|------|------|---------|----------|-------|
| eval-001 | ❌ | N/A | pothole | ❌ | N/A | high | ❌ | 2539 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-002 | ❌ | N/A | broken_sign | ❌ | N/A | critical | ❌ | 1559 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-003 | ❌ | N/A | streetlight_outage | ❌ | N/A | high | ❌ | 1637 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-004 | ❌ | N/A | graffiti | ❌ | N/A | low | ❌ | 1611 | N/A | N/A | 0 | N/A | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('cf306a3a-b6be-4a1d-9361-1c8073758ff4'), 'text_description': 'Graffiti on the retaining wall of the 14th Street subway station', 'photo_url': None, 'audio_url': None, 'latitude': 40.738, 'longitude': -73.996, 'address': '14th St & 8th Ave, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': '517d7283-73fa-41f2-8006-8f94ce5428f7', 'review_tier': 'mandatory_review'} (Invalid state update, expected dict with one or mo...) |
| eval-005 | ❌ | N/A | sidewalk_damage | ❌ | N/A | high | ❌ | 1420 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-006 | ❌ | N/A | traffic_signal | ❌ | N/A | critical | ❌ | 814 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-007 | ❌ | N/A | drainage_issue | ❌ | N/A | critical | ❌ | 657 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-008 | ❌ | N/A | damaged_property | ❌ | N/A | low | ❌ | 1100 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-009 | ❌ | N/A | pothole | ❌ | N/A | critical | ❌ | 1549 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-010 | ❌ | N/A | broken_sign | ❌ | N/A | high | ❌ | 900 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-011 | ❌ | N/A | drainage_issue | ❌ | N/A | critical | ❌ | 5626 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-012 | ❌ | N/A | sidewalk_damage | ❌ | N/A | medium | ❌ | 748 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-013 | ❌ | N/A | traffic_signal | ❌ | N/A | critical | ❌ | 565 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-014 | ❌ | N/A | graffiti | ❌ | N/A | low | ❌ | 672 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-015 | ❌ | N/A | damaged_property | ❌ | N/A | high | ❌ | 2457 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-016 | ❌ | N/A | pothole | ❌ | N/A | critical | ❌ | 4657 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-017 | ❌ | N/A | streetlight_outage | ❌ | N/A | high | ❌ | 862 | N/A | N/A | 0 | N/A | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('eaa3a391-14e3-4767-9b10-a5c630b51a85'), 'text_description': 'Broken streetlight pole leaning dangerously at 3rd Avenue and 28th Street', 'photo_url': None, 'audio_url': None, 'latitude': 40.7412, 'longitude': -73.9812, 'address': '3rd Ave & 28th St, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': 'b35f09a5-b8f2-4bed-8258-133226fb293d', 'review_tier': 'mandatory_review'} (Invalid state update, expected dict with one or mo...) |
| eval-018 | ❌ | N/A | drainage_issue | ❌ | N/A | critical | ❌ | 3352 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-019 | ❌ | N/A | damaged_property | ❌ | N/A | low | ❌ | 3214 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-020 | ❌ | N/A | damaged_property | ❌ | N/A | medium | ❌ | 1610 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-021 | ❌ | N/A | pothole | ❌ | N/A | critical | ❌ | 1616 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-022 | ❌ | N/A | broken_sign | ❌ | N/A | medium | ❌ | 2148 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-022 | ❌ | N/A | drainage_issue | ❌ | N/A | high | ❌ | 732 | N/A | N/A | 0 | N/A | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('8a480e35-daac-474a-90fc-ebd80e6ef9e2'), 'text_description': 'Flooded basement complaint at building on Water Street near Wall Street', 'photo_url': None, 'audio_url': None, 'latitude': 40.706, 'longitude': -74.009, 'address': 'Water St & Wall St, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': 'e6d88852-659f-403c-a158-3a2dd06b6d32', 'review_tier': 'mandatory_review'} (Invalid state update, expected dict with one or mo...) |
| eval-023 | ❌ | N/A | broken_sign | ❌ | N/A | high | ❌ | 2243 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-024 | ❌ | N/A | damaged_property | ❌ | N/A | medium | ❌ | 1475 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |
| eval-025 | ❌ | N/A | streetlight_outage | ❌ | N/A | medium | ❌ | 1169 | N/A | N/A | 0 | N/A | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type (2 validation errors for VerificationInput
category...) |

---

## Failed Incidents

| Incident | Error |
|----------|-------|
| eval-001 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-002 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-003 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-004 | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('cf306a3a-b6be-4a1d-9361-1c8073758ff4'), 'text_description': 'Graffiti on the retaining wall of the 14th Street subway station', 'photo_url': None, 'audio_url': None, 'latitude': 40.738, 'longitude': -73.996, 'address': '14th St & 8th Ave, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': '517d7283-73fa-41f2-8006-8f94ce5428f7', 'review_tier': 'mandatory_review'} |
| eval-005 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-006 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-007 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-008 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-009 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-010 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-011 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-012 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-013 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-014 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-015 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-016 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-017 | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('eaa3a391-14e3-4767-9b10-a5c630b51a85'), 'text_description': 'Broken streetlight pole leaning dangerously at 3rd Avenue and 28th Street', 'photo_url': None, 'audio_url': None, 'latitude': 40.7412, 'longitude': -73.9812, 'address': '3rd Ave & 28th St, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': 'b35f09a5-b8f2-4bed-8258-133226fb293d', 'review_tier': 'mandatory_review'} |
| eval-018 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-019 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-020 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-021 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-022 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-022 | Invalid state update, expected dict with one or more of ['complaint_id', 'text_description', 'photo_url', 'audio_url', 'latitude', 'longitude', 'address', 'vision_analysis', 'speech_transcript', 'location_details', 'rag_context', 'rag_sources', 'decision', 'verification', 'confidence_score', 'requires_human_review', 'human_review_decision', 'human_review_notes', 'human_review_modified_data', 'work_order', 'work_order_id', 'status', 'errors', 'current_agent', 'trace_id'], got {'complaint_id': UUID('8a480e35-daac-474a-90fc-ebd80e6ef9e2'), 'text_description': 'Flooded basement complaint at building on Water Street near Wall Street', 'photo_url': None, 'audio_url': None, 'latitude': 40.706, 'longitude': -74.009, 'address': 'Water St & Wall St, New York, NY', 'vision_analysis': {'caption': 'No photo provided', 'categories': {}, 'detected_objects': [], 'damage_assessment': 'No photo submitted for analysis', 'recommended_category': 'other', 'confidence': 0.0, 'model_used': 'Salesforce/blip-image-captioning-base'}, 'speech_transcript': '', 'location_details': None, 'rag_context': None, 'rag_sources': [], 'decision': {'category': <ComplaintCategory.OTHER: 'other'>, 'priority': <PriorityLevel.HIGH: 'high'>, 'recommended_action': 'Repair other per municipal standards. Schedule based on priority.', 'assigned_department': 'Public Works - Street Maintenance', 'estimated_cost': 2500.0, 'estimated_duration_days': 2, 'reasoning': 'LLM failed, using enhanced fallback. Category: other. Weather: N/A. Infra: {}. RAG: ', 'confidence': 0.6}, 'verification': {'checks': [{'check_name': 'vision_confidence', 'passed': False, 'details': 'Vision model confidence: 0.00', 'weight': 0.25}, {'check_name': 'speech_confidence', 'passed': True, 'details': 'Speech recognition confidence: 0.92', 'weight': 0.15}, {'check_name': 'location_accuracy', 'passed': True, 'details': 'Location accuracy: geocoded', 'weight': 0.15}, {'check_name': 'rag_relevance', 'passed': False, 'details': 'RAG context confidence: 0.00', 'weight': 0.25}, {'check_name': 'decision_consistency', 'passed': False, 'details': 'Decision agent confidence: 0.60', 'weight': 0.2}], 'overall_confidence': 0.3, 'requires_human_review': True, 'review_reason': 'LLM verification failed, using deterministic checks only. Confidence: 0.30'}, 'confidence_score': 0.3, 'requires_human_review': True, 'human_review_decision': 'approve', 'human_review_notes': 'Auto-approved for development', 'human_review_modified_data': None, 'work_order': None, 'work_order_id': None, 'status': 'awaiting_review', 'errors': ["Location: AttributeError: 'NoneType' object has no attribute 'get'", "RAG: OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)"], 'current_agent': 'verification', 'trace_id': 'e6d88852-659f-403c-a158-3a2dd06b6d32', 'review_tier': 'mandatory_review'} |
| eval-023 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-024 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |
| eval-025 | 2 validation errors for VerificationInput
category
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type
priority
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information visit https://errors.pydantic.dev/2.5/v/string_type |

---

## Groundedness Details

| Incident | Verification Confidence | Checks Passed/Total | Grounded |
|----------|------------------------|---------------------|----------|
| Incident | Ver Conf | Checks Passed | Grounded |
|----------|----------|---------------|----------|


---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|--------------|
| Mean | 0 |
| P50 | 0 |
| P90 | 0 |
| P95 | 0 |
| P99 | 0 |

---

## Cost Analysis

| Metric | Value |
|--------|-------|
| Estimated Cost/Incident | $0.0000 |
| Total Estimated Cost | $0.00 |
| Note | Rough estimate based on token usage |

---

*Report generated automatically by CivicOps AI Evaluation Framework*
