# Descope React SDK - Integration Guide

The Descope React SDK provides an easy way to add authentication to React applications with built-in components, hooks, and utilities for authentication flows.

## Installation

```bash
npm install @descope/react-sdk
# or
yarn add @descope/react-sdk
# or
pnpm add @descope/react-sdk
```

## Quick Setup

### 1. Add Descope Provider

Wrap your application with the `DescopeProvider` component:

```jsx
// src/index.jsx or src/index.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from '@descope/react-sdk'
import App from './App'

const root = ReactDOM.createRoot(document.getElementById('root'))
root.render(
  <React.StrictMode>
    <AuthProvider
      projectId="YOUR_PROJECT_ID"
      baseUrl="https://api.descope.com" // optional
      persistTokens={true} // optional
      autoRefresh={true} // optional
    >
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
```

### 2. Add Authentication Component

Use the Descope Flow component to render a hosted authentication form:

```jsx
// src/components/Login.jsx
import React from 'react'
import { Descope, useSession } from '@descope/react-sdk'
import { useNavigate } from 'react-router-dom'

function Login() {
  const { isAuthenticated } = useSession()
  const navigate = useNavigate()

  // Redirect to dashboard if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  const onSuccess = (e) => {
    console.log('User authenticated:', e.detail.user)
    navigate('/dashboard')
  }

  const onError = (e) => {
    console.error('Authentication error:', e)
  }

  return (
    <div className="login-container">
      <h1>Sign In</h1>
      <Descope
        flowId="sign-up-or-in"
        onSuccess={onSuccess}
        onError={onError}
        theme="light"
      />
    </div>
  )
}

export default Login
```

## Configuration Options

When configuring the `AuthProvider`, you can use the following options:

```jsx
<AuthProvider
  // Required: Your Descope Project ID
  projectId="YOUR_PROJECT_ID"
  // Optional: Descope API base URL (defaults to https://api.descope.com)
  baseUrl="https://api.descope.com"
  // Optional: Store tokens in browser storage (default: true)
  persistTokens={true}
  // Optional: Auto refresh session before expiry (default: true)
  autoRefresh={true}
  // Optional: Store session token in a cookie instead of localStorage
  sessionTokenViaCookie={true}
  // or with cookie options
  sessionTokenViaCookie={{
    sameSite: 'Strict',
    secure: true,
  }}
  // Optional: OIDC configuration
  oidcConfig={true} // or detailed config object
  // Optional: Debug mode (default: false)
  debug={false}
>
  <App />
</AuthProvider>
```

## Authentication Components

### Descope Flow Component

The `Descope` component renders a full-featured authentication UI:

```jsx
import { Descope } from '@descope/react-sdk'

function AuthenticationForm() {
  return (
    <Descope
      flowId="sign-up-or-in"
      tenant="my-tenant" // optional
      theme={{
        root: {
          colorScheme: 'light',
          fontFamily: 'Roboto, sans-serif',
        },
      }}
      locale="en" // optional
      debug={false} // optional
      elementId="auth-container" // optional
      redirectUrl="/dashboard" // optional
      autoFocus={true} // optional
      uiConfig={{
        buttons: {
          primary: {
            borderRadius: '4px',
          },
        },
      }}
      onSuccess={(e) => console.log('Success', e.detail)}
      onError={(e) => console.error('Error', e)}
      onReady={() => console.log('Flow component is ready')}
    />
  )
}
```

## React Hooks

### useSession

The `useSession` hook provides access to the authentication session state:

```jsx
import { useSession } from '@descope/react-sdk'

function Dashboard() {
  const { isAuthenticated, isSessionLoading, sessionToken } = useSession()

  if (isSessionLoading) {
    return <div>Loading...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  return (
    <div>
      <h1>Welcome to Dashboard</h1>
    </div>
  )
}
```

### useUser

The `useUser` hook provides access to the authenticated user information:

```jsx
import { useUser } from '@descope/react-sdk'

function Profile() {
  const { user, isUserLoading } = useUser()

  if (isUserLoading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      <h1>Welcome, {user?.name}</h1>
      <p>Email: {user?.email}</p>
    </div>
  )
}
```

### useDescope

The `useDescope` hook provides access to the Descope SDK instance:

```jsx
import { useDescope } from '@descope/react-sdk'

function LogoutButton() {
  const sdk = useDescope()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await sdk.logout()
    navigate('/login')
  }

  return <button onClick={handleLogout}>Logout</button>
}
```

## Route Protection

Create a wrapper component to protect authenticated routes:

```jsx
// src/components/ProtectedRoute.jsx
import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useSession } from '@descope/react-sdk'

function ProtectedRoute() {
  const { isAuthenticated, isSessionLoading } = useSession()

  if (isSessionLoading) {
    return <div>Loading...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  return <Outlet />
}

export default ProtectedRoute
```

Then use it in your router configuration:

```jsx
// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './components/Home'
import Login from './components/Login'
import Dashboard from './components/Dashboard'
import Profile from './components/Profile'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

## FedCM (Federated Credential Management)

Implement FedCM for passwordless authentication with Chrome's native UI:

```jsx
// src/components/FedCMLogin.jsx
import React, { useState, useEffect } from 'react'
import { useDescope } from '@descope/react-sdk'
import { useNavigate } from 'react-router-dom'

function FedCMLogin() {
  const sdk = useDescope()
  const navigate = useNavigate()
  const [isFedCMSupported, setIsFedCMSupported] = useState(false)

  useEffect(() => {
    // Check if FedCM is supported
    setIsFedCMSupported(sdk.fedcm?.isSupported?.() ?? false)
  }, [sdk.fedcm])

  const loginWithFedCM = async () => {
    try {
      // Configure FedCM provider
      const fedcmConfig = {
        provider: 'google',
        clientId: 'YOUR_CLIENT_ID',
      }

      // Authenticate with FedCM
      const response = await sdk.fedcm.authenticate(fedcmConfig)

      if (response.ok) {
        console.log('Successfully authenticated with FedCM')
        navigate('/dashboard')
      }
    } catch (error) {
      console.error('FedCM authentication failed:', error)
    }
  }

  if (!isFedCMSupported) {
    return (
      <div>
        <p>FedCM is not supported in this browser.</p>
        {/* Fallback authentication option */}
      </div>
    )
  }

  return <button onClick={loginWithFedCM}>Sign in with FedCM</button>
}

export default FedCMLogin
```

## Google One Tap Integration

Implement Google One Tap for a frictionless sign-in experience:

```jsx
// src/components/OneTapLogin.jsx
import React, { useState, useEffect, useRef } from 'react'
import { useDescope } from '@descope/react-sdk'
import { useNavigate } from 'react-router-dom'

function OneTapLogin() {
  const sdk = useDescope()
  const navigate = useNavigate()
  const [isInitialized, setIsInitialized] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    const initOneTap = async () => {
      try {
        // Initialize One Tap
        await sdk.oneTap?.initialize({
          auto_select: true,
        })

        setIsInitialized(true)

        // Optionally show the prompt automatically
        showOneTap()
      } catch (error) {
        console.error('Failed to initialize One Tap:', error)
      }
    }

    initOneTap()

    return () => {
      // Clean up One Tap
      sdk.oneTap?.cancel()
    }
  }, [sdk.oneTap])

  const showOneTap = async () => {
    if (!isInitialized) return

    try {
      // Display One Tap prompt and get credential
      const credential = await sdk.oneTap.prompt()

      // Verify credential with Descope
      const response = await sdk.oneTap?.verify(credential)

      if (response?.ok) {
        console.log('Successfully authenticated with One Tap')
        navigate('/dashboard')
      }
    } catch (error) {
      console.error('One Tap authentication failed:', error)
    }
  }

  return (
    <div>
      <div id="one-tap-container" ref={containerRef}></div>
      <button disabled={!isInitialized} onClick={showOneTap}>
        Sign in with Google
      </button>
    </div>
  )
}

export default OneTapLogin
```

## OIDC (OpenID Connect) Implementation

Configure OIDC for redirect-based authentication:

```jsx
// src/index.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from '@descope/react-sdk'
import App from './App'

const root = ReactDOM.createRoot(document.getElementById('root'))
root.render(
  <React.StrictMode>
    <AuthProvider
      projectId="YOUR_PROJECT_ID"
      oidcConfig={{
        applicationId: 'YOUR_APPLICATION_ID', // Optional
        redirectUri: 'https://your-app.com/callback',
        scope: 'openid profile email',
      }}
    >
      <App />
    </AuthProvider>
  </React.StrictMode>,
)
```

### OIDC Login Component

```jsx
// src/components/OIDCLogin.jsx
import React from 'react'
import { useDescope } from '@descope/react-sdk'

function OIDCLogin() {
  const sdk = useDescope()

  const loginWithOIDC = async () => {
    try {
      await sdk.oidc?.loginWithRedirect({
        redirect_uri: window.location.origin + '/callback',
      })
    } catch (error) {
      console.error('Failed to initiate OIDC login:', error)
    }
  }

  return <button onClick={loginWithOIDC}>Login with OIDC</button>
}

export default OIDCLogin
```

### OIDC Callback Component

```jsx
// src/components/OIDCCallback.jsx
import React, { useEffect } from 'react'
import { useDescope } from '@descope/react-sdk'
import { useNavigate } from 'react-router-dom'

function OIDCCallback() {
  const sdk = useDescope()
  const navigate = useNavigate()

  useEffect(() => {
    const completeLogin = async () => {
      try {
        // Complete the OIDC login
        await sdk.oidc?.finishLoginIfNeeded()
        navigate('/dashboard')
      } catch (error) {
        console.error('OIDC login failed:', error)
        navigate('/login')
      }
    }

    completeLogin()
  }, [sdk.oidc, navigate])

  return <div>Completing login...</div>
}

export default OIDCCallback
```

## Common Patterns

### Access Token for API Calls

```jsx
import { useSession } from '@descope/react-sdk'

function ApiComponent() {
  const { sessionToken } = useSession()

  const fetchData = async () => {
    const response = await fetch('/api/data', {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    })
    return response.json()
  }

  // ...
}
```

### Conditional Rendering Based on Auth State

```jsx
import { useSession, useUser } from '@descope/react-sdk'

function Header() {
  const { isAuthenticated } = useSession()
  const { user } = useUser()

  return (
    <header>
      {isAuthenticated ? (
        <span>Welcome, {user?.name}</span>
      ) : (
        <a href="/login">Sign In</a>
      )}
    </header>
  )
}
```
