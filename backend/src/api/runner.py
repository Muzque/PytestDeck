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

            try:
                async for chunk in runner.run_test_stream(
                    nodes=nodes,
                    marker=marker,
                    extra_args=extra_args,
                    report_json_path=report_json_path,
                ):

                    await websocket.send_text(chunk)
            finally:
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

