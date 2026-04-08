from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Factory, Singleton

from app.blob.adapter.output.repository.blob import SQLAlchemyBlobRepository
from app.blob.adapter.output.repository.blob_reference import SQLAlchemyBlobReferenceRepository
from app.blob.adapter.output.domain_service.blob_domain_service import SQLAlchemyBlobDomainService
from app.blob.adapter.output.domain_service.blob_public_service import SQLAlchemyBlobPublicDomainService
from app.blob.adapter.output.domain_service.file_processor import SqlAlchemyFileProcessorService
from app.blob.adapter.output.domain_service.image_processor import ImageProcessorImpl
from app.blob.adapter.output.domain_service.blob_attachment_domain_service import SQLAlchemyBlobAttachmentDomainService
from app.blob.adapter.output.cache.blob_storage_thumbnail_cache import BlobStorageThumbnailCacheAdapter
from app.blob.adapter.output.storage import create_storage_adapter
from app.blob.application.service.blob_external import BlobExternalCommandService
from app.blob.domain.factory.blob_factory import BlobFactory
from app.blob.adapter.output.query.blob_query import SQLAlchemyBlobQueryService
from app.blob.adapter.output.domain_service.blob_file_domain_service import SQLAlchemyBlobFileDomainService
from core.config import config



class BlobContainer(DeclarativeContainer):
    """Blob 模块的依赖注入容器。"""

    wiring_config = WiringConfiguration(modules=["app"])

    # 存储适配器（基础设施，由防腐层使用）
    storage_adapter = Singleton(create_storage_adapter)

    # 仓储
    blob_repository = Singleton(SQLAlchemyBlobRepository)
    blob_reference_repository = Singleton(SQLAlchemyBlobReferenceRepository)

    # 文件处理服务
    file_processor_service = Singleton(SqlAlchemyFileProcessorService)

    # 图像处理服务
    image_processor_service = Singleton(ImageProcessorImpl)

    # 领域工厂
    blob_factory = Factory(
        BlobFactory,
        file_processor=file_processor_service,
    )

    # 领域服务
    blob_domain_service = Singleton(
        SQLAlchemyBlobDomainService,
        blob_repository=blob_repository,
    )
    blob_public_domain_service = Singleton(
        SQLAlchemyBlobPublicDomainService,
        repository=blob_repository,
        storage_adapter=storage_adapter,
        signing_secret=config.blob_storage.signing_secret_key or None,
    )
    blob_file_domain_service = Singleton(
        SQLAlchemyBlobFileDomainService,
        blob_repository=blob_repository,
        blob_factory=blob_factory,
        storage_adapter=storage_adapter,
    )
    blob_attachment_domain_service = Singleton(
        SQLAlchemyBlobAttachmentDomainService,
        blob_reference_repository=blob_reference_repository,
    )

    # 缩略图缓存适配器
    thumbnail_cache_adapter = Singleton(
        BlobStorageThumbnailCacheAdapter,
        storage_adapter=storage_adapter,
    )

    # 查询服务
    blob_query_service = Singleton(SQLAlchemyBlobQueryService)

    # 对外 Command Service
    blob_external_command_service = Factory(
        BlobExternalCommandService,
        blob_file_domain_service=blob_file_domain_service,
        blob_attachment_domain_service=blob_attachment_domain_service,
        public_domain_service=blob_public_domain_service,
    )

    # 对外暴露配置（供其他容器使用）
    default_bucket = Singleton(lambda: config.blob_storage.default_bucket)
    default_storage_provider = Singleton(lambda: config.blob_storage.storage_provider)
