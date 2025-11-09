from __future__ import annotations

import sys

from . import app, domain, infra

sys.modules.setdefault("services.api.app", app)
sys.modules.setdefault("services.api.domain", domain)
sys.modules.setdefault("services.api.infra", infra)

