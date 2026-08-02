from .auth import router as auth_router
from .health import router as health_router
from .model import router as model_router
from .predictions import router as predictions_router
from .transactions import router as transactions_router
from .admin import router as admin_router
from .samples import router as samples_router
from .monitoring import router as monitoring_router
from .agent import router as agent_router   # <-- NEW

__all__ = [
    'auth_router',
    'admin_router',
    'health_router',
    'model_router',
    'predictions_router',
    'transactions_router',
    'samples_router',
    'monitoring_router',   # <-- added
]