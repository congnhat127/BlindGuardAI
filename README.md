# BlindGuard AI

Hệ thống AI đánh giá rủi ro theo ngữ cảnh và hỗ trợ ra quyết định trong vùng điểm mù của phương tiện cỡ lớn.
Dự án tham gia cuộc thi "Thiết kế điện tử Việt Nam 2026" (VEDC 2026) của đội Nova - Trường Đại học Bách Khoa, Đại học Đà Nẵng.

## Cấu trúc thư mục dự án

- `1_AI_Processing_Edge/`: Lớp xử lý AI trên cụm máy tính biên (NVIDIA Jetson) (Nhận diện, Tracking, Dự đoán quỹ đạo).
- `2_BlindSpot_Risk_Calculation/`: Phân hệ tính toán vùng điểm mù động và Chỉ số rủi ro điểm mù (BSRI).
- `3_Hardware_Embedded/`: Firmware vi điều khiển ESP32 và thiết kế phần cứng/sơ đồ mạch.
- `4_Cabin_HUD_UI/`: Giao diện hiển thị HUD trong cabin (Explainable AI).
- `5_Web_Cloud_Dashboard/`: Web quản trị đám mây và Backend API cho dữ liệu lưu trữ sự kiện suýt va chạm.
- `6_Docs_and_References/`: Tài liệu dự án, cấu trúc giải pháp và quy trình làm việc.
- `7_Local_Setup_Web/`: Web cài đặt tại xe (Tier 1) — công cụ cho kỹ thuật viên thiết lập kích thước xe và căn chỉnh camera bằng điện thoại/iPad, chạy trực tiếp trên Jetson. Xem `7_Local_Setup_Web/README.md`.

## Quy trình làm việc (Git Workflow)
Vui lòng tham khảo tài liệu trong `6_Docs_and_References/05_git_workflow_guidelines` để nắm rõ quy trình commit và push code của nhóm.
