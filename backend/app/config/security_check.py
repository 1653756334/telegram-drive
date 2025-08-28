"""Environment variables security check module."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set
from ..config.logging import get_logger

# 尝试导入 python-dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = get_logger(__name__)


class SecurityCheckError(Exception):
    """Exception raised when critical security checks fail."""
    pass


# 默认值字典 - 来自 .env.example 文件
DEFAULT_VALUES = {
    "TGDRIVE_API_ID": "123456",
    "TGDRIVE_API_HASH": "your_api_hash",
    "TGDRIVE_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "TGDRIVE_SESSION_SECRET": "change_me_generate_random_long_secret",
    "TGDRIVE_DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_drive",
    "TGDRIVE_STORAGE_CHANNEL_USERNAME": "",
    "TGDRIVE_STORAGE_CHANNEL_ID": "",
    "TGDRIVE_LOG_LEVEL": "INFO",
    "TGDRIVE_CORS_ORIGINS": '["*"]',
    "TGDRIVE_ADMIN_USERNAME": "admin",
    "TGDRIVE_JWT_SECRET_KEY": "your-super-secret-jwt-key-change-this-in-production",
    "TGDRIVE_JWT_ALGORITHM": "HS256",
    "TGDRIVE_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
}

# 关键安全变量 - 如果是默认值则启动失败
CRITICAL_SECURITY_VARS = {
    "TGDRIVE_API_ID",
    "TGDRIVE_API_HASH", 
    "TGDRIVE_BOT_TOKEN",
    "TGDRIVE_SESSION_SECRET",
    "TGDRIVE_JWT_SECRET_KEY",
    "TGDRIVE_ADMIN_USERNAME",
    "TGDRIVE_DATABASE_URL",
}

def check_environment_security() -> None:
    """
    检查环境变量安全性。

    - 检查关键安全变量是否还是默认值，如果是则抛出异常阻止启动
    - 检查重要变量是否是默认值，如果是则记录警告

    Raises:
        SecurityCheckError: 当关键安全变量使用默认值时
    """
    logger.info("开始环境变量安全检查...")

    # 尝试加载 .env 文件
    if DOTENV_AVAILABLE:
        # .env 文件位于 backend 目录下，直接查找当前目录
        env_file = os.path.join(os.getcwd(), '.env')

        if os.path.exists(env_file):
            logger.info(f"加载环境变量文件: {env_file}")
            load_dotenv(env_file)
        else:
            logger.warning(f"未找到 .env 文件: {env_file}")
            logger.warning("请确保在 backend 目录下运行，并且存在 .env 文件")
    else:
        logger.warning("python-dotenv 未安装，无法加载 .env 文件")

    critical_issues: List[str] = []
    
    # 检查所有环境变量
    for var_name, default_value in DEFAULT_VALUES.items():
        current_value = os.getenv(var_name)
        
        # 如果环境变量未设置，跳过检查
        if current_value is None:
            continue
            
        # 检查是否使用默认值
        if current_value == default_value:
            if var_name in CRITICAL_SECURITY_VARS:
                critical_issues.append(var_name)
    
    # 处理关键安全问题
    if critical_issues:
        error_msg = "🚨 安全检查失败！以下关键环境变量仍使用默认值，必须修改后才能启动:\n"
        for var in critical_issues:
            error_msg += f"   - {var} = {DEFAULT_VALUES[var]}\n"
        error_msg += "\n请按以下步骤修改:\n"
        error_msg += "1. 复制 backend/.env.example 为 backend/.env\n"
        error_msg += "2. 修改 .env 文件中的敏感信息\n"
        error_msg += "3. 重新启动应用\n"
        
        logger.error(error_msg)
        raise SecurityCheckError(error_msg)
    
    # 检查通过
    logger.info("✅ 环境变量安全检查通过")


def get_security_recommendations() -> Dict[str, str]:
    """
    获取安全建议。
    
    Returns:
        Dict[str, str]: 变量名到建议的映射
    """
    return {
        "TGDRIVE_API_ID": "从 https://my.telegram.org 获取你的 API ID",
        "TGDRIVE_API_HASH": "从 https://my.telegram.org 获取你的 API Hash", 
        "TGDRIVE_BOT_TOKEN": "从 @BotFather 获取你的 Bot Token",
        "TGDRIVE_SESSION_SECRET": "生成一个32位以上的随机字符串用于加密会话",
        "TGDRIVE_JWT_SECRET_KEY": "生成一个强随机字符串用于JWT签名",
        "TGDRIVE_DATABASE_URL": "配置你的PostgreSQL数据库连接",
        "TGDRIVE_ADMIN_USERNAME": "设置管理员用户名",
    }


def print_security_help() -> None:
    """打印安全配置帮助信息。"""
    print("\n" + "="*60)
    print("🔒 Telegram Drive 安全配置指南")
    print("="*60)
    print("\n1. 复制示例配置文件:")
    print("   cp backend/.env.example backend/.env")
    print("\n2. 编辑 backend/.env 文件，修改以下关键变量:")
    
    recommendations = get_security_recommendations()
    for var in CRITICAL_SECURITY_VARS:
        if var in recommendations:
            print(f"   - {var}: {recommendations[var]}")
    
    print("\n4. 重新启动应用")
    print("="*60 + "\n")


if __name__ == "__main__":
    """命令行工具：检查环境变量安全性。"""
    try:
        check_environment_security()
        print("✅ 环境变量安全检查通过")
    except SecurityCheckError as e:
        print(f"❌ {e}")
        sys.exit(1)
