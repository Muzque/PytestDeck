import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from infrastructure.report_service import (
    cleanup_report_file,
    create_report_path,
    prune_stale_reports,
)
from infrastructure.runner_service import SubprocessRunnerService

router = APIRouter(prefix="/ws", tags=["runner"])


@router.websocket("/run")
async def websocket_run(websocket: WebSocket):
    await websocket.accept()
    runner: SubprocessRunnerService | None = None

    try:
        msg_raw = await websocket.receive_text()
        msg = json.loads(msg_raw)

        action = msg.get("action", "START")
        if action == "START":
            target_path = msg.get("target_path", "")
            nodes = msg.get("nodes", [])
            marker = msg.get("marker", None)
            extra_args = msg.get("extra_args", [])

            from domain.services import resolve_target_path

            try:
                resolved_target = resolve_target_path(target_path)
            except Exception:
                resolved_target = None

            if not target_path or not resolved_target or not resolved_target.exists():
                await websocket.send_json({"type": "error", "message": f"Invalid target_path: {target_path}"})
                await websocket.close()
                return

            target_dir_str = str(resolved_target)
            runner = SubprocessRunnerService(target_dir_str)

            prune_stale_reports(target_dir_str)
            report_file = create_report_path(target_dir_str, prefix="run")
            report_json_path = str(report_file)

            async def _stream_output() -> None:
                async for chunk in runner.run_test_stream(
                    nodes=nodes,
                    marker=marker,
                    extra_args=extra_args,
                    report_json_path=report_json_path,
                ):
                    await websocket.send_text(chunk)

            async def _listen_for_stop() -> None:
                try:
                    while True:
                        ctrl_raw = await websocket.receive_text()
                        try:
                            ctrl_msg = json.loads(ctrl_raw)
                        except Exception:
                            ctrl_msg = None
                        if isinstance(ctrl_msg, dict) and ctrl_msg.get("action") == "STOP":
                            await runner.abort()
                            try:
                                await websocket.send_json(
                                    {"type": "status", "data": "Process aborted by user.\r\n"}
                                )
                            except Exception:
                                pass
                            return
                except WebSocketDisconnect:
                    await runner.abort()

            stream_task = asyncio.create_task(_stream_output())
            stop_task = asyncio.create_task(_listen_for_stop())

            try:
                done, pending = await asyncio.wait(
                    {stream_task, stop_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

                if stream_task in done and not stream_task.cancelled():
                    exc = stream_task.exception()
                    if exc is not None and not isinstance(exc, WebSocketDisconnect):
                        raise exc
            finally:
                await runner.abort()
                cleanup_report_file(report_json_path)
        elif action == "STOP":
            if runner:
                await runner.abort()
                await websocket.send_json({"type": "status", "data": "Process aborted by user.\r\n"})
    except WebSocketDisconnect:
        if runner:
            await runner.abort()
    except Exception as e:
        if runner:
            await runner.abort()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


