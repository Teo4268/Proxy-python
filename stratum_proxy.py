import asyncio
import ssl
import socket

# Proxy config
PROXY_HOST = "0.0.0.0"       # Proxy lắng nghe trên tất cả các địa chỉ IP
PROXY_PORT = 10000            # Cổng proxy (cấu hình miner kết nối tới đây)

# Pool config
POOL_HOST = "stratum-na.rplant.xyz"  # Địa chỉ pool
POOL_PORT = 17068                   # Cổng TCPS của pool (SSL/TLS)

# Lấy địa chỉ IP của máy chạy proxy
def get_local_ip():
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)

async def handle_connection(reader, writer):
    miner_ip = writer.get_extra_info('peername')[0]  # Lấy địa chỉ IP của miner
    local_ip = get_local_ip()  # Lấy địa chỉ IP của máy chạy proxy
    print(f"Kết nối từ miner: {miner_ip} -> Proxy: {local_ip}:{PROXY_PORT}")

    # Thiết lập SSL để kết nối tới pool
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True  # Kiểm tra tên miền SSL
    ssl_context.verify_mode = ssl.CERT_REQUIRED  # Đảm bảo chứng chỉ hợp lệ

    try:
        # Kết nối tới pool qua SSL
        pool_reader, pool_writer = await asyncio.open_connection(
            POOL_HOST, POOL_PORT, ssl=ssl_context
        )
        print(f"Proxy ({local_ip}) kết nối tới pool: {POOL_HOST}:{POOL_PORT}")

        # Chuyển dữ liệu giữa miner và pool
        async def forward_data(source, destination):
            while True:
                data = await source.read(1024)
                if not data:
                    break
                destination.write(data)
                await destination.drain()

        await asyncio.gather(
            forward_data(reader, pool_writer),  # Miner -> Pool
            forward_data(pool_reader, writer)  # Pool -> Miner
        )

    except Exception as e:
        print(f"Lỗi kết nối tới pool: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Kết nối từ {miner_ip} đã đóng.")

async def main():
    local_ip = get_local_ip()  # Lấy địa chỉ IP của máy proxy
    print(f"Proxy đang chạy trên {local_ip}:{PROXY_PORT}, kết nối tới pool {POOL_HOST}:{POOL_PORT}")

    # Khởi chạy server proxy
    server = await asyncio.start_server(handle_connection, PROXY_HOST, PROXY_PORT)

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã dừng proxy.")
