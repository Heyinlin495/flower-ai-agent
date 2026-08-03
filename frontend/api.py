"""
花卉识别 AI Agent - 前端 API 工具

统一封装与后端的 HTTP 通信，所有页面共用：
- 统一错误处理（连接失败/非 200 → {"success": False, "error": ...}）
- 统一超时、异常捕获，避免各页面重复写 try/except
"""

import requests

from config import API_BASE_URL, API_TOKEN

_DEFAULT_TIMEOUT = 15


def auth_headers() -> dict:
    """携带 Bearer Token 的请求头（未配置 API_TOKEN 时返回空 dict，本地开发不受影响）"""
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}


def _error(msg: str) -> dict:
    """构造统一错误响应"""
    return {"success": False, "error": msg}


def api_get(path: str, params: dict | None = None, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """GET 请求后端，返回 JSON dict（失败返回统一错误结构）"""
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", params=params, headers=auth_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return _error(f"API 错误: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        return _error("无法连接到后端服务")
    except Exception as e:
        return _error(str(e))


def api_post(path: str, json: dict | None = None, timeout: int = 30) -> dict:
    """POST 请求后端（JSON body），返回 JSON dict（失败返回统一错误结构）"""
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=json, headers=auth_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return _error(f"API 错误: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        return _error("无法连接到后端服务")
    except Exception as e:
        return _error(str(e))


def api_post_files(path: str, files: dict, timeout: int = 120) -> dict:
    """POST 请求后端（multipart 文件上传），返回 JSON dict"""
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", files=files, headers=auth_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return _error(f"API 错误({resp.status_code}): {detail}")
    except requests.exceptions.ConnectionError:
        return _error("无法连接到后端服务")
    except Exception as e:
        return _error(str(e))


def api_delete(path: str, timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """DELETE 请求后端，返回 JSON dict（失败返回统一错误结构）"""
    try:
        resp = requests.delete(f"{API_BASE_URL}{path}", headers=auth_headers(), timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        return _error(f"API 错误: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        return _error("无法连接到后端服务")
    except Exception as e:
        return _error(str(e))
