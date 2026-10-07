import asyncio
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.protocols.vless.parser import parse_vless_header, build_vless_response_header
from app.protocols.trojan.parser import parse_trojan_header, compute_trojan_hash
from app.networking.relay import connect_outbound
from app.services.repository import repo

logger = logging.getLogger("miliconfig.websocket")

async def handle_websocket_connection(websocket: WebSocket, path_param: str = ""):
    """
    Multiplexed WebSocket handler for VLESS and Trojan over WebSocket.
    Authenticates user, parses initial binary frame, connects to remote target,
    and pipelines bidirectional traffic with live metric logging.
    """
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    user_agent = websocket.headers.get("user-agent", "Unknown")

    remote_reader = None
    remote_writer = None
    authenticated_user = None
    protocol_type = "unknown"
    total_up = 0
    total_down = 0

    try:
        # Read first message from WebSocket
        first_message = await websocket.receive_bytes()
        total_up += len(first_message)

        # Check if VLESS (version 0x00 and len >= 24)
        if len(first_message) >= 24 and first_message[0] == 0:
            ok, vless_req, err = parse_vless_header(first_message)
            if not ok or not vless_req:
                logger.warning(f"VLESS parse error: {err}")
                await websocket.close(code=1008)
                return

            authenticated_user = repo.get_user_by_uuid(vless_req.user_uuid)
            if not authenticated_user:
                logger.warning(f"VLESS auth failed: unknown UUID {vless_req.user_uuid}")
                await websocket.close(code=1008)
                return

            if authenticated_user.status != "active":
                logger.warning(f"VLESS rejected: user {authenticated_user.username} is {authenticated_user.status}")
                await websocket.close(code=1008)
                return

            protocol_type = "vless"
            target_addr = vless_req.target_address
            target_port = vless_req.target_port
            initial_payload = vless_req.payload

            # Connect outbound
            remote_reader, remote_writer = await connect_outbound(target_addr, target_port)

            # Send VLESS response header (version 0 + 0 addon length)
            resp_hdr = build_vless_response_header(vless_req.version)
            await websocket.send_bytes(resp_hdr)
            total_down += len(resp_hdr)

            # Write initial client payload if present
            if initial_payload:
                remote_writer.write(initial_payload)
                await remote_writer.drain()

        # Check if Trojan (starts with hex string and CRLF at 56:58)
        elif len(first_message) >= 62 and first_message[56:58] == b"\r\n":
            ok, trojan_req, err = parse_trojan_header(first_message)
            if not ok or not trojan_req:
                logger.warning(f"Trojan parse error: {err}")
                await websocket.close(code=1008)
                return

            # Check users for matching Trojan password
            users = repo.list_users()
            for u in users:
                expected_hash = compute_trojan_hash(u.uuid)
                if expected_hash.lower() == trojan_req.password_hash.lower():
                    authenticated_user = u
                    break

            if not authenticated_user:
                logger.warning("Trojan auth failed: hash mismatch")
                await websocket.close(code=1008)
                return

            if authenticated_user.status != "active":
                logger.warning(f"Trojan rejected: user {authenticated_user.username} is {authenticated_user.status}")
                await websocket.close(code=1008)
                return

            protocol_type = "trojan"
            target_addr = trojan_req.target_address
            target_port = trojan_req.target_port
            initial_payload = trojan_req.payload

            remote_reader, remote_writer = await connect_outbound(target_addr, target_port)
            if initial_payload:
                remote_writer.write(initial_payload)
                await remote_writer.drain()

        else:
            logger.warning("Unrecognized proxy protocol frame over WebSocket")
            await websocket.close(code=1008)
            return

        # Record active session
        repo.record_session(authenticated_user.id, client_ip, user_agent, protocol_type)

        # Pipeline: Client (WebSocket) <-> Remote (TCP socket)
        async def ws_to_remote():
            nonlocal total_up
            try:
                while True:
                    data = await websocket.receive_bytes()
                    total_up += len(data)
                    remote_writer.write(data)
                    await remote_writer.drain()
            except WebSocketDisconnect:
                pass
            except Exception:
                pass
            finally:
                try:
                    remote_writer.close()
                except Exception:
                    pass

        async def remote_to_ws():
            nonlocal total_down
            try:
                while True:
                    data = await remote_reader.read(32768)
                    if not data:
                        break
                    total_down += len(data)
                    await websocket.send_bytes(data)
            except Exception:
                pass
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

        await asyncio.gather(ws_to_remote(), remote_to_ws())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket transport error: {e}")
    finally:
        if authenticated_user:
            repo.record_user_traffic(authenticated_user.id, total_up, total_down)
        if remote_writer:
            try:
                remote_writer.close()
            except Exception:
                pass
