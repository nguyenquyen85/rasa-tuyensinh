# Sử dụng image Python 3.9
FROM python:3.9-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cập nhật pip
RUN pip install --upgrade pip

# Sao chép file requirements.txt
COPY requirements.txt .

# Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ dự án
COPY . .

# Lệnh chạy Rasa server
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]