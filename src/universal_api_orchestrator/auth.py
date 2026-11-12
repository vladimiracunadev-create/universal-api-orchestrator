"""Autorización de proveedores: API key, bearer, basic, OAuth refresh y MSAL."""
import asyncio
import base64
import os
import time

from .errors import IntegrationError
from .transport import request


class AuthManager:
    def __init__(self, store):
        self.store = store
        self.locks = {}
        self.cache = {}

    def env(self, name):
        value = os.getenv(name, "")
        if not value:
            raise IntegrationError("MISSING_CREDENTIALS")
        return value

    async def headers(self, cfg):
        kind = cfg.get("type", "none")
        if kind == "none":
            return {}
        if kind == "bearer":
            return {"Authorization": cfg.get("prefix", "Bearer") + " " + self.env(cfg["token_env"])}
        if kind == "api_key":
            return {cfg.get("header", "X-API-Key"): self.env(cfg["token_env"])}
        if kind == "basic":
            value = self.env(cfg["username_env"]) + ":" + self.env(cfg["password_env"])
            return {"Authorization": "Basic " + base64.b64encode(value.encode()).decode()}
        if kind in {"oauth2", "client_credentials"}:
            token = await self.oauth(cfg)
            return {"Authorization": "Bearer " + token}
        if kind == "msal":
            token = await self.microsoft(cfg)
            return {"Authorization": "Bearer " + token}
        raise IntegrationError("UNSUPPORTED_AUTH")

    async def oauth(self, cfg):
        name = cfg.get("token_key", cfg.get("client_id_env", "oauth"))
        async with self.locks.setdefault(name, asyncio.Lock()):
            now = time.time()
            cached = self.cache.get(name)
            if cached and cached[1] > now+60:
                return cached[0]
            saved = self.store.token_get(name) or {}
            token = saved.get("access_token", saved.get("token"))
            if token and saved.get("expires_at",0) > now+60:
                return token
            if cfg["type"] == "client_credentials":
                data = {"grant_type":"client_credentials", "client_id": self.env(cfg["client_id_env"]), "client_secret": self.env(cfg["client_secret_env"])}
                if cfg.get("scope"):
                    data["scope"] = cfg["scope"]
            else:
                if not saved.get("refresh_token"):
                    raise IntegrationError("OAUTH_CONSENT_REQUIRED")
                data = {"grant_type":"refresh_token", "refresh_token": saved["refresh_token"], "client_id": saved["client_id"]}
                if saved.get("client_secret"):
                    data["client_secret"] = saved["client_secret"]
            _, result = await request("POST", cfg["token_url"], cfg["allowed_hosts"], data=data)
            if not isinstance(result,dict) or not result.get("access_token"):
                raise IntegrationError("INVALID_TOKEN_RESPONSE")
            expiry = now + int(result.get("expires_in",300))
            self.cache[name] = result["access_token"], expiry
            if cfg["type"] == "oauth2":
                self.store.token_put(name, {**saved, **result, "expires_at":expiry})
            return result["access_token"]

    async def microsoft(self, cfg):
        name = cfg.get("token_key", "microsoft")
        async with self.locks.setdefault(name, asyncio.Lock()):
            return await asyncio.to_thread(self._microsoft_sync,cfg,name)

    def _microsoft_sync(self,cfg,name):
        try:
            import msal
        except ImportError as exc:
            raise IntegrationError("INSTALL_AUTH_EXTRA") from exc
        cache = msal.SerializableTokenCache()
        saved = self.store.token_get(name)
        if saved:
            cache.deserialize(saved["cache"])
        client = msal.PublicClientApplication(self.env(cfg["client_id_env"]),authority=cfg["authority"],token_cache=cache)
        accounts = client.get_accounts(username=cfg.get("username"))
        if len(accounts) != 1:
            raise IntegrationError("MSAL_CONSENT_OR_ACCOUNT_SELECTION_REQUIRED")
        result = client.acquire_token_silent(cfg["scopes"],account=accounts[0])
        if cache.has_state_changed:
            self.store.token_put(name,{"cache":cache.serialize()})
        if not result or not result.get("access_token"):
            raise IntegrationError("MSAL_CONSENT_REQUIRED")
        return result["access_token"]
