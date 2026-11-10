# Bài làm: ReAct agent viết từ đầu

## Phần đã triển khai

- `tools.py`: gợi ý áo mỏng khi nhiệt độ > 30°C, áo khoác nhẹ ở nhánh còn lại;
  thêm ô/áo mưa khi xác suất mưa > 0.5; báo lỗi nếu xác suất nằm ngoài [0, 1].
- Schema `recommend_outfit`: hai tham số bắt buộc, kiểu number, mô tả °C và xác suất 0–1.
- `agent.py`: lưu nguyên phản hồi assistant, thực thi mọi tool_use, ghép kết quả theo ID,
  gửi tất cả tool_result trong một lượt user, rồi gọi model tiếp; tối đa 6 lượt model.
- Hỗ trợ key Anthropic hoặc OpenRouter. Lần chạy thực tế dùng OpenRouter với
  `anthropic/claude-haiku-5.5`, lấy key từ `.env`.
- `check.py` kiểm tra thêm ngưỡng 30°C/50%, nhiều tool trong một lượt, sửa tham số sau lỗi,
  câu trả lời trực tiếp và giới hạn vòng lặp. `test_provider.py` có 4 kiểm tra định tuyến API.

## Kiểm chứng và giới hạn bộ chấm

Ngày chạy: 10/11/2026, múi giờ Việt Nam. Dữ liệu thời tiết là dữ liệu giả lập của bài tập.

`check.py` đạt 3/3 TODO; cả 4 kiểm tra trong `test_provider.py` đạt.
Lần chấm đầu đạt 20/20 PASS (mỗi mức 5/5), lưu tại
`experiments/baseline_before_prompt_fix/report.md` và `report.json`.

Đọc câu trả lời M1 và H5 của lần đầu cho thấy model tự thêm ô/áo mưa khi xác suất mưa 30%.
Các điều kiện hiện tại không kiểm tra việc thêm đồ che mưa trong hai câu này, nên vẫn PASS.
Đây là điểm sai ở bước tổng hợp câu trả lời: kết quả tool đúng, nhưng model thêm lời khuyên
không theo quy tắc của bài. Đã bổ sung prompt: chỉ tư vấn đồ khi được hỏi, bám đúng `items`,
không thêm ô/áo mưa để “phòng hờ” khi xác suất mưa ≤ 50%.

Báo cáo chính `report.md` và `report.json` được dùng cho lần chấm lại sau sửa prompt.
Kết quả lần chấm lại: **20/20 PASS, 0 PARTIAL, 0 FAIL**, mỗi mức đều đạt 5/5.
Đã đọc lại M1 và H5: M1 chỉ trả nhiệt độ/xác suất mưa; H5 chỉ gợi ý áo thun mỏng, vải cotton,
không còn thêm ô/áo mưa. Trung bình 2.4 lượt model và 4.0 giây mỗi câu trong lần chạy này.
Điểm số chỉ phản ánh các điều kiện trong bộ chấm trên 20 câu; không chứng minh mọi câu trả lời
ngoài dataset đều đúng. Ví dụ, kiểm tra `contains` có thể chấp nhận một đáp án chỉ nhắc tới
thành phố đúng mà chưa thực sự kết luận đúng.

## Trả lời câu hỏi suy nghĩ

### 1. Phân tích một câu PARTIAL và cách sửa

Lần chấm đầu không có FAIL/PARTIAL, nên chọn H1 trong thí nghiệm giới hạn 2 vòng:

1. Vòng 1 gọi `get_current_date`, xác định ngày mai là 11/11/2026.
2. Vòng 2 gọi `get_weather` cho cả Đà Nẵng và Phú Quốc; nhận xác suất mưa 30% và 60%.
3. Agent chạm giới hạn và trả thông báo dừng, chưa có lượt model để kết luận Đà Nẵng ít mưa hơn.

Thought/Action và Observation của hai vòng đều phù hợp. Nguyên nhân là giới hạn vòng lặp,
không phải dữ liệu tool sai. Khôi phục `MAX_ITERATIONS = 6` cho phép hoàn tất bước tổng hợp;
H1 đã PASS trong báo cáo cấu hình 6 vòng. Sửa prompt không thể thay thế lượt model còn thiếu.
Ngoài ra, vấn đề gợi ý đồ che mưa ở M1/H5 được xử lý bằng sửa prompt như mô tả ở trên.

### 2. Bỏ get_current_date khỏi TOOLS

Kết quả thực đo: nhóm medium giảm từ **5/5 PASS xuống 0/5 PASS, 5 FAIL**.
Xem `experiments/without_date/report.md`.

Cả 5 câu dùng ngày tương đối. Khi schema ngày không còn được gửi cho model, model trả lời
rằng chưa biết ngày cụ thể và hỏi lại người dùng; không gọi tool thời tiết. Hàm Python
`get_current_date` vẫn tồn tại nhưng model không biết nó có sẵn. Agent không tự bịa ngày,
nhưng không hoàn thành tác vụ nên bộ chấm đánh FAIL.

### 3. Giới hạn MAX_ITERATIONS = 2

Kết quả thực đo trên hard: **0/5 PASS, 4 PARTIAL, 1 FAIL**.
Xem `experiments/limit_2/report.md`.

H1–H4 đã lấy đủ dữ liệu ở vòng 2 nhưng chưa có lượt tổng hợp, nên PARTIAL.
H5 mới tra xong thời tiết, chưa gọi `recommend_outfit` và chưa có đáp án, nên FAIL.
Với chuỗi ngày → thời tiết → trang phục → đáp án, thông thường cần 4 lượt model.

Giới hạn vòng lặp giúp chặn agent gọi tool vô hạn, kiểm soát thời gian và chi phí API.
Cần đặt đủ lớn cho chuỗi công việc; bài này giữ 6 vòng. Các thí nghiệm thay đổi biến trong
tiến trình riêng, không sửa file `agent.py` hoặc ghi đè báo cáo chính.

## Chạy lại

```powershell
.\.venv\Scripts\python.exe -X utf8 check.py
.\.venv\Scripts\python.exe -X utf8 -m unittest test_provider -v
.\.venv\Scripts\python.exe -X utf8 evaluate.py
.\.venv\Scripts\python.exe -X utf8 experiments.py
```

Hai lệnh cuối sử dụng API. `evaluate.py --ids M1,H5` cho phép chỉ kiểm tra các câu vừa sửa,
nhưng sẽ ghi đè báo cáo chính bằng kết quả của tập con đó.
