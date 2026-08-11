from fastapi import FastAPI
import uvicorn

app = FastAPI(title="BlindGuard API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Hệ thống Backend BlindGuard Cloud đang hoạt động."}

@app.post("/api/events")
def receive_near_miss_event(event_data: dict):
    """
    API tiếp nhận dữ liệu 'Near Miss Event' (sự kiện suýt va chạm) 
    từ Jetson Edge gửi lên đám mây để lưu trữ.
    """
    # TODO: Lưu event_data vào cơ sở dữ liệu PostgreSQL
    print(f"Đã nhận sự kiện cảnh báo: {event_data}")
    return {"status": "success", "message": "Event recorded."}

if __name__ == "__main__":
    # Chạy server ở cổng 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
