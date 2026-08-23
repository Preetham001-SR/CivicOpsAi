import os
from contextlib import asynccontextmanager
from typing import Optional
import structlog
from langfuse import Langfuse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from app.core.config import settings

logger = structlog.get_logger()


class ObservabilityManager:
    def __init__(self):
        self.langfuse: Optional[Langfuse] = None
        self.tracer_provider: Optional[TracerProvider] = None
        self._initialized = False

    def initialize(self, app=None):
        if self._initialized:
            return

        # Initialize Langfuse
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            try:
                self.langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
                logger.info("langfuse_initialized", host=settings.LANGFUSE_HOST)
            except Exception as e:
                logger.error("langfuse_init_failed", error=str(e))
        else:
            logger.warning("langfuse_not_configured", public_key=bool(settings.LANGFUSE_PUBLIC_KEY))

        # Initialize OpenTelemetry
        try:
            resource = Resource(attributes={SERVICE_NAME: settings.OTEL_SERVICE_NAME})
            self.tracer_provider = TracerProvider(resource=resource)
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=True,
            )
            self.tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            
            trace.set_tracer_provider(self.tracer_provider)
            logger.info("otel_initialized", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        except Exception as e:
            logger.error("otel_init_failed", error=str(e))

        # Auto-instrument if app provided
        if app:
            self.instrument_app(app)

        self._initialized = True

    def instrument_app(self, app):
        try:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=self.tracer_provider)
            SQLAlchemyInstrumentor().instrument(engine=None, tracer_provider=self.tracer_provider)
            RedisInstrumentor().instrument(tracer_provider=self.tracer_provider)
            CeleryInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("auto_instrumentation_enabled")
        except Exception as e:
            logger.error("auto_instrumentation_failed", error=str(e))

    def get_tracer(self, name: str):
        return trace.get_tracer(name)

    def create_langfuse_trace(self, trace_id: str, name: str, metadata: dict = None):
        if self.langfuse:
            return self.langfuse.trace(id=trace_id, name=name, metadata=metadata or {})
        return None

    def create_langfuse_span(self, trace, name: str, input_data: dict = None, output_data: dict = None, metadata: dict = None):
        if self.langfuse and trace:
            return trace.span(name=name, input=input_data, output=output_data, metadata=metadata or {})
        return None

    def flush(self):
        if self.langfuse:
            self.langfuse.flush()


observability = ObservabilityManager()


def get_tracer(name: str):
    return observability.get_tracer(name)