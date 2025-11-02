# Authentication Guide

## Overview

The Politician Trading Tracker uses `streamlit-authenticator` for secure user authentication. This provides:

- **Secure password hashing** using bcrypt
- **Session management** with cookies
- **Simple login/logout** interface
- **Easy to enable/disable** for development

## Setup

### 1. Default Credentials

The app comes with a default admin account:

```
Username: admin
Password: demo123
```

**⚠️ IMPORTANT:** Change these credentials in production!

### 2. Configuration

Authentication is configured in `.streamlit/secrets.toml`:

```toml
[auth]
enabled = true  # Set to false to disable authentication

[auth.cookie]
name = "politician_tracker_auth"
key = "random_signature_key_change_this_in_production"  # Change this!
expiry_days = 30

[auth.credentials.usernames.admin]
password = "$2b$12$..."  # Hashed password
name = "Administrator"
email = "admin@example.com"
```

### 3. Adding New Users

To add a new user:

1. Generate a password hash:
   ```bash
   python scripts/generate_password_hash.py your_password
   ```

2. Add the user to `.streamlit/secrets.toml`:
   ```toml
   [auth.credentials.usernames.john]
   password = "$2b$12$..."  # Use the generated hash
   name = "John Doe"
   email = "john@example.com"
   ```

3. For Streamlit Cloud, add the same configuration to your app's secrets in the Streamlit Cloud dashboard.

## Usage

### In Main App (app.py)

Authentication is already added to `app.py`:

```python
from auth_utils import require_authentication
require_authentication()
```

### In Pages

Add authentication to any page by adding this at the top (after imports):

```python
import streamlit as st

# ... other imports ...

# Page config
st.set_page_config(...)

# Require authentication
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from auth_utils import require_authentication
require_authentication()

# ... rest of your page code ...
```

## Deployment

### Streamlit Cloud

1. Go to your app's settings on Streamlit Cloud
2. Navigate to "Secrets"
3. Add the entire `[auth]` section from your local `.streamlit/secrets.toml`
4. Save and redeploy

### Security Best Practices

1. **Change the cookie key**: Use a random string for `auth.cookie.key`
   ```python
   import secrets
   secrets.token_urlsafe(32)
   ```

2. **Change default password**: Always change the default admin password

3. **Use HTTPS**: Ensure your app is served over HTTPS (Streamlit Cloud does this automatically)

4. **Strong passwords**: Use strong, unique passwords for all accounts

5. **Regular updates**: Keep `streamlit-authenticator` updated

## Disabling Authentication

For local development, you can disable authentication:

```toml
[auth]
enabled = false
```

Or comment out the `require_authentication()` calls in your code.

## Troubleshooting

### Login not working

1. Check that secrets are loaded correctly:
   ```python
   import streamlit as st
   st.write(st.secrets.get('auth', 'Not found'))
   ```

2. Verify password hash is correct (regenerate if needed)

3. Clear browser cookies and try again

### Authentication bypassed

1. Check that `enabled = true` in secrets
2. Ensure `require_authentication()` is called before page content
3. Verify secrets are deployed to Streamlit Cloud

### Password generation fails

Make sure `bcrypt` is installed:
```bash
pip install bcrypt
```

## API Reference

### `require_authentication()`

Checks if user is authenticated. If not, shows login form and stops page execution.

```python
from auth_utils import require_authentication
require_authentication()
```

### `check_authentication()`

Returns `True` if authenticated, `False` otherwise. Does not stop execution.

```python
from auth_utils import check_authentication

if check_authentication():
    st.write("Welcome!")
else:
    st.write("Please log in")
```

## Example Pages

See `app.py` for the main app authentication example.

To add authentication to a page like `pages/1_📥_Data_Collection.py`, add:

```python
# At the top of the file, after imports
from auth_utils import require_authentication
require_authentication()
```

That's it! The page will now require authentication before displaying any content.
