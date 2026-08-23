from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Any, Optional
from dataclasses import dataclass, field
import time
import uuid
import structlog
from app.core.observability import observability, get_tracer
from app.db.models import AgentType, AgentLog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
tracer = get_tracer(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class AgentResult(Generic[OutputT]):
    success: bool
    output: Optional[OutputT] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.tracer = get_tracer(f"agent.{agent_type.value}")

    @abstractmethod
    async def process(self, input_data: InputT, db: AsyncSession, complaint_id: uuid.UUID, trace_id: str) -> AgentResult[OutputT]:
        pass

    async def execute(
        self,
        input_data: InputT,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[OutputT]:
        start_time = time.perf_counter()
        langfuse_trace = observability.create_langfuse_trace(trace_id, f"agent.{self.agent_type.value}")
        langfuse_span = None
        
        if langfuse_trace:
            langfuse_span = observability.create_langfuse_span(
                langfuse_trace,
                f"agent.{self.agent_type.value}.execute",
                input_data=input_data.model_dump() if hasattr(input_data, 'model_dump') else str(input_data),
            )

        with self.tracer.start_as_current_span(f"agent.{self.agent_type.value}.process") as span:
            span.set_attribute("complaint_id", str(complaint_id))
            span.set_attribute("agent_type", self.agent_type.value)
            span.set_attribute("trace_id", trace_id)
            
            try:
                result = await self.process(input_data, db, complaint_id, trace_id)
                
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                result.execution_time_ms = execution_time_ms
                
                # Log to database
                await self._log_execution(
                    db, complaint_id, input_data, result, execution_time_ms, trace_id
                )
                
                # Update Langfuse span
                if langfuse_span:
                    langfuse_span.end(
                        output=result.output.model_dump() if hasattr(result.output, 'model_dump') else str(result.output),
                        metadata={"execution_time_ms": execution_time_ms, "success": result.success, **result.metadata}
                    )
                    if result.error:
                        langfuse_span.end(metadata={"error": result.error})
                
                if langfuse_trace:
                    langfuse_trace.update(metadata={"status": "success" if result.success else "error"})
                    observability.flush()
                
                span.set_attribute("success", result.success)
                span.set_attribute("execution_time_ms", execution_time_ms)
                
                if not result.success:
                    span.record_exception(Exception(result.error or "Agent processing failed"))
                
                return result
                
            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                error_msg = f"{type(e).__name__}: {str(e)}"
                
                result = AgentResult[OutputT](
                    success=False,
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )
                
                await self._log_execution(
                    db, complaint_id, input_data, result, execution_time_ms, trace_id
                )
                
                if langfuse_span:
                    langfuse_span.end(
                        output={"error": error_msg},
                        metadata={"execution_time_ms": execution_time_ms, "success": False, "error": error_msg}
                    )
                
                if langfuse_trace:
                    langfuse_trace.update(metadata={"status": "error", "error": error_msg})
                    observability.flush()
                
                span.record_exception(e)
                span.set_attribute("success", False)
                span.set_attribute("error", error_msg)
                
                logger.error(
                    "agent_execution_failed",
                    agent_type=self.agent_type.value,
                    complaint_id=str(complaint_id),
                    error=error_msg,
                    execution_time_ms=execution_time_ms,
                )
                
                return result

    async def _log_execution(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        input_data: InputT,
        result: AgentResult[OutputT],
        execution_time_ms: int,
        trace_id: str,
    ):
        try:
            input_dict = input_data.model_dump() if hasattr(input_data, 'model_dump') else {"data": str(input_data)}
            output_dict = result.output.model_dump() if result.output and hasattr(result.output, 'model_dump') else {"data": str(result.output) if result.output else None}
            
            log = AgentLog(
                complaint_id=complaint_id,
                agent_type=self.agent_type,
                input_data=input_dict,
                output_data=output_dict,
                execution_time_ms=execution_time_ms,
                error=result.error,
                trace_id=trace_id,
            )
            db.add(log)
            await db.flush()
        except Exception as e:
            logger.error("agent_log_failed", agent_type=self.agent_type.value, error=str(e))