# Drone4Dengue E2E Tests

End-to-end tests for the **Drone4Dengue** project using **pytest**, **Selenium** (admin web), and **Appium** (iOS mobile via Expo Go or a native dev build).

Tests live under `tests/` and assume the API, admin app, and (for mobile) Expo Metro are running locally with a seeded database.

---

## Test suites

| Folder | Platform | App under test | Examples |
|--------|----------|----------------|----------|
| `tests/login/` | Web + iOS | Admin login (`client-admin`) / mobile login | Valid login, validation errors |
| `tests/register/` | Web + iOS | Registration flows | Sign-up, terms & privacy |
| `tests/resetPassword/` | Web + iOS | Password reset | OTP, new password |
| `tests/editProfile/` | Web + iOS | Profile settings | Save, validation, cancel |

- **Web tests** use the `web_driver` fixture (Chrome via Selenium).
- **Mobile tests** use the `mobile_driver` fixture (iOS Simulator + Appium).

---

## Prerequisites

### All tests

- **Python 3.10+** (3.11–3.14 supported in local development)
- **Node.js 18+** and npm (for running the apps under test)
- **PostgreSQL** (or hosted DB) with API schema migrated and **seed data**
- **Google Chrome** (web tests; ChromeDriver is installed automatically via `webdriver-manager`)

### Web tests only

- **client-admin** on `http://localhost:3000`
- **server-api** on `http://localhost:4000`

### Mobile tests only (macOS)

- **Xcode** with iOS Simulator
- **Appium 2** with the XCUITest driver
- **Expo Go** on the simulator *or* a local iOS dev build (`npx expo run:ios`)
- **client-mobile** Metro bundler on `http://127.0.0.1:8081` (default Expo port)

---

## 1. Start the applications

From the repository root, in separate terminals:

### API

```bash
cd server-api
npm install
npm run dev
```

API should listen on **http://localhost:4000** (or the port in your `server-api/.env`).

### Admin web (for web tests)

```bash
cd client-admin
npm install
npm run dev
```

Admin should be at **http://localhost:3000**.

### Mobile app (for mobile tests)

```bash
cd client-mobile
npm install
```

Create `.env` from `env.example`. For the **iOS Simulator**, use a host the simulator can reach:

```env
EXPO_PUBLIC_API_URL=http://127.0.0.1:4000
```

Start Metro:

```bash
npx expo start
```

Press **`i`** to open the iOS simulator, or open **Expo Go** on an already-booted simulator.

After changing mobile `testID`s or test-related code, reload the app in the simulator (**⌘R** in Expo Go).

---

## 2. Install Python dependencies

```bash
cd drone4dengue-tests
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Install and run Appium (mobile tests)

Install Appium and the iOS driver (once per machine):

```bash
npm install -g appium
appium driver install xcuitest
```

Boot a simulator (example):

```bash
open -a Simulator
```

Find your simulator **UDID** (needed if not using the default in `conftest.py`):

```bash
xcrun simctl list devices available
```

Start the Appium server (keep this terminal open):

```bash
appium
```

Default server URL: **http://localhost:4723**

---

## 4. Configure test environment (optional)

Environment variables override defaults in `conftest.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPO_DEV_URL` | `exp://127.0.0.1:8081` | Deep link base for Expo Go |
| `MOBILE_UDID` | (see `conftest.py`) | Target iOS Simulator UDID |
| `MOBILE_DEVICE_NAME` | `iPhone 17` | Simulator device name for Appium |
| `MOBILE_BUNDLE_ID` | auto-detected | `host.exp.Exponent` (Expo Go) or `com.adamarbain.dengueeyemobileapp` (native build) |
| `MOBILE_APP_PATH` | — | Path to `.app` if installing via Appium |

Example:

```bash
export MOBILE_UDID="<your-simulator-udid>"
export MOBILE_BUNDLE_ID=host.exp.Exponent
export EXPO_DEV_URL=exp://127.0.0.1:8081
```

`conftest.py` picks the first installed app among: requested `MOBILE_BUNDLE_ID`, native bundle id, then Expo Go.

---

## 5. Database and test accounts

Tests expect certain users to exist (see each test file for emails/passwords). Typical preconditions:

| Account | Password | Used for |
|---------|----------|----------|
| `admin@drone4dengue.com` | `Drone4Dengue!` | Admin web login |
| `wingtenglei@gmail.com` | `Drone4Dengue!` | Mobile login, profile, reset password |

Seed the database from `server-api` if needed:

```bash
cd server-api
npm run seed
```

Some registration tests also use Supabase auth cleanup in `conftest.py`. Use project credentials appropriate for your environment; do not commit real secrets to GitHub.

**Note:** `phone` is unique in the database. Mobile profile save tests generate a unique phone number per run to avoid conflicts.

---

## 6. Run tests

Activate the virtual environment from `drone4dengue-tests/`:

```bash
source venv/bin/activate
```

### All tests

```bash
pytest -v
```

### Web only

```bash
pytest tests/login/test_login_web.py -v
pytest tests/register/test_register_web.py -v
pytest tests/resetPassword/test_reset_web.py -v
pytest tests/editProfile/test_edit_profile_web.py -v
```

### Mobile only

Ensure **Appium**, **Metro**, **API**, and the **simulator app** are running first.

```bash
pytest tests/login/test_login_mobile.py -v
pytest tests/register/test_register_mobile.py -v
pytest tests/register/test_register_mobile_terms.py -v
pytest tests/resetPassword/test_reset_mobile.py -v
pytest tests/editProfile/test_edit_profile_mobile.py -v
```

### Single test

```bash
pytest tests/editProfile/test_edit_profile_mobile.py::test_successful_profile_save_mobile -v
```

### Useful pytest options

```bash
pytest -v -x              # stop on first failure
pytest -k "login" -v      # run tests whose name contains "login"
pytest --collect-only     # list tests without running
```

---

## Mobile test flow (reference)

Many mobile suites follow this pattern:

1. Accept the medical disclaimer (if shown).
2. Open the login screen (deep link or in-app navigation).
3. Log in with the mobile test user.
4. Navigate via bottom tabs / profile screens using `testID`s.

Edit profile mobile tests:

**Login → Profile tab → My Account → Edit Profile → Save → Confirm**

---

## Troubleshooting

| Symptom | Things to check |
|---------|------------------|
| Web test cannot reach admin | `client-admin` running on port 3000; Chrome installed |
| Mobile test skips / no app found | Simulator booted; Expo Go or native app installed; correct `MOBILE_UDID` |
| Login works manually but not in tests | `EXPO_PUBLIC_API_URL` uses `127.0.0.1` on iOS Simulator, not `localhost` |
| Stale UI / missing `testID` | Reload Expo (**⌘R**); confirm Metro is serving latest bundle |
| Profile save shows API error | Phone number may already exist for another user; re-run uses a new unique phone |
| `Connection refused` on port 4723 | Start Appium: `appium` |
| Element not found on bottom nav | Wait for dashboard; ensure `bottomNavBar` / tab `testID`s are in the current build |

---

## Project layout

```
drone4dengue-tests/
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── pytest.ini          # Pytest configuration
├── conftest.py         # Web + mobile fixtures, Expo / Appium setup
└── tests/
    ├── mobile_helpers.py
    ├── login/
    ├── register/
    ├── resetPassword/
    └── editProfile/
```

---

## Related documentation

- [Repository setup guide](../docs/setup-guide.md) — full stack local development
- [client-mobile README](../client-mobile/README.md) — Expo and API URL notes
- [Root README](../README.md) — project overview
