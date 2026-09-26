from __future__ import annotations

from flask import Flask

from gerdiary.config import Settings
from gerdiary.infrastructure.database import db, migrate
from gerdiary.modules.budget.models import Budget  # noqa: F401
from gerdiary.modules.budget.routes import budget_blueprint
from gerdiary.modules.categories.routes import categories_blueprint
from gerdiary.modules.datarights.routes import datarights_blueprint
from gerdiary.modules.health.routes import health_blueprint
from gerdiary.modules.identity.routes import identity_blueprint
from gerdiary.modules.journal.models import FoodEntry, SymptomEvent  # noqa: F401
from gerdiary.modules.journal.routes import journal_blueprint
from gerdiary.modules.nutrition.models import NutritionCacheEntry  # noqa: F401
from gerdiary.modules.nutrition.routes import nutrition_blueprint
from gerdiary.modules.spending.models import Account, Vendor  # noqa: F401
from gerdiary.modules.spending.routes import spending_blueprint
from gerdiary.modules.trigger_preferences.models import (  # noqa: F401
    UserTriggerPreference,
)
from gerdiary.modules.trigger_preferences.routes import trigger_preferences_blueprint
from gerdiary.shared.errors import register_error_handlers
from gerdiary.shared.request_id import register_request_id


def create_app(settings: Settings | None = None) -> Flask:
    resolved_settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config.update(resolved_settings.to_flask_config())

    db.init_app(app)
    migrate.init_app(app, db)
    register_request_id(app)
    register_error_handlers(app)
    app.register_blueprint(health_blueprint, url_prefix="/api/v1")
    app.register_blueprint(identity_blueprint, url_prefix="/api/v1")
    app.register_blueprint(categories_blueprint, url_prefix="/api/v1")
    app.register_blueprint(journal_blueprint, url_prefix="/api/v1")
    app.register_blueprint(spending_blueprint, url_prefix="/api/v1")
    app.register_blueprint(budget_blueprint, url_prefix="/api/v1")
    app.register_blueprint(datarights_blueprint, url_prefix="/api/v1")
    app.register_blueprint(trigger_preferences_blueprint, url_prefix="/api/v1")
    app.register_blueprint(nutrition_blueprint, url_prefix="/api/v1")

    return app
