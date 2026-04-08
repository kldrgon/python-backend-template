from typing import Optional, Dict, Any, BinaryIO, AsyncIterator, Tuple
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from botocore import UNSIGNED
from datetime import datetime

from app.blob.domain.domain_service.storage_adapter import (
    StorageAdapter,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
    ObjectAlreadyExistsError,
    StorageQuotaExceededError,
)
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.mime_type import MimeType


class S3StorageAdapter(StorageAdapter):
    """AWS S3存储适配器实现（异步版本）。"""
    
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        disable_chunked_encoding: bool = False
    ):
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.disable_chunked_encoding = disable_chunked_encoding
        
        # 配置botocore客户端 - 禁用chunked编码以兼容阿里云OSS
        if disable_chunked_encoding:
            # 阿里云OSS官方建议:boto3使用V4签名时强制chunked encoding无法禁用
            # 解决方案:改用signature_version='s3'(即V2签名)
            self.client_config = Config(
                signature_version='s3',  # 使用V2签名,避免chunked encoding
                s3={
                    'addressing_style': 'virtual',
                }
            )
        else:
            self.client_config = None
    
    async def put_object(
        self,
        locator: StorageLocator,
        body: BinaryIO,
        *,
        mime_type: Optional[MimeType] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: Optional[str] = None
    ) -> ObjectMetadata:
        """将对象存储到S3。"""
        try:
            # 读取body内容到内存(避免chunked encoding)
            if self.disable_chunked_encoding:
                if hasattr(body, 'read'):
                    body_bytes = body.read()
                    if hasattr(body, 'seek'):
                        body.seek(0)
                else:
                    body_bytes = body
            else:
                body_bytes = body
            
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                extra_args = {}
                
                if mime_type:
                    extra_args['ContentType'] = str(mime_type)
                
                if metadata:
                    extra_args['Metadata'] = metadata
                    
                if storage_class:
                    extra_args['StorageClass'] = storage_class
                
                # 上传对象
                response = await s3.put_object(
                    Bucket=locator.bucket,
                    Key=locator.object_key,
                    Body=body_bytes,
                    **extra_args
                )
                
                # 获取对象信息
                head_response = await s3.head_object(
                    Bucket=locator.bucket,
                    Key=locator.object_key
                )
                
                return ObjectMetadata(
                    size_bytes=head_response['ContentLength'],
                    etag=Etag(value=response['ETag'].strip('"')),
                    mime_type=MimeType(value=head_response.get('ContentType')) if head_response.get('ContentType') else mime_type,
                    last_modified=head_response['LastModified'].isoformat(),
                    storage_class=head_response.get('StorageClass', 'STANDARD'),
                    custom_metadata=head_response.get('Metadata', {})
                )
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise StorageError(f"存储桶不存在: {locator.bucket}", locator=locator, cause=e)
            elif error_code == 'AccessDenied':
                raise StorageError(f"访问被拒绝: {locator}", locator=locator, cause=e)
            else:
                raise StorageError(f"S3存储失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"存储对象失败: {str(e)}", locator=locator, cause=e)
    
    async def head_object(self, locator: StorageLocator) -> Optional[ObjectMetadata]:
        """获取S3对象的元数据。"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                response = await s3.head_object(
                    Bucket=locator.bucket,
                    Key=locator.object_key
                )
                
                return ObjectMetadata(
                    size_bytes=response['ContentLength'],
                    etag=Etag(value=response['ETag'].strip('"')),
                    mime_type=MimeType(value=response.get('ContentType')) if response.get('ContentType') else None,
                    last_modified=response['LastModified'].isoformat(),
                    storage_class=response.get('StorageClass', 'STANDARD'),
                    custom_metadata=response.get('Metadata', {})
                )
                
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise StorageError(f"获取S3对象元数据失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"获取对象元数据失败: {str(e)}", locator=locator, cause=e)
    
    async def delete_object(self, locator: StorageLocator) -> bool:
        """从S3删除对象。"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                # 先检查对象是否存在
                if not await self.object_exists(locator):
                    return False
                
                await s3.delete_object(
                    Bucket=locator.bucket,
                    Key=locator.object_key
                )
                return True
                
        except ClientError as e:
            raise StorageError(f"删除S3对象失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"删除对象失败: {str(e)}", locator=locator, cause=e)
    
    async def object_exists(self, locator: StorageLocator) -> bool:
        """检查S3对象是否存在。"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                await s3.head_object(
                    Bucket=locator.bucket,
                    Key=locator.object_key
                )
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise StorageError(f"检查S3对象存在性失败: {str(e)}", locator=locator, cause=e)
    
    async def get_object_url(
        self,
        locator: StorageLocator,
        *,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str:
        """生成S3对象的预签名URL。
        
        Args:
            locator: 存储位置定位器
            expires_in_seconds: URL过期时间（秒）
            skip_exists_check: 是否跳过存在性检查以提升性能，默认 False
        """
        try:
            # 仅在需要时检查对象存在性
            if not skip_exists_check:
                if not await self.object_exists(locator):
                    raise ObjectNotFoundError(f"S3对象不存在: {locator}", locator=locator)
            
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                url = await s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': locator.bucket,
                        'Key': locator.object_key
                    },
                    ExpiresIn=expires_in_seconds or 3600  # 默认1小时
                )
                return url
                
        except ClientError as e:
            raise StorageError(f"生成S3预签名URL失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"生成对象URL失败: {str(e)}", locator=locator, cause=e)

    async def get_object_stream(
        self,
        locator: StorageLocator,
        *,
        chunk_size: int = 1024 * 1024,
        **kwargs
    ) -> Tuple[ObjectMetadata, AsyncIterator[bytes]]:
        """S3 流式下载（用于降级：下载+上传）。"""
        try:
            skip_exists_check = kwargs.get('skip_exists_check', False)
            if not skip_exists_check:
                if not await self.object_exists(locator):
                    raise ObjectNotFoundError(f"S3对象不存在: {locator}", locator=locator)

            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                head = await s3.head_object(Bucket=locator.bucket, Key=locator.object_key)
                meta = ObjectMetadata(
                    size_bytes=head['ContentLength'],
                    etag=Etag(value=head['ETag'].strip('"')),
                    mime_type=MimeType(value=head.get('ContentType')) if head.get('ContentType') else None,
                    last_modified=head['LastModified'].isoformat(),
                    storage_class=head.get('StorageClass', 'STANDARD'),
                    custom_metadata=head.get('Metadata', {}),
                )

            async def _iter() -> AsyncIterator[bytes]:
                try:
                    async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                        resp = await s3.get_object(Bucket=locator.bucket, Key=locator.object_key)
                        async with resp['Body'] as stream:
                            reader = stream
                            if hasattr(stream, 'content') and hasattr(stream.content, 'read'):
                                reader = stream.content
                            while True:
                                chunk = await reader.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                except ClientError as e:
                    raise StorageError(f"下载流中断: {str(e)}", locator=locator, cause=e)

            return meta, _iter()
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ObjectNotFoundError(f"S3对象不存在: {locator}", locator=locator)
            raise StorageError(f"下载S3对象失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"下载对象失败: {str(e)}", locator=locator, cause=e)

    def supports_copy(self) -> bool:
        return True

    async def copy_object(
        self,
        *,
        source: StorageLocator,
        target: StorageLocator,
    ) -> ObjectMetadata:
        """S3 CopyObject：服务端拷贝对象。"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                await s3.copy_object(
                    Bucket=target.bucket,
                    Key=target.object_key,
                    CopySource={"Bucket": source.bucket, "Key": source.object_key},
                )
                head = await s3.head_object(Bucket=target.bucket, Key=target.object_key)
                return ObjectMetadata(
                    size_bytes=head['ContentLength'],
                    etag=Etag(value=head['ETag'].strip('"')),
                    mime_type=MimeType(value=head.get('ContentType')) if head.get('ContentType') else None,
                    last_modified=head['LastModified'].isoformat(),
                    storage_class=head.get('StorageClass', 'STANDARD'),
                    custom_metadata=head.get('Metadata', {}),
                )
        except ClientError as e:
            raise StorageError(f"S3 CopyObject 失败: {str(e)}", locator=target, cause=e)
        except Exception as e:
            raise StorageError(f"复制对象失败: {str(e)}", locator=target, cause=e)