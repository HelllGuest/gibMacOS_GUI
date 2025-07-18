#!/usr/bin/env python3
"""
gibMacOS GUI
https://github.com/HelllGuest/gibMacOS_GUI

Original gibMacOS by corpnewt: https://github.com/corpnewt/gibMacOS
macrecovery.py by acidanthera team: https://github.com/acidanthera/OpenCorePkg

GUI Author: Anoop Kumar
License: MIT
"""

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.gui.dialogs import ask_overwrite_file


class Downloader:
    def __init__(self, skip_w=False, skip_q=False, skip_s=False, interactive=True):
        self.prog_len = 20
        self.last_percent = -1
        self.start_time = 0
        self.indent = 4
        self.total = -1
        self.interactive = interactive
        self.bytes_downloaded = 0
        self.resume_header = {}

        # Enhanced headers for better compatibility
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        # Network configuration - more lenient for large files
        self.timeout = 60  # Increased from 30 to 60 seconds
        self.max_retries = 5  # Increased from 3 to 5 attempts
        self.retry_delay = 3  # Increased initial delay
        self.chunk_size = 1024 * 8  # 8KB chunks for better performance

        self.skip_w = skip_w
        self.skip_q = skip_q
        self.skip_s = skip_s

    def _create_session_with_retries(self):
        """Create a requests session with retry configuration."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=self.retry_delay,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def resize(self, prog_len):
        self.prog_len = prog_len

    def get_time_string(self, t):
        if t < 60:
            return "{: >2}s".format(int(t))
        elif t < 3600:
            return "{: >2}m {: >2}s".format(int(t // 60), int(t % 60))
        else:
            return "{: >2}h {: >2}m {: >2}s".format(
                int(t // 3600), int((t % 3600) // 60), int(t % 60)
            )

    def get_size(self, size):
        if size < 1024:
            return "{: >3} B".format(size)
        elif size < 1024**2:
            return "{: >3.1f} KB".format(size / 1024)
        elif size < 1024**3:
            return "{: >3.1f} MB".format(size / 1024**2)
        elif size < 1024**4:
            return "{: >3.1f} GB".format(size / 1024**3)
        else:
            return "{: >3.1f} TB".format(size / 1024**4)

    def test_url_accessibility(self, url, suppress_errors=False):
        """Test if a URL is accessible and return detailed information."""
        session = self._create_session_with_retries()

        try:
            print(f"Testing URL accessibility: {url}")

            # Test HEAD request first
            try:
                head_req = session.head(url, headers=self.headers, timeout=self.timeout)
                print(f"HEAD request status: {head_req.status_code}")
                print(
                    f"Content-Length: {head_req.headers.get('Content-Length', 'Not provided')}"
                )
                print(
                    f"Content-Type: {head_req.headers.get('Content-Type', 'Not provided')}"
                )
                return head_req.status_code == 200
            except requests.exceptions.RequestException as e:
                print(f"HEAD request failed: {e}")

            # Try GET request if HEAD fails
            try:
                get_req = session.get(
                    url, headers=self.headers, timeout=self.timeout, stream=True
                )
                print(f"GET request status: {get_req.status_code}")
                print(
                    f"Content-Length: {get_req.headers.get('Content-Length', 'Not provided')}"
                )
                print(
                    f"Content-Type: {get_req.headers.get('Content-Type', 'Not provided')}"
                )
                return get_req.status_code == 200
            except requests.exceptions.RequestException as e:
                print(f"GET request failed: {e}")

            return False

        except Exception as e:
            if not suppress_errors:
                print(f"URL accessibility test failed: {e}")
            return False

    def get_string(self, url, suppress_errors=False):
        """Get string content from URL with retry mechanism."""
        session = self._create_session_with_retries()

        for attempt in range(self.max_retries + 1):
            try:
                req = session.get(url, headers=self.headers, timeout=self.timeout)
                req.raise_for_status()
                return req.content.decode("utf-8")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    if not suppress_errors:
                        print(f"Attempt {attempt + 1} failed for {url}: {e}")
                        print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    if not suppress_errors:
                        print(
                            f"Error getting string from {url} after {self.max_retries + 1} attempts: {e}"
                        )
                    return None
        return None

    def get_bytes(self, url, suppress_errors=False):
        """Get bytes content from URL with retry mechanism."""
        session = self._create_session_with_retries()

        for attempt in range(self.max_retries + 1):
            try:
                req = session.get(url, headers=self.headers, timeout=self.timeout)
                req.raise_for_status()
                return req.content
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    if not suppress_errors:
                        print(f"Attempt {attempt + 1} failed for {url}: {e}")
                        print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    if not suppress_errors:
                        print(
                            f"Error getting bytes from {url} after {self.max_retries + 1} attempts: {e}"
                        )
                    return None
        return None

    def stream_to_file(
        self,
        url,
        file_path,
        resume_bytes=0,
        total_bytes=-1,
        allow_resume=True,
        callback=None,
        cancel_event=None,
        parent_window=None,
    ):
        """Stream download to file with enhanced error handling and retry mechanisms."""
        import os

        # File existence check and GUI dialog
        if os.path.exists(file_path) and (resume_bytes == 0):
            if parent_window is not None:
                overwrite = ask_overwrite_file(parent_window, file_path)
                if not overwrite:
                    print(
                        f"Skipping download: {file_path} already exists and user chose not to overwrite."
                    )
                    return None
            else:
                print(
                    f"File {file_path} exists. No parent window for dialog; skipping download."
                )
                return None
        session = self._create_session_with_retries()
        original_retry_delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                self.bytes_downloaded = resume_bytes
                self.total = total_bytes
                self.start_time = time.time()

                if cancel_event and cancel_event.is_set():
                    return None

                # Setup resume headers
                self.resume_header = (
                    {"Range": "bytes={}-".format(resume_bytes)}
                    if allow_resume and resume_bytes > 0
                    else {}
                )

                # Get total file size if not provided
                if self.total == -1 and allow_resume and resume_bytes > 0:
                    try:
                        if cancel_event and cancel_event.is_set():
                            return None
                        print(f"Getting file size for {os.path.basename(file_path)}...")
                        head_req = session.head(
                            url, headers=self.headers, timeout=self.timeout
                        )
                        head_req.raise_for_status()
                        self.total = int(head_req.headers.get("Content-Length", 0))
                        print(f"File size: {self.get_size(self.total)}")
                    except requests.exceptions.RequestException as e:
                        print(f"Could not get file size: {e}")
                        pass

                if cancel_event and cancel_event.is_set():
                    return None

                # Start the download
                print(
                    f"Starting download attempt {attempt + 1}/{self.max_retries + 1} for {os.path.basename(file_path)}"
                )
                req = session.get(
                    url,
                    headers={**self.headers, **self.resume_header},
                    stream=True,
                    timeout=self.timeout,
                )
                req.raise_for_status()

                # Get total size from response headers if not already set
                if self.total == -1:
                    try:
                        self.total = int(req.headers.get("Content-Length", 0))
                        print(f"File size from response: {self.get_size(self.total)}")
                    except (ValueError, KeyError):
                        print("Could not determine file size from response headers")
                        pass

                # Download the file
                with open(
                    file_path, "ab" if allow_resume and resume_bytes > 0 else "wb"
                ) as f:
                    for chunk in req.iter_content(chunk_size=self.chunk_size):
                        if cancel_event and cancel_event.is_set():
                            return None
                        if chunk:
                            f.write(chunk)
                            self.bytes_downloaded += len(chunk)
                            if callback:
                                callback(
                                    self.bytes_downloaded, self.total, self.start_time
                                )

                # Verify download completed successfully
                if os.path.exists(file_path):
                    actual_size = os.path.getsize(file_path)
                    if self.total > 0 and actual_size != self.total:
                        print(
                            f"Warning: Downloaded size ({self.get_size(actual_size)}) doesn't match expected size ({self.get_size(self.total)})"
                        )
                        if attempt < self.max_retries:
                            print("Retrying download due to size mismatch...")
                            os.remove(file_path)
                            time.sleep(self.retry_delay)
                            self.retry_delay *= 2
                            continue
                    else:
                        print(
                            f"Download completed successfully: {os.path.basename(file_path)} ({self.get_size(actual_size)})"
                        )
                        return file_path
                else:
                    print(f"Error: File was not created: {file_path}")
                    return None

            except requests.exceptions.HTTPError as e:
                print(
                    f"HTTP Error {e.response.status_code} for {os.path.basename(file_path)}: {e}"
                )
                if e.response.status_code == 416 and allow_resume and resume_bytes > 0:
                    # Range not satisfiable - retry from beginning
                    print(
                        f"Server returned 416. Retrying download from scratch for {os.path.basename(file_path)}."
                    )
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return self.stream_to_file(
                        url,
                        file_path,
                        resume_bytes=0,
                        total_bytes=-1,
                        allow_resume=False,
                        callback=callback,
                        cancel_event=cancel_event,
                    )
                elif (
                    e.response.status_code in [429, 500, 502, 503, 504]
                    and attempt < self.max_retries
                ):
                    # Retryable server errors
                    print(
                        f"Server error {e.response.status_code}. Retrying in {self.retry_delay} seconds..."
                    )
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2
                    continue
                elif e.response.status_code == 404:
                    print(f"File not found (404): {url}")
                    return None
                elif e.response.status_code == 403:
                    print(f"Access forbidden (403): {url}")
                    return None
                else:
                    print(
                        f"Download failed due to HTTP error {e.response.status_code}: {e}"
                    )
                    return None

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                if attempt < self.max_retries:
                    print(f"Network error (attempt {attempt + 1}): {e}")
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2
                    continue
                else:
                    print(
                        f"Download failed due to network error after {self.max_retries + 1} attempts: {e}"
                    )
                    return None

            except Exception as e:
                print(f"Download failed due to unexpected error: {e}")
                print(f"Error type: {type(e).__name__}")
                if attempt < self.max_retries:
                    print(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2
                    continue
                return None

        # Reset retry delay for next download
        self.retry_delay = original_retry_delay
        return None
