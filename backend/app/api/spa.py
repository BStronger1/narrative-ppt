from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAStaticFiles(StaticFiles):
    """本地构建与 API 同源服务，刷新客户端路由仍能加载页面。"""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if (error.status_code == 404 and scope["method"] in {"GET", "HEAD"}
                    and not path.startswith("api/") and "." not in path.rsplit("/", 1)[-1]):
                return await super().get_response("index.html", scope)
            raise
