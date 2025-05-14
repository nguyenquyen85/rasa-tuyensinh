# Sử dụng image Python 3.9
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cập nhật pip
RUN pip install --upgrade pip

# Sao chép file requirements.txt từ thư mục gốc
COPY requirements.txt .

# Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép thư mục actions
COPY actions/ .

# Lệnh chạy Action Server
CMD ["rasa", "run", "actions", "--debug"]