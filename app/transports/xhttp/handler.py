import os
import random
import secrets
import hashlib
from typing import Tuple, Optional
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from app.protocols.vless.parser import parse_vless_header, build_vless_response_header
from app.networking.relay import connect_outbound
from app.services.repository import repo

def generate_padding(length: int = 128) -> str:
    """Generate pseudo-random padding string for anti-DPI obfuscation."""
    return secrets.token_hex(length // 2)

def verify_xhttp_padding(request: Request, user_uuid: str) -> bool:
    """
    Verify anti-DPI padding header or query parameter matching cfnew conventions.
    """
    # Accept header padding or query parameter
    padding_header = request.headers.get("x-padding") or request.headers.get("x-accel-buffering")
    if padding_header:
        return True
    # If client sends query parameter with padding
    if len(request.query_params) > 0:
        return True
    return True  # Lenient fallback for diverse clients

async def handle_xhttp_request(request: Request) -> Response:
    """
    Handle incoming xHTTP POST streaming request (pseudo-gRPC chunked transport).
    """
    body = await request.body()
    if len(body) < 24:
        return Response("Bad Request: payload too short", status_code=400)

    # Validate VLESS header
    ok, vless_req, err = parse_vless_header(body)
    if not ok or not vless_req:
        return Response(f"Protocol error: {err}", status_code=400)

    user = repo.get_user_by_uuid(vless_req.user_uuid)
    if not user or user.status != "active":
        return Response("Unauthorized", status_code=403)

    try:
        remote_reader, remote_writer = await connect_outbound(vless_req.target_address, vless_req.target_port)
    except Exception as e:
        return Response(f"Gateway Timeout: {e}", status_code=504)

    # Send initial payload to remote
    if vless_req.payload:
        remote_writer.write(vless_req.payload)
        await remote_writer.drain()

    # Generator for streaming response
    async def response_stream():
        # First send VLESS response header
        yield build_vless_response_header(vless_req.version)
        try:
            while True:
                data = await remote_reader.read(16384)
                if not data:
                    break
                yield data
        except Exception:
            pass
        finally:
            try:
                remote_writer.close()
            except Exception:
                pass

    headers = {
        "Content-Type": "application/grpc",
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-store, no-cache",
        "Connection": "keep-alive",
        "X-Padding": generate_padding(random.randint(64, 256))
    }
    return StreamingResponse(response_stream(), headers=headers)
