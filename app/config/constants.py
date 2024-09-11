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

from __future__ import annotations

"""Name of the favicon file in the static directory"""
DB_SESSION_DEPENDENCY_KEY = "db_session"
"""The name of the key used for dependency injection of the database
session."""
USER_DEPENDENCY_KEY = "current_user"
"""The name of the key used for dependency injection of the database
session."""
DTO_INFO_KEY = "info"
"""The name of the key used for storing DTO information."""
DEFAULT_PAGINATION_SIZE = 10
"""Default page size to use."""
HEALTH_ENDPOINT = "/health"
"""The endpoint to use for the the service health check."""
SITE_INDEX = "/"
"""The site index URL."""
OPENAPI_SCHEMA = "/schema"
