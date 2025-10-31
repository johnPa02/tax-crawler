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
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/crawl")
async def crawl_single(request: Request, tax_code: str = Form(...)):
    """Crawl a single tax code"""
    try:
        result = await crawl_tax_code(tax_code)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": [result],
                "tax_code": tax_code
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": f"Error: {str(e)}",
                "tax_code": tax_code
            }
        )


@app.post("/crawl_csv")
async def crawl_from_csv(request: Request, file: UploadFile = File(...)):
    """Crawl tax codes from uploaded CSV file with columns: dinh_danh_doanh_nghiep, ten_doanh_nghiep"""
    try:
        # Read CSV file - preserve leading zeros by reading as string
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents), dtype=str)

        # Validate CSV structure
        if df.empty:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": "CSV file is empty"}
            )
        
        # Check if required columns exist
        if 'dinh_danh_doanh_nghiep' not in df.columns:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": "CSV file must have 'dinh_danh_doanh_nghiep' column"}
            )

        # Get tax codes from dinh_danh_doanh_nghiep column
        tax_codes = df['dinh_danh_doanh_nghiep'].dropna().tolist()

        if not tax_codes:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error": "No tax codes found in 'dinh_danh_doanh_nghiep' column"}
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
            delay_range = (1, 2)
        elif len(tax_codes) <= 50:
            batch_size = 2
            delay_range = (3, 5)
        elif len(tax_codes) <= 100:
            batch_size = 2
            delay_range = (3, 6)
        else:
            batch_size = 3
            delay_range = (3, 5)

        print(f"Processing {len(tax_codes)} tax codes with batch_size={batch_size}, delay={delay_range}")

        # Check if AJAX request
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if is_ajax:
            # For AJAX requests, start background task and return session_id immediately
            async def crawl_in_background():
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

                    results = await crawl_multiple_tax_codes_with_progress(
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

            # Start background task
            asyncio.create_task(crawl_in_background())

            # Return session_id immediately
            print(f"[AJAX] Starting background crawl with session_id: {session_id}")
            return {"session_id": session_id, "status": "started"}

        # For non-AJAX requests, process synchronously
        results = []
        try:
            from crawler import crawl_multiple_tax_codes_with_progress
            results = await crawl_multiple_tax_codes_with_progress(
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
            "index.html",
            {
                "request": request,
                "results": results,
                "csv_uploaded": True,
                "total_codes": len(tax_codes),
                "session_id": session_id
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": f"Error processing CSV: {str(e)}"}
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
            "index.html",
            {"request": request, "error": "Session not found or expired"}
        )

    progress = progress_store[session_id]

    if progress.get('status') == 'completed' and 'results' in progress:
        results = progress['results']
        total_codes = progress.get('total', len(results))

        # Clean up session after retrieving results
        del progress_store[session_id]

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": results,
                "csv_uploaded": True,
                "total_codes": total_codes
            }
        )
    elif progress.get('status') == 'error':
        error_msg = progress.get('message', 'Unknown error')
        del progress_store[session_id]
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": error_msg}
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "Crawling still in progress"}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
