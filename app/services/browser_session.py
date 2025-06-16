# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Browser fingerprinting for session management without login."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar import Request


class BrowserFingerprint:
    """Generate browser fingerprints for session identification."""

    @staticmethod
    def generate_fingerprint(request: Request) -> str:
        """Generate a semi-stable browser fingerprint from request headers."""
        # Collect fingerprinting data
        fingerprint_data = []

        # IP address (with fallback for proxies)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP", "")
            or request.client.host if request.client else "unknown"
        )
        fingerprint_data.append(f"ip:{client_ip}")

        # User agent (most stable identifier)
        user_agent = request.headers.get("User-Agent", "unknown")
        fingerprint_data.append(f"ua:{user_agent}")

        # Accept language (relatively stable)
        accept_language = request.headers.get("Accept-Language", "unknown")
        fingerprint_data.append(f"lang:{accept_language}")

        # Accept encoding (stable for same browser)
        accept_encoding = request.headers.get("Accept-Encoding", "unknown")
        fingerprint_data.append(f"enc:{accept_encoding}")

        # Host header (for multi-tenant scenarios)
        host = request.headers.get("Host", "unknown")
        fingerprint_data.append(f"host:{host}")

        # Combine all data and hash
        combined = "|".join(fingerprint_data)

        # Use SHA-256 for consistent, collision-resistant fingerprint
        fingerprint_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        # Use first 16 characters for manageable session IDs
        return f"browser_{fingerprint_hash[:16]}"

    @staticmethod
    def get_stable_user_id(request: Request) -> str:
        """Get a stable user ID based on browser fingerprint."""
        return BrowserFingerprint.generate_fingerprint(request)
