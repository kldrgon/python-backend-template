"""
??????

??????????????????PPT/PPTX ??PDF
????
- LibreOffice (soffice): ???????
- comtypes (Windows): pip install comtypes
"""
import asyncio
import structlog
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class DocumentConverter:
    """???????? PPT/Word/Excel ??PDF??""
    
    def __init__(self, *, libreoffice_path: Optional[str] = None):
        """
        ????????
        
        Args:
            libreoffice_path: LibreOffice ??????????None ??????
        """
        self.libreoffice_path = libreoffice_path or self._find_libreoffice()
        if not self.libreoffice_path:
            logger.warning("LibreOffice not found. Document conversion will not work.")
    
    def _find_libreoffice(self) -> Optional[str]:
        """???? LibreOffice ????"""
        system = platform.system()
        
        possible_paths = []
        if system == "Windows":
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
        elif system == "Linux":
            possible_paths = [
                "/usr/bin/soffice",
                "/usr/bin/libreoffice",
            ]
        elif system == "Darwin":  # macOS
            possible_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found LibreOffice at: {path}")
                return path
        
        # ????PATH ????
        try:
            result = subprocess.run(
                ["which", "soffice"] if system != "Windows" else ["where", "soffice"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip().split("\n")[0]
                logger.info(f"Found LibreOffice in PATH: {path}")
                return path
        except Exception:
            pass
        
        return None
    
    async def ppt_to_pdf(self, *, ppt_bytes: bytes, filename: str = "presentation.pptx") -> bytes:
        """
        ??PPT/PPTX ????PDF
        
        Args:
            ppt_bytes: PPT ????
            filename: ??????????????
        
        Returns:
            PDF ????
        
        Raises:
            RuntimeError: ????
            ValueError: LibreOffice ????
        """
        if not self.libreoffice_path:
            raise ValueError("LibreOffice is not installed or not found")
        
        # ??????
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # ???? PPT ??
            input_file = tmpdir_path / filename
            input_file.write_bytes(ppt_bytes)
            
            # ?? PDF ????
            output_file = tmpdir_path / (input_file.stem + ".pdf")
            
            try:
                # ?? LibreOffice ????????
                cmd = [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(tmpdir_path),
                    str(input_file),
                ]
                
                logger.info(f"Converting PPT to PDF: {filename}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
                
                if process.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")
                
                # ??????PDF
                if not output_file.exists():
                    raise RuntimeError(f"PDF file not generated: {output_file}")
                
                pdf_bytes = output_file.read_bytes()
                logger.info(f"PPT converted to PDF successfully: {len(pdf_bytes)} bytes")
                return pdf_bytes
            
            except asyncio.TimeoutError:
                raise RuntimeError("PPT to PDF conversion timeout (120s)")
            except Exception as e:
                logger.error(f"PPT to PDF conversion failed: {e}", exc_info=True)
                raise RuntimeError(f"PPT to PDF conversion failed: {e}")
    
    async def convert_to_pdf(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> bytes:
        """
        ??????PDF ??
        
        Args:
            content: ????
            filename: ????
            content_type: MIME ??
        
        Returns:
            PDF ????
        """
        name_lower = filename.lower()
        
        # PPT/PPTX
        if name_lower.endswith((".ppt", ".pptx")) or content_type in (
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ):
            return await self.ppt_to_pdf(ppt_bytes=content, filename=filename)
        
        # Word (??????
        elif name_lower.endswith((".doc", ".docx")) or content_type in (
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            # ?????????
            if not self.libreoffice_path:
                raise ValueError("LibreOffice is not installed or not found")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                input_file = tmpdir_path / filename
                input_file.write_bytes(content)
                output_file = tmpdir_path / (input_file.stem + ".pdf")
                
                cmd = [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(tmpdir_path),
                    str(input_file),
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
                
                if process.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="ignore")
                    raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")
                
                if not output_file.exists():
                    raise RuntimeError(f"PDF file not generated: {output_file}")
                
                return output_file.read_bytes()
        
        else:
            raise ValueError(f"Unsupported file type for conversion: {filename} ({content_type})")


# ????????
_converter: Optional[DocumentConverter] = None


def get_document_converter(libreoffice_path: Optional[str] = None) -> DocumentConverter:
    """
    ??????????
    
    Args:
        libreoffice_path: ??? LibreOffice ????????????
    """
    global _converter
    if _converter is None:
        _converter = DocumentConverter(libreoffice_path=libreoffice_path)
    return _converter

