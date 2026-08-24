import io
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from app.core.config import settings
from app.core.observability import get_tracer
import structlog

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class MinioClient:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("minio_bucket_created", bucket=self.bucket)
        except S3Error as e:
            logger.error("minio_bucket_check_failed", error=str(e))
            raise

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        with tracer.start_as_current_span("minio.upload_file") as span:
            span.set_attribute("minio.bucket", self.bucket)
            span.set_attribute("minio.object_name", object_name)
            try:
                self.client.put_object(
                    bucket_name=self.bucket,
                    object_name=object_name,
                    data=data,
                    length=length,
                    content_type=content_type,
                )
                url = self.get_presigned_url(object_name)
                span.set_attribute("minio.url", url)
                logger.info("minio_upload_success", object_name=object_name, size=length)
                return url
            except S3Error as e:
                span.record_exception(e)
                logger.error("minio_upload_failed", object_name=object_name, error=str(e))
                raise

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        return self.upload_file(object_name, io.BytesIO(data), len(data), content_type)

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        try:
            return self.client.presigned_get_object(self.bucket, object_name, expires=expires)
        except S3Error as e:
            logger.error("minio_presigned_url_failed", object_name=object_name, error=str(e))
            raise

    def download_file(self, object_name: str) -> bytes:
        with tracer.start_as_current_span("minio.download_file") as span:
            span.set_attribute("minio.bucket", self.bucket)
            span.set_attribute("minio.object_name", object_name)
            try:
                response = self.client.get_object(self.bucket, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                logger.info("minio_download_success", object_name=object_name, size=len(data))
                return data
            except S3Error as e:
                span.record_exception(e)
                logger.error("minio_download_failed", object_name=object_name, error=str(e))
                raise

    def delete_file(self, object_name: str) -> bool:
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info("minio_delete_success", object_name=object_name)
            return True
        except S3Error as e:
            logger.error("minio_delete_failed", object_name=object_name, error=str(e))
            return False

    def file_exists(self, object_name: str) -> bool:
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


minio_client = MinioClient()