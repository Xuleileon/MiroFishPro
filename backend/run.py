"""
MiroFish Backend 启动入口
"""

import os
import sys
import subprocess
import atexit
import socket
import logging
from urllib.parse import urlparse


# 解决 Windows 控制台中文乱码问题：在所有导入之前设置 UTF-8 编码
if sys.platform == 'win32':
    # 设置环境变量确保 Python 使用 UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # 重新配置标准输出流为 UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

# 设置日志用于启动管理
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mirofish.runner")

_mock_process = None


def stop_mock_server():
    """停止已启动的 Mock 服务器"""
    global _mock_process
    if _mock_process:
        logger.info("正在关闭 Mock 服务器...")
        _mock_process.terminate()
        try:
            _mock_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mock_process.kill()
        logger.info("Mock 服务器已关闭")
        _mock_process = None


def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def start_mock_server():
    """检测并启动 Mock 服务器"""
    global _mock_process
    
    # 只要在非 Reloader 进程中启动一次即可
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        return

    if not Config.USE_MOCK_LLM:
        return

    # 解析端口
    try:
        url = urlparse(Config.MOCK_LLM_URL)
        port = url.port or 5099
    except Exception:
        port = 5099

    if is_port_in_use(port):
        logger.info(f"端口 {port} 已被占用，假设 Mock 服务器已在运行。")
        return

    logger.info(f"🧪 正在启动 Mock 模式配套服务器 (端口 {port})...")
    
    # 脚本路径
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts/mock_openai_server.py')
    
    # 将 Mock 日志记录到文件，方便调试
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'mock_server.log')
    
    try:
        # 使用 'a' 模式追加日志
        log_file = open(log_file_path, 'a', encoding='utf-8')
        
        # 使用与当前环境一致的 Python (通过 sys.executable)
        _mock_process = subprocess.Popen(
            [sys.executable, script_path, "--port", str(port)],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            bufsize=1  # 行缓冲
        )

        # 注册退出钩子
        atexit.register(stop_mock_server)
        logger.info("🧪 Mock 服务器已在后台启动。")
    except Exception as e:
        logger.error(f"启动 Mock 服务器失败: {e}")



def main():
    """主函数"""
    # 验证配置
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f"  - {err}")
        print("\n请检查 .env 文件中的配置")
        sys.exit(1)
    
    # 自动启动 Mock 服务器
    start_mock_server()

    
    # 创建应用
    app = create_app()
    
    # 获取运行配置
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    # 启动服务
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()

