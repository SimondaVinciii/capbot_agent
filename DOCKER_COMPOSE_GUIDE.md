# Docker Compose Guide for CapBot Agent

## Tổng quan

File `docker-compose.yml` này cung cấp một môi trường containerized hoàn chỉnh cho hệ thống CapBot Agent, bao gồm:

- **CapBot API**: Ứng dụng FastAPI chính
- **SQL Server**: Cơ sở dữ liệu (tùy chọn, chỉ khi cần)
- **Redis**: Cache (tùy chọn, cho tương lai)
- **Traefik**: Reverse proxy (tùy chọn)

## Cài đặt và Chạy

### 1. Chuẩn bị môi trường

```bash
# Copy file cấu hình mẫu
cp docker-compose.env .env

# Chỉnh sửa các biến môi trường trong .env
# Đặc biệt chú ý:
# - GOOGLE_API_KEY: API key của Google AI
# - DATABASE_URL: URL kết nối database
```

### 2. Chạy ứng dụng cơ bản

```bash
# Chạy chỉ CapBot API
docker-compose up -d capbot-api

# Xem logs
docker-compose logs -f capbot-api
```

### 3. Chạy với database

```bash
# Chạy với SQL Server
docker-compose --profile database up -d

# Hoặc chạy tất cả services
docker-compose up -d
```

### 4. Chạy với reverse proxy

```bash
# Chạy với Traefik proxy
docker-compose --profile proxy up -d

# Truy cập:
# - API: http://capbot.local
# - Traefik Dashboard: http://localhost:8080
```

## Profiles

### `database`
- Bao gồm SQL Server container
- Sử dụng khi cần database local

### `cache`
- Bao gồm Redis container
- Sử dụng cho caching (tương lai)

### `proxy`
- Bao gồm Traefik reverse proxy
- Sử dụng cho production deployment

## Cấu hình

### Biến môi trường quan trọng

| Biến | Mô tả | Mặc định |
|------|-------|----------|
| `GOOGLE_API_KEY` | API key Google AI | **Bắt buộc** |
| `DATABASE_URL` | URL kết nối database | SQL Server local |
| `CHROMA_COLLECTION_NAME` | Tên collection ChromaDB | `topics_collection` |
| `SIMILARITY_THRESHOLD` | Ngưỡng tương đồng | `0.8` |
| `DEBUG` | Chế độ debug | `False` |
| `EMBEDDING_BACKEND` | Backend embedding | `sentence` |

### Volumes

- `chroma_data`: Lưu trữ dữ liệu ChromaDB
- `sqlserver_data`: Lưu trữ dữ liệu SQL Server
- `redis_data`: Lưu trữ dữ liệu Redis

## Lệnh hữu ích

### Quản lý containers

```bash
# Khởi động
docker-compose up -d

# Dừng
docker-compose down

# Dừng và xóa volumes
docker-compose down -v

# Rebuild
docker-compose up --build -d

# Xem logs
docker-compose logs -f [service_name]

# Vào container
docker-compose exec capbot-api bash
```

### Health checks

```bash
# Kiểm tra trạng thái
docker-compose ps

# Kiểm tra health
docker-compose exec capbot-api python -c "
import requests
try:
    response = requests.get('http://localhost:8000/api/v1/health')
    print(f'Status: {response.status_code}')
    print(f'Response: {response.json()}')
except Exception as e:
    print(f'Error: {e}')
"
```

## Troubleshooting

### Lỗi kết nối database

```bash
# Kiểm tra SQL Server
docker-compose logs sqlserver

# Test kết nối
docker-compose exec capbot-api python -c "
from app.models.database import engine
try:
    with engine.connect() as conn:
        print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

### Lỗi ChromaDB

```bash
# Kiểm tra ChromaDB
docker-compose exec capbot-api ls -la /app/chroma_db

# Reset ChromaDB
docker-compose down
docker volume rm capbot_agent_chroma_data
docker-compose up -d
```

### Lỗi Google AI

```bash
# Kiểm tra API key
docker-compose exec capbot-api python -c "
import os
print(f'GOOGLE_API_KEY set: {bool(os.getenv(\"GOOGLE_API_KEY\"))}')
"
```

## Production Deployment

### 1. Cấu hình production

```bash
# Tạo file .env.production
cp docker-compose.env .env.production

# Chỉnh sửa cho production:
# - DEBUG=False
# - DATABASE_URL=production_database_url
# - GOOGLE_API_KEY=production_api_key
```

### 2. Chạy production

```bash
# Sử dụng file env production
docker-compose --env-file .env.production up -d

# Hoặc với proxy
docker-compose --env-file .env.production --profile proxy up -d
```

### 3. Monitoring

```bash
# Xem resource usage
docker stats

# Xem logs
docker-compose logs -f --tail=100
```

## Backup và Restore

### Backup

```bash
# Backup ChromaDB
docker run --rm -v capbot_agent_chroma_data:/data -v $(pwd):/backup alpine tar czf /backup/chroma_backup.tar.gz -C /data .

# Backup SQL Server
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "BACKUP DATABASE capbot_db TO DISK = '/var/opt/mssql/backup/capbot_db.bak'"
```

### Restore

```bash
# Restore ChromaDB
docker run --rm -v capbot_agent_chroma_data:/data -v $(pwd):/backup alpine tar xzf /backup/chroma_backup.tar.gz -C /data
```

## Security Notes

1. **Đổi mật khẩu SQL Server** trong production
2. **Sử dụng secrets** cho API keys
3. **Cấu hình firewall** cho ports
4. **Sử dụng HTTPS** trong production
5. **Backup định kỳ** dữ liệu

## Liên hệ

Nếu có vấn đề, vui lòng tạo issue hoặc liên hệ team phát triển.
