from fastapi import FastAPI

from iptv_tools.api.routes.proxy import router as proxy_router

app = FastAPI(title="IPTV Tools API", version="0.1.0")

app.include_router(proxy_router)
