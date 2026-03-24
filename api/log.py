"""Centralized logging for PSR.

Azure Functions Python worker intercepts the root logger and forwards
messages to the host, which sends them to App Insights under the
``Function.<name>.User`` category.  Using ``logging.getLogger(__name__)``
in submodules works for HTTP triggers but can silently drop logs in
timer-triggered and Durable Functions contexts.

Fix: every module imports ``log`` from here.  We use a child of the root
logger (name="psr") so messages always propagate to the worker's handler.
We also silence the noisy Azure SDK HTTP loggers that otherwise flood
App Insights traces.
"""

import logging

# Silence Azure SDK HTTP request/response noise (severity INFO).
# These produce hundreds of Cosmos/Blob REST traces per invocation.
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.storage").setLevel(logging.WARNING)

# Single app-wide logger.  Child of root → always propagates to the
# Azure Functions worker handler regardless of invocation context.
log = logging.getLogger("psr")
