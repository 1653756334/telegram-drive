#!/usr/bin/env python3
"""Run the Telegram Drive backend server."""

import sys
import uvicorn
from app.config.security_check import check_environment_security, SecurityCheckError, print_security_help

def main():
    """主启动函数，包含安全检测"""
    print("🚀 启动 Telegram Drive 后端服务...")
    print("=" * 50)

    # 环境变量安全检测
    try:
        check_environment_security()
        print("✅ 环境变量安全检查通过，正在启动服务...\n")
    except SecurityCheckError as e:
        # print(f"❌ 启动失败：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 安全检查过程中发生错误：{e}")
        sys.exit(1)

    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )

if __name__ == "__main__":
    main()
