from typing import Optional, Dict, Any, BinaryIO, AsyncIterator, Tuple
import aioboto3
from botocore.exceptions import ClientError
from botocore.config import Config
from datetime import datetime

from app.blob.domain.domain_service.storage_adapter import (
    StorageAdapter,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
)
from app.blob.domain.entity.storage_locator import StorageLocator
from app.blob.domain.vo.etag import Etag
from app.blob.domain.vo.mime_type import MimeType


class MinIOStorageAdapter(StorageAdapter):
    """MinIO存储适配器实现（使用aioboto3，兼容S3 API）。"""
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
        region: Optional[str] = None,
        disable_chunked_encoding: bool = False
    ):
        # MinIO使用S3兼容的API，所以可以用aioboto3
        self.endpoint_url = f"{'https' if secure else 'http'}://{endpoint}"
        self.session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region or 'us-east-1'
        )
        self.region = region
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
        """将对象存储到MinIO。"""
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
                # 确保存储桶存在
                try:
                    await s3.head_bucket(Bucket=locator.bucket)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        await s3.create_bucket(Bucket=locator.bucket)
                
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
            raise StorageError(f"MinIO存储失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"存储对象失败: {str(e)}", locator=locator, cause=e)
    
    async def head_object(self, locator: StorageLocator) -> Optional[ObjectMetadata]:
        """获取MinIO对象的元数据。"""
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
            raise StorageError(f"获取MinIO对象元数据失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"获取对象元数据失败: {str(e)}", locator=locator, cause=e)
    
    async def delete_object(self, locator: StorageLocator) -> bool:
        """从MinIO删除对象。"""
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
            raise StorageError(f"删除MinIO对象失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"删除对象失败: {str(e)}", locator=locator, cause=e)
    
    async def object_exists(self, locator: StorageLocator) -> bool:
        """检查MinIO对象是否存在。"""
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
            raise StorageError(f"检查MinIO对象存在性失败: {str(e)}", locator=locator, cause=e)
    
    async def get_object_url(
        self,
        locator: StorageLocator,
        *,
        expires_in_seconds: Optional[int] = None,
        skip_exists_check: bool = False,
    ) -> str:
        """生成MinIO对象的预签名URL。
        
        Args:
            locator: 存储位置定位器
            expires_in_seconds: URL过期时间（秒）
            skip_exists_check: 是否跳过存在性检查以提升性能，默认 False
        """
        try:
            # 仅在需要时检查对象存在性
            if not skip_exists_check:
                if not await self.object_exists(locator):
                    raise ObjectNotFoundError(f"MinIO对象不存在: {locator}", locator=locator)
            
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
            raise StorageError(f"生成MinIO预签名URL失败: {str(e)}", locator=locator, cause=e)
        except Exception as e:
            raise StorageError(f"生成对象URL失败: {str(e)}", locator=locator, cause=e)

    async def get_object_stream(
        self,
        locator: StorageLocator,
        *,
        chunk_size: int = 1024 * 1024,
        **kwargs
    ) -> Tuple[ObjectMetadata, AsyncIterator[bytes]]:
        """以流式方式读取 MinIO 对象内容。
        
        优化：直接发起 GET 请求，从响应头解析元数据，避免单独的 HEAD 请求。
        """
        try:
            # 可选的存在性检查（默认执行，性能敏感场景可跳过）
            # 注意：如果 skip_exists_check=False，此处仍会多发一次 HEAD 请求。
            # 为了极致性能，调用方应设为 True，依靠 get_object 的 404 异常来处理不存在的情况。
            skip_exists_check = kwargs.get('skip_exists_check', False)
            if not skip_exists_check:
                if not await self.object_exists(locator):
                    raise ObjectNotFoundError(f"MinIO对象不存在: {locator}", locator=locator)

            # 先获取对象元数据
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
                        # 直接获取整个流，让 aioboto3/urllib3 处理分块
                        resp = await s3.get_object(Bucket=locator.bucket, Key=locator.object_key)
                        async with resp['Body'] as stream:
                            # 兼容性处理：aioboto3/aiobotocore 的 resp['Body'] 可能是 StreamingBody 或 ClientResponse
                            # 报错提示 "ClientResponse.read() takes 1 positional argument"，说明 stream 可能是 ClientResponse
                            # ClientResponse.read() 读取全部且不接受 size 参数，应使用 content.read(size)
                            reader = stream
                            if hasattr(stream, 'content') and hasattr(stream.content, 'read'):
                                reader = stream.content
                                
                            while True:
                                chunk = await reader.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                except ClientError as e:
                    # 这里捕获异常比较晚，但对于流式处理是必须的
                    raise StorageError(f"下载流中断: {str(e)}", locator=locator, cause=e)

            return meta, _iter()
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ObjectNotFoundError(f"MinIO对象不存在: {locator}", locator=locator)
            raise StorageError(f"下载MinIO对象失败: {str(e)}", locator=locator, cause=e)
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
        """MinIO/S3 CopyObject：服务端拷贝对象。"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url, config=self.client_config) as s3:
                # 确保目标 bucket 存在
                try:
                    await s3.head_bucket(Bucket=target.bucket)
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        await s3.create_bucket(Bucket=target.bucket)

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
            raise StorageError(f"MinIO CopyObject 失败: {str(e)}", locator=target, cause=e)
        except Exception as e:
            raise StorageError(f"复制对象失败: {str(e)}", locator=target, cause=e)