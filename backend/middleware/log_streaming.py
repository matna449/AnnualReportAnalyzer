"""
Log streaming middleware for capturing and streaming logs to the frontend.
"""
import logging
import asyncio
import json
import time
from typing import Dict, List, AsyncGenerator, Optional
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

# Create a custom log handler to capture logs
class LogCaptureHandler(logging.Handler):
    def __init__(self, capacity=1000):
        super().__init__()
        self.log_queue = asyncio.Queue(maxsize=capacity)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
    def emit(self, record):
        """Emit a log record to the log queue."""
        try:
            log_entry = {
                'timestamp': time.time(),
                'level': record.levelname,
                'message': self.formatter.format(record),
                'logger': record.name,
                'pipeline': 'PIPELINE:' in record.getMessage() if hasattr(record, 'getMessage') else False
            }
            
            # Only log pipeline logs to the queue
            if log_entry['pipeline']:
                # Create a coroutine to put the log entry in the queue
                async def put_log_entry():
                    try:
                        await self.log_queue.put(log_entry)
                    except Exception as e:
                        print(f"Error putting log entry in queue: {e}")
                
                # Try to schedule the coroutine in the event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(put_log_entry())
                    else:
                        # If no loop is running, use run_coroutine_threadsafe
                        asyncio.run_coroutine_threadsafe(put_log_entry(), loop)
                except RuntimeError:
                    # If there's no event loop in this thread, just pass
                    # The log will be dropped, but this is better than crashing
                    pass
        except Exception as e:
            print(f"Error in log handler: {e}")
    
    async def get_logs(self) -> AsyncGenerator[Dict, None]:
        """Get logs from the queue as an async generator."""
        while True:
            try:
                log_entry = await self.log_queue.get()
                yield log_entry
            except asyncio.CancelledError:
                break

# Create a single instance of the log handler
log_handler = LogCaptureHandler()

# Configure the root logger to use our handler
root_logger = logging.getLogger()
root_logger.addHandler(log_handler)

# Create a FastAPI middleware to add log streaming route
class LogStreamingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, path: str = "/api/logs/stream"):
        super().__init__(app)
        self.path = path
    
    async def dispatch(self, request, call_next):
        if request.url.path == self.path:
            return await self.stream_logs(request)
        return await call_next(request)
    
    async def stream_logs(self, request):
        """Stream logs as Server-Sent Events."""
        async def event_generator():
            try:
                async for log in log_handler.get_logs():
                    if log:
                        yield f"data: {json.dumps(log)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay to prevent CPU overload
            except asyncio.CancelledError:
                print("Log streaming cancelled")
                
        response = StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
        return response

def setup_log_streaming(app: FastAPI):
    """Add log streaming to FastAPI app."""
    app.add_middleware(LogStreamingMiddleware)
    print("Log streaming middleware initialized") 