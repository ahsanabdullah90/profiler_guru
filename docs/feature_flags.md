# Feature Flags & Subscription Tiers

Profile Guru includes a feature flag system designed to support subscription-based tier management. The system is fully implemented and currently configured for the **Free tier** (all core features enabled). Pro tier features are gated and ready for the subscription rollout.

---

## 1. Feature Flag Architecture (`feature_gate.py`)

The feature flag system is implemented in [feature_gate.py](file:///f:/Github/Profile-Guru/src/engine/feature_gate.py) and integrates with the settings manager for persistent storage.

### Core Functions

```python
# From src/engine/feature_gate.py
def get_feature_flags() -> dict[str, bool]:
    """Return all feature flags from settings, merged with defaults."""

def is_feature_enabled(feature_id: str) -> bool:
    """Check if a feature is enabled."""

def set_feature_flag(feature_id: str, enabled: bool):
    """Set a feature flag (for admin/tier management)."""

def get_tier_label() -> str:
    """Return the current tier label based on feature flags."""
```

### Storage

Feature flags are stored in `settings.json` under the `"feature_flags"` key. The settings manager handles persistence and atomic writes.

---

## 2. Current Feature Flags

### Free Tier Features (Currently Enabled)

| Feature ID | Description | Status |
| :--- | :--- | :--- |
| `clinical_instruments` | PHQ-9, GAD-7, BHS questionnaire scoring | ✅ Enabled |
| `trait_frameworks` | All 4 LLM-synthesized trait frameworks (Big Five, Attachment, EQ, Conversation Pattern) | ✅ Enabled |
| `unlimited_patients` | No cap on patient/contact count | ✅ Enabled |
| `whatsapp_import` | WhatsApp Bridge live ingestion + XML migration | ✅ Enabled |
| `audio_upload` | Post-session audio upload + transcription | ✅ Enabled |

### Pro Tier Features (Currently Disabled)

| Feature ID | Description | Status |
| :--- | :--- | :--- |
| `report_library` | Saved PDF report compilation and retrieval | ❌ Disabled |
| `framework_expansion_packs` | Additional assessment frameworks beyond the core 4 | ❌ Disabled |
| `cloud_sync` | Cloud backup and multi-device sync | ❌ Disabled |

---

## 3. Frontend Integration (`FeatureGate.tsx`)

The frontend provides a React context and wrapper component for consuming feature flags:

### React Context

```typescript
// From frontend/src/components/FeatureGate.tsx
const FeatureContext = React.createContext<{
  flags: Record<string, boolean>;
  isEnabled: (feature: string) => boolean;
  tier: string;
}>({
  flags: {},
  isEnabled: () => false,
  tier: 'Free',
});
```

### Usage in Components

Wrap components or sections that should be gated:

```typescript
import { useFeatureGate, TierBadge } from './FeatureGate';

function AssessmentPanel() {
  const { isEnabled, tier } = useFeatureGate();
  
  if (!isEnabled('clinical_instruments')) {
    return (
      <div className="opacity-50">
        <TierBadge tier={tier} />
        <p>Upgrade to Pro to access clinical instruments.</p>
      </div>
    );
  }
  
  return <QuestionnaireRunner />;
}
```

### TierBadge Component

Displays the current subscription tier with visual styling:

```typescript
<TierBadge tier="Free" />  // Gray badge
<TierBadge tier="Pro" />   // Gold badge with star icon
```

---

## 4. Settings UI

The **Settings → Plan** tab displays:

- Current tier label (Free / Pro)
- Feature availability matrix
- Upgrade CTA (placeholder for future payment integration)
- Feature flag toggles (admin-only, hidden in production builds)

### SubscriptionSection Component

Located in `frontend/src/components/SettingsPanel.tsx`:

```typescript
function SubscriptionSection() {
  const { flags, tier } = useFeatureGate();
  
  return (
    <div>
      <h3>Subscription Plan</h3>
      <TierBadge tier={tier} />
      <ul>
        {Object.entries(flags).map(([feature, enabled]) => (
          <li key={feature}>
            {feature}: {enabled ? '✅' : '🔒'}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 5. API Endpoints

### GET /settings/features

Returns all feature flags and current tier label.

**Response:**
```json
{
  "flags": {
    "clinical_instruments": true,
    "trait_frameworks": true,
    "unlimited_patients": true,
    "report_library": false,
    "framework_expansion_packs": false,
    "cloud_sync": false,
    "whatsapp_import": true,
    "audio_upload": true
  },
  "tier": "Free"
}
```

**Authentication:** Requires JWT (not a public route).

---

## 6. Tier Detection Logic

The `get_tier_label()` function determines the current tier based on Pro feature flags:

```python
def get_tier_label() -> str:
    """Return the current tier label based on feature flags."""
    any_pro_enabled = any(get_feature_flags().get(f, False) for f in PRO_FEATURES)
    return "Pro" if any_pro_enabled else "Free"
```

- If **any** Pro feature is enabled → tier is `"Pro"`
- If **all** Pro features are disabled → tier is `"Free"`

This allows gradual rollout: enabling one Pro feature (e.g., `report_library`) immediately upgrades the tier label.

---

## 7. Subscription Rollout Plan

### Phase 1 (Current): Free Tier GA
- All core features enabled
- No payment integration
- Feature flags stored in settings.json

### Phase 2 (Next Quarter): Pro Subscription
- Integrate Stripe or similar payment provider
- Add `/subscription/create` endpoint
- On successful payment, enable Pro feature flags
- Add billing history UI in Settings → Plan

### Phase 3 (Future): Enterprise Tier
- Add `ENTERPRISE_FEATURES` set (e.g., multi-practitioner support, audit logs, SSO)
- Extend `get_tier_label()` to return `"Enterprise"` if enterprise features are enabled
- Add license key validation

---

## 8. Testing

The feature gate system is tested in `tests/test_feature_gate.py` (if exists) or implicitly through settings API tests. Key test scenarios:

- Default flags on fresh install
- Flag persistence across restarts
- Tier label detection (Free vs. Pro)
- Frontend context provider behavior
- API endpoint response format

---

## 9. Admin Override

For development and testing, feature flags can be manually toggled via the API:

```bash
# Enable a Pro feature (for testing)
curl -X POST http://localhost:8000/api/v1/settings/features \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"feature_id": "report_library", "enabled": true}'
```

**Warning:** In production, this endpoint should be restricted to admin users or removed entirely.
