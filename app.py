"""
FastAPI web application for tax information crawler
"""
import io
import asyncio
import json
from typing import Dict, List
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import pandas as pd

from crawler import crawl_tax_code, crawl_multiple_tax_codes

app = FastAPI(title="Tax Information Crawler")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Global progress storage (in production, use Redis or similar)
progress_store: Dict[str, Dict] = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse(request, "index.html")


@app.post("/lookup")
async def crawl_single(request: Request, tax_code: str = Form(...)):
    """Crawl a single tax code"""
    try:
        result = crawl_tax_code(tax_code)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "results": [result],
                "tax_code": tax_code
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "error": f"Error: {str(e)}",
                "tax_code": tax_code
            }
        )


@app.get("/api/lookup/{tax_code}")
async def api_crawl_single(tax_code: str):
    """API endpoint to crawl a single tax code and return JSON"""
    try:
        result = crawl_tax_code(tax_code)
        return {"status": "success", "data": result}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/lookup_csv")
async def crawl_from_csv(request: Request, file: UploadFile = File(...)):
    """Crawl tax codes from uploaded CSV file with columns: dinh_danh_doanh_nghiep, ten_doanh_nghiep"""
    try:
        # Read CSV file - preserve leading zeros by reading as string
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents), dtype=str)

        # Validate CSV structure
        if df.empty:
            return templates.TemplateResponse(
                request,
                "index.html",
                {"error": "CSV file is empty"}
            )
        
        # Check if required columns exist
        if 'dinh_danh_doanh_nghiep' not in df.columns:
            return templates.TemplateResponse(
                request,
                "index.html",
                {"error": "CSV file must have 'dinh_danh_doanh_nghiep' column"}
            )

        # Get tax codes from dinh_danh_doanh_nghiep column
        tax_codes = df['dinh_danh_doanh_nghiep'].dropna().tolist()

        if not tax_codes:
            return templates.TemplateResponse(
                request,
                "index.html",
                {"error": "No tax codes found in 'dinh_danh_doanh_nghiep' column"}
            )

        # Generate session ID for progress tracking
        import uuid
        session_id = str(uuid.uuid4())

        # Initialize progress
        progress_store[session_id] = {
            'status': 'processing',
            'total': len(tax_codes),
            'completed': 0,
            'current': '',
            'message': 'Starting crawl...'
        }

        # Crawl all tax codes with anti-detection and progress tracking
        # Use larger batch_size for better performance
        if len(tax_codes) <= 10:
            batch_size = 5
            delay_range = (3, 6)
        elif len(tax_codes) <= 50:
            batch_size = 2
            delay_range = (4, 8)
        elif len(tax_codes) <= 100:
            batch_size = 2
            delay_range = (5, 9)
        else:
            batch_size = 3
            delay_range = (6, 12)

        print(f"Processing {len(tax_codes)} tax codes with batch_size={batch_size}, delay={delay_range}")

        # Check if AJAX request
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if is_ajax:
            # For AJAX requests, start background task and return session_id immediately
            def crawl_in_background():
                try:
                    from crawler import crawl_multiple_tax_codes_with_progress

                    def progress_callback(current, total, code, status):
                        progress_data = {
                            'status': 'processing',
                            'total': total,
                            'completed': current,
                            'current': code,
                            'message': status,
                            'percentage': int((current / total) * 100)
                        }
                        progress_store[session_id] = progress_data
                        print(f"[Progress] {current}/{total}: {code} - {status}")

                    results = crawl_multiple_tax_codes_with_progress(
                        tax_codes,
                        batch_size=batch_size,
                        delay_range=delay_range,
                        progress_callback=progress_callback
                    )

                    # Mark as completed and store results
                    progress_store[session_id] = {
                        'status': 'completed',
                        'total': len(tax_codes),
                        'completed': len(tax_codes),
                        'message': 'Crawling completed!',
                        'percentage': 100,
                        'results': results
                    }
                    print(f"[Completed] Stored {len(results)} results for session {session_id}")
                except Exception as e:
                    error_msg = f'Error: {str(e)}'
                    progress_store[session_id] = {
                        'status': 'error',
                        'message': error_msg
                    }
                    print(f"[Error] {error_msg}")

            # Start background task using threading
            import threading
            thread = threading.Thread(target=crawl_in_background, daemon=True)
            thread.start()

            # Return session_id immediately
            print(f"[AJAX] Starting background crawl with session_id: {session_id}")
            return {"session_id": session_id, "status": "started"}

        # For non-AJAX requests, process synchronously
        results = []
        try:
            from crawler import crawl_multiple_tax_codes_with_progress
            results = crawl_multiple_tax_codes_with_progress(
                tax_codes,
                batch_size=batch_size,
                delay_range=delay_range,
                progress_callback=lambda current, total, code, status: progress_store.update({
                    session_id: {
                        'status': 'processing',
                        'total': total,
                        'completed': current,
                        'current': code,
                        'message': status,
                        'percentage': int((current / total) * 100)
                    }
                })
            )

            # Mark as completed
            progress_store[session_id] = {
                'status': 'completed',
                'total': len(tax_codes),
                'completed': len(tax_codes),
                'message': 'Crawling completed!',
                'percentage': 100
            }
        except Exception as e:
            progress_store[session_id] = {
                'status': 'error',
                'message': f'Error: {str(e)}'
            }
            raise


        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "results": results,
                "csv_uploaded": True,
                "total_codes": len(tax_codes),
                "session_id": session_id
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error": f"Error processing CSV: {str(e)}"}
        )


@app.get("/progress/{session_id}")
async def progress_stream(session_id: str):
    """Stream progress updates using Server-Sent Events"""
    async def event_generator():
        while True:
            if session_id in progress_store:
                progress = progress_store[session_id]
                # Send progress as SSE
                yield f"data: {json.dumps(progress)}\n\n"

                # If completed or error, stop streaming (but keep data for retrieval)
                if progress.get('status') in ['completed', 'error']:
                    await asyncio.sleep(1)
                    break
            else:
                # Session not found yet, wait
                yield f"data: {json.dumps({'status': 'waiting', 'message': 'Waiting for task...'})}\n\n"

            await asyncio.sleep(0.5)  # Update every 500ms

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/results/{session_id}")
async def get_results(request: Request, session_id: str):
    """Get results after crawling is complete"""
    if session_id not in progress_store:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error": "Session not found or expired"}
        )

    progress = progress_store[session_id]

    if progress.get('status') == 'completed' and 'results' in progress:
        results = progress['results']
        total_codes = progress.get('total', len(results))

        # Clean up session after retrieving results
        del progress_store[session_id]

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "results": results,
                "csv_uploaded": True,
                "total_codes": total_codes
            }
        )
    elif progress.get('status') == 'error':
        error_msg = progress.get('message', 'Unknown error')
        del progress_store[session_id]
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error": error_msg}
        )
    else:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error": "Crawling still in progress"}
        )


@app.post("/download_excel")
async def download_excel(results_json: str = Form(...)):
    """Download results as Excel file"""
    import json
    import base64
    from datetime import datetime

    try:
        # Try to decode from base64 first
        try:
            decoded = base64.b64decode(results_json).decode('utf-8')
            results = json.loads(decoded)
        except:
            # Fallback to direct JSON parsing
            results = json.loads(results_json)

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Reorder columns: "Tên" and "MST" first, then the rest
        priority_cols = ['Tên', 'MST']
        other_cols = [col for col in df.columns if col not in priority_cols]

        # Build new column order
        new_column_order = []
        for col in priority_cols:
            if col in df.columns:
                new_column_order.append(col)
        new_column_order.extend(other_cols)

        df = df[new_column_order]

        # Create Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tax Results')

            # Auto-adjust column widths
            worksheet = writer.sheets['Tax Results']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

        output.seek(0)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tax_results_{timestamp}.xlsx"

        # Return as downloadable file
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        # Return error as plain text
        return StreamingResponse(
            io.BytesIO(f"Error creating Excel: {str(e)}".encode('utf-8')),
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=error.txt"
            }
        )


@app.post("/download_json")
async def download_json(results_json: str = Form(...)):
    """Download results as JSON file"""
    import base64
    from datetime import datetime

    try:
        # Try to decode from base64 first
        try:
            decoded = base64.b64decode(results_json).decode('utf-8')
            results = json.loads(decoded)
        except Exception:
            # Fallback to direct JSON parsing
            results = json.loads(results_json)

        # Pretty-print JSON
        json_bytes = json.dumps(
            results, ensure_ascii=False, indent=2
        ).encode('utf-8')

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tax_results_{timestamp}.json"

        return StreamingResponse(
            io.BytesIO(json_bytes),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return StreamingResponse(
            io.BytesIO(f"Error creating JSON: {str(e)}".encode('utf-8')),
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=error.txt"
            }
        )


def _build_excel_bytes(results: list) -> bytes:
    """Convert a list of result dicts to an in-memory Excel file."""
    df = pd.DataFrame(results)

    # Put Tên and MST first
    priority_cols = ["Tên", "MST"]
    other_cols = [c for c in df.columns if c not in priority_cols]
    ordered = [c for c in priority_cols if c in df.columns] + other_cols
    df = df[ordered]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tax Results")
        ws = writer.sheets["Tax Results"]
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            ws.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
    output.seek(0)
    return output.read()


def _parse_csv_upload(contents: bytes) -> list:
    """Parse CSV bytes and return list of tax codes from dinh_danh_doanh_nghiep column."""
    df = pd.read_csv(io.BytesIO(contents), dtype=str)
    if "dinh_danh_doanh_nghiep" not in df.columns:
        raise ValueError("CSV phải có cột 'dinh_danh_doanh_nghiep'")
    codes = df["dinh_danh_doanh_nghiep"].dropna().str.strip().tolist()
    if not codes:
        raise ValueError("Không tìm thấy mã số thuế nào trong cột 'dinh_danh_doanh_nghiep'")
    return codes


# ---------------------------------------------------------------------------
# API: Đồng bộ — upload CSV, trả thẳng file Excel
# ---------------------------------------------------------------------------

@app.post("/api/lookup_csv", summary="Upload CSV → trả file Excel (đồng bộ)")
async def api_lookup_csv_sync(file: UploadFile = File(...)):
    """
    Upload file CSV có cột **dinh_danh_doanh_nghiep** chứa mã số thuế.

    - Crawl toàn bộ MST.
    - Trả về file Excel (.xlsx) ngay khi hoàn thành.

    > Phù hợp cho danh sách nhỏ (≤ 20 MST). Với danh sách lớn hơn hãy dùng endpoint `/api/lookup_csv/async`.
    """
    from fastapi.responses import JSONResponse

    try:
        contents = await file.read()
        tax_codes = _parse_csv_upload(contents)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Không thể đọc file CSV: {e}"})

    try:
        from crawler import crawl_multiple_tax_codes_with_progress
        results = crawl_multiple_tax_codes_with_progress(tax_codes, batch_size=3, delay_range=(4, 7))
        excel_bytes = _build_excel_bytes(results)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    from datetime import datetime
    filename = f"tax_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/lookup_csv/json", summary="Upload CSV → trả JSON (đồng bộ)")
async def api_lookup_csv_sync_json(file: UploadFile = File(...)):
    """
    Upload file CSV có cột **dinh_danh_doanh_nghiep** chứa mã số thuế.

    - Crawl toàn bộ MST.
    - Trả về kết quả dưới dạng JSON.

    > Phù hợp cho danh sách nhỏ (≤ 20 MST). Với danh sách lớn hơn hãy dùng endpoint `/api/lookup_csv/async`.
    """
    from fastapi.responses import JSONResponse

    try:
        contents = await file.read()
        tax_codes = _parse_csv_upload(contents)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Không thể đọc file CSV: {e}"})

    try:
        from crawler import crawl_multiple_tax_codes_with_progress
        results = crawl_multiple_tax_codes_with_progress(tax_codes, batch_size=3, delay_range=(4, 7))
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    return {"status": "success", "total": len(results), "data": results}


# ---------------------------------------------------------------------------
# API: Bất đồng bộ — upload CSV, nhận session_id, poll tiến độ, tải kết quả
# ---------------------------------------------------------------------------

@app.post("/api/lookup_csv/async", summary="Upload CSV → xử lý nền, trả session_id")
async def api_lookup_csv_async(file: UploadFile = File(...)):
    """
    Upload file CSV có cột **dinh_danh_doanh_nghiep**.

    Trả về `session_id` ngay lập tức. Dùng các endpoint bên dưới để theo dõi và lấy kết quả:

    - `GET /api/progress/{session_id}` — SSE stream tiến độ (reuse `/progress/{id}`)
    - `GET /api/results/{session_id}/excel` — tải Excel khi xong
    - `GET /api/results/{session_id}/json` — lấy JSON khi xong
    """
    import uuid, threading
    from fastapi.responses import JSONResponse

    try:
        contents = await file.read()
        tax_codes = _parse_csv_upload(contents)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": f"Không thể đọc file CSV: {e}"})

    session_id = str(uuid.uuid4())
    total = len(tax_codes)

    # Chọn tốc độ crawl tuỳ kích thước
    if total <= 10:
        batch_size, delay_range = 5, (3, 6)
    elif total <= 50:
        batch_size, delay_range = 2, (4, 8)
    else:
        batch_size, delay_range = 3, (5, 10)

    progress_store[session_id] = {
        "status": "processing",
        "total": total,
        "completed": 0,
        "current": "",
        "message": "Starting crawl...",
        "percentage": 0,
    }

    def _background():
        try:
            from crawler import crawl_multiple_tax_codes_with_progress

            def _cb(current, total_n, code, status):
                progress_store[session_id] = {
                    "status": "processing",
                    "total": total_n,
                    "completed": current,
                    "current": code,
                    "message": status,
                    "percentage": int((current / total_n) * 100) if total_n else 0,
                }

            results = crawl_multiple_tax_codes_with_progress(
                tax_codes, batch_size=batch_size, delay_range=delay_range, progress_callback=_cb
            )
            progress_store[session_id] = {
                "status": "completed",
                "total": total,
                "completed": total,
                "message": "Crawling completed!",
                "percentage": 100,
                "results": results,
            }
        except Exception as e:
            progress_store[session_id] = {"status": "error", "message": str(e)}

    threading.Thread(target=_background, daemon=True).start()
    return {"session_id": session_id, "status": "started", "total": total}


@app.get("/api/progress/{session_id}", summary="SSE stream tiến độ crawl")
async def api_progress_stream(session_id: str):
    """
    Server-Sent Events stream trả về tiến độ crawl theo `session_id`.

    Mỗi event có dạng: `data: {JSON}\\n\\n`
    """
    async def _gen():
        while True:
            if session_id in progress_store:
                progress = progress_store[session_id]
                # Trả về bản copy không có results (tránh payload lớn)
                payload = {k: v for k, v in progress.items() if k != "results"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if progress.get("status") in ("completed", "error"):
                    await asyncio.sleep(0.5)
                    break
            else:
                yield f"data: {json.dumps({'status': 'waiting', 'message': 'Session chưa sẵn sàng...'})}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/results/{session_id}/excel", summary="Tải file Excel kết quả")
async def api_results_excel(session_id: str):
    """
    Tải kết quả crawl dưới dạng file Excel (.xlsx).

    Chỉ khả dụng khi `status == "completed"`. Session bị xóa sau khi tải.
    """
    from fastapi.responses import JSONResponse
    from datetime import datetime

    if session_id not in progress_store:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Session không tồn tại hoặc đã hết hạn"})

    progress = progress_store[session_id]

    if progress.get("status") == "processing":
        pct = progress.get("percentage", 0)
        return JSONResponse(status_code=202, content={"status": "processing", "percentage": pct, "message": "Đang crawl, vui lòng thử lại sau"})

    if progress.get("status") == "error":
        msg = progress.get("message", "Unknown error")
        del progress_store[session_id]
        return JSONResponse(status_code=500, content={"status": "error", "message": msg})

    results = progress.get("results", [])
    del progress_store[session_id]

    excel_bytes = _build_excel_bytes(results)
    filename = f"tax_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/results/{session_id}/json", summary="Lấy kết quả JSON")
async def api_results_json(session_id: str):
    """
    Lấy kết quả crawl dưới dạng JSON.

    Chỉ khả dụng khi `status == "completed"`. Session bị xóa sau khi lấy.
    """
    from fastapi.responses import JSONResponse

    if session_id not in progress_store:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Session không tồn tại hoặc đã hết hạn"})

    progress = progress_store[session_id]

    if progress.get("status") == "processing":
        pct = progress.get("percentage", 0)
        return JSONResponse(status_code=202, content={"status": "processing", "percentage": pct, "message": "Đang crawl, vui lòng thử lại sau"})

    if progress.get("status") == "error":
        msg = progress.get("message", "Unknown error")
        del progress_store[session_id]
        return JSONResponse(status_code=500, content={"status": "error", "message": msg})

    results = progress.get("results", [])
    total = progress.get("total", len(results))
    del progress_store[session_id]

    return {"status": "success", "total": total, "data": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

