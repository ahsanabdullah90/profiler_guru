"""Feature flag system for free/pro tier gating.

Flags are stored in settings.json under "feature_flags".
Free tier = True for all core features. Pro gated features are
marked False and need a subscription upgrade.

The feature flag system is designed for the subscription rollout
next quarter. Currently all flags are True (free tier).
"""


from src.engine.settings_manager import settings_manager

FREE_FEATURES = frozenset([
    "clinical_instruments",
    "trait_frameworks",
    "unlimited_patients",
    "whatsapp_import",
    "audio_upload",
])

PRO_FEATURES = frozenset([
    "report_library",
    "framework_expansion_packs",
    "cloud_sync",
])


def get_feature_flags() -> dict[str, bool]:
    """Return all feature flags from settings, merged with defaults."""
    defaults = {
        "clinical_instruments": True,
        "trait_frameworks": True,
        "unlimited_patients": True,
        "report_library": False,
        "framework_expansion_packs": False,
        "cloud_sync": False,
        "whatsapp_import": True,
        "audio_upload": True,
    }
    stored = settings_manager.get_setting("feature_flags", {})
    if isinstance(stored, dict):
        defaults.update(stored)
    return defaults


def is_feature_enabled(feature_id: str) -> bool:
    """Check if a feature is enabled."""
    return get_feature_flags().get(feature_id, False)


def set_feature_flag(feature_id: str, enabled: bool):
    """Set a feature flag (for admin/tier management)."""
    flags = get_feature_flags()
    flags[feature_id] = enabled
    settings_manager.set_setting("feature_flags", flags)


def get_tier_label() -> str:
    """Return the current tier label based on feature flags."""
    # If all PRO features are disabled, it's the free tier
    any_pro_enabled = any(get_feature_flags().get(f, False) for f in PRO_FEATURES)
    return "Pro" if any_pro_enabled else "Free"
