# fraud_detection/api/routes/__init__.py
from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router
from .model import router as model_router
from .predictions import router as predictions_router
from .transactions import router as transactions_router

__all__ = [
    'auth_router',
    'admin_router',
    'health_router',
    'model_router',
    'predictions_router',
    'transactions_router'
]
