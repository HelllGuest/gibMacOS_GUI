"""
File verification utilities for gibMacOS GUI.

Provides chunklist verification and file integrity checking for downloaded files.
Based on macrecovery.py verification functions.
"""

import hashlib
import os
import struct
from typing import Generator, Tuple


class FileVerification:
    """Handles file integrity verification for downloaded macOS files."""

    # Apple's public key for signature verification
    # fmt: off
    APPLE_EFI_ROM_PUBLIC_KEY_1 = 0xC3E748CAD9CD384329E10E25A91E43E1A762FF529ADE578C935BDDF9B13F2179D4855E6FC89E9E29CA12517D17DFA1EDCE0BEBF0EA7B461FFE61D94E2BDF72C196F89ACD3536B644064014DAE25A15DB6BB0852ECBD120916318D1CCDEA3C84C92ED743FC176D0BACA920D3FCF3158AFF731F88CE0623182A8ED67E650515F75745909F07D415F55FC15A35654D118C55A462D37A3ACDA08612F3F3F6571761EFCCBCC299AEE99B3A4FD6212CCFFF5EF37A2C334E871191F7E1C31960E010A54E86FA3F62E6D6905E1CD57732410A3EB0C6B4DEFDABE9F59BF1618758C751CD56CEF851D1C0EAA1C558E37AC108DA9089863D20E2E7E4BF475EC66FE6B3EFDCF  # noqa: E501
    # fmt: on

    # Chunklist structures
    CHUNKLIST_HEADER = struct.Struct("<4sIBBBxQQQ")
    CHUNK = struct.Struct("<I32s")

    def __init__(self):
        assert self.CHUNKLIST_HEADER.size == 0x24
        assert self.CHUNK.size == 0x24

    def verify_chunklist(
        self, chunklist_path: str
    ) -> Generator[Tuple[int, bytes], None, None]:
        """
        Verify a chunklist file and yield chunk information.

        Args:
            chunklist_path: Path to the chunklist file

        Yields:
            Tuple of (chunk_size, chunk_sha256) for each chunk

        Raises:
            ValueError: If chunklist is invalid or corrupted
            RuntimeError: If digital signature is missing
        """
        if not os.path.exists(chunklist_path):
            raise FileNotFoundError(f"Chunklist file not found: {chunklist_path}")

        with open(chunklist_path, "rb") as f:
            # Read and verify header
            data = f.read(self.CHUNKLIST_HEADER.size)
            if len(data) != self.CHUNKLIST_HEADER.size:
                raise ValueError("Invalid chunklist: header too short")

            hash_ctx = hashlib.sha256()
            hash_ctx.update(data)

            (
                magic,
                header_size,
                file_version,
                chunk_method,
                signature_method,
                chunk_count,
                chunk_offset,
                signature_offset,
            ) = self.CHUNKLIST_HEADER.unpack(data)

            # Validate header fields
            if magic != b"CNKL":
                raise ValueError("Invalid chunklist: wrong magic number")
            if header_size != self.CHUNKLIST_HEADER.size:
                raise ValueError("Invalid chunklist: wrong header size")
            if file_version != 1:
                raise ValueError("Invalid chunklist: unsupported file version")
            if chunk_method != 1:
                raise ValueError("Invalid chunklist: unsupported chunk method")
            if signature_method not in [1, 2]:
                raise ValueError("Invalid chunklist: unsupported signature method")
            if chunk_count <= 0:
                raise ValueError("Invalid chunklist: invalid chunk count")
            if chunk_offset != 0x24:
                raise ValueError("Invalid chunklist: wrong chunk offset")
            if signature_offset != chunk_offset + self.CHUNK.size * chunk_count:
                raise ValueError("Invalid chunklist: wrong signature offset")

            # Read chunks
            for _ in range(chunk_count):
                data = f.read(self.CHUNK.size)
                if len(data) != self.CHUNK.size:
                    raise ValueError("Invalid chunklist: chunk data truncated")

                hash_ctx.update(data)
                chunk_size, chunk_sha256 = self.CHUNK.unpack(data)
                yield chunk_size, chunk_sha256

            # Verify signature
            digest = hash_ctx.digest()

            if signature_method == 1:
                # RSA signature verification
                data = f.read(256)
                if len(data) != 256:
                    raise ValueError("Invalid chunklist: signature truncated")

                signature = int.from_bytes(data, "little")
                plaintext = int(
                    f'0x1{"f"*404}003031300d060960864801650304020105000420{"0"*64}', 16
                ) | int.from_bytes(digest, "big")

                if (
                    pow(signature, 0x10001, self.APPLE_EFI_ROM_PUBLIC_KEY_1)
                    != plaintext
                ):
                    raise ValueError("Invalid chunklist: signature verification failed")

            elif signature_method == 2:
                # Simple hash verification
                data = f.read(32)
                if data != digest:
                    raise ValueError("Invalid chunklist: hash verification failed")
                raise RuntimeError("Chunklist missing digital signature")

            # Ensure file is completely read
            if f.read(1):
                raise ValueError("Invalid chunklist: extra data after signature")

    def verify_file_against_chunklist(
        self, file_path: str, chunklist_path: str
    ) -> bool:
        """
        Verify a file against its chunklist.

        Args:
            file_path: Path to the file to verify
            chunklist_path: Path to the chunklist file

        Returns:
            True if verification passes, False otherwise
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                for chunk_size, expected_hash in self.verify_chunklist(chunklist_path):
                    # Read chunk data
                    chunk_data = f.read(chunk_size)
                    if len(chunk_data) != chunk_size:
                        return False  # File truncated

                    # Verify chunk hash
                    chunk_hash = hashlib.sha256(chunk_data).digest()
                    if chunk_hash != expected_hash:
                        return False  # Hash mismatch

            # Ensure file is completely read
            if f.read(1):
                return False  # Extra data in file

            return True

        except Exception:
            return False

    def calculate_file_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """
        Calculate hash of a file.

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            Hexadecimal hash string
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        hash_func = getattr(hashlib, algorithm.lower(), None)
        if not hash_func:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        hash_obj = hash_func()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def verify_file_hash(
        self, file_path: str, expected_hash: str, algorithm: str = "sha256"
    ) -> bool:
        """
        Verify file hash against expected value.

        Args:
            file_path: Path to the file
            expected_hash: Expected hash value (hex string)
            algorithm: Hash algorithm to use (default: sha256)

        Returns:
            True if hash matches, False otherwise
        """
        try:
            actual_hash = self.calculate_file_hash(file_path, algorithm)
            return actual_hash.lower() == expected_hash.lower()
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> dict:
        """
        Get comprehensive file information including size and hashes.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        stat_info = os.stat(file_path)

        return {
            "path": file_path,
            "size": stat_info.st_size,
            "size_human": self._format_size(stat_info.st_size),
            "sha256": self.calculate_file_hash(file_path, "sha256"),
            "md5": self.calculate_file_hash(file_path, "md5"),
            "modified": stat_info.st_mtime,
            "is_file": os.path.isfile(file_path),
            "is_directory": os.path.isdir(file_path),
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math

        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
