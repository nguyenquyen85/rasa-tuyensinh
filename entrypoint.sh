#!/bin/bash

# Gán cổng PORT của Render nếu có
PORT_TO_USE=${PORT:-5005}

# Chạy Rasa server với cổng tương ứng
rasa run --enable-api --port $PORT_TO_USE --cors "*" --debug
