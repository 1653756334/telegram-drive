# Telegram Drive 后端 v2.0

一个现代化、架构良好的文件存储系统，使用 Telegram 作为后端存储提供商。

## 🏗️ 架构设计

本项目遵循 **领域驱动设计 (DDD)** 原则和 **整洁架构** 方法：

```
app/
├── config/           # 配置层
├── core/             # 核心工具 (安全、异常、依赖)
├── domain/           # 业务逻辑层
│   ├── entities/     # 领域实体 (User, Node, Channel)
│   ├── repositories/ # 仓储接口
│   └── services/     # 领域服务
├── application/      # 应用层
│   ├── schemas/      # API 的 Pydantic 模型
│   └── use_cases/    # 应用用例
├── infrastructure/   # 基础设施层
│   ├── database/     # 数据库模型和仓储
│   └── telegram/     # Telegram 客户端集成
└── presentation/     # 表现层
    ├── api/          # REST API 路由
    └── middleware/   # HTTP 中间件
```

## 🎯 核心原则

### 高内聚，低耦合
- **领域层**: 包含纯业务逻辑，无外部依赖
- **应用层**: 编排用例，仅依赖领域层
- **基础设施层**: 实现外部关注点（数据库、Telegram）
- **表现层**: HTTP API，依赖应用层

### 依赖倒置
- 高层模块不依赖低层模块
- 两者都依赖抽象（接口）
- 仓储模式抽象数据访问

### 单一职责
- 每个类/模块只有一个变更原因
- 各层之间关注点清晰分离

## 🚀 功能特性

### 核心功能
- **文件管理**: 上传、下载、移动、重命名、删除文件
- **目录结构**: 分层文件夹组织
- **去重处理**: 基于校验和的自动文件去重
- **软删除**: 回收站功能
- **大文件支持**: 通过用户客户端处理最大 2GB 的文件

### 技术特性
- **现代 Python**: 类型提示、async/await、Pydantic v2
- **数据库**: PostgreSQL 配合 SQLAlchemy 2.0
- **API**: FastAPI 自动生成 OpenAPI 文档
- **安全性**: 加密会话存储，可选 API 令牌
- **错误处理**: 全面的异常层次结构
- **日志记录**: 带上下文的结构化日志

## 📦 安装

1. **克隆和设置**:
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境**:
```bash
cp .env.example .env
# 编辑 .env 文件配置你的设置
```

3. **运行数据库迁移**:
```bash
alembic upgrade head
```

4. **启动服务器**:
```bash
python run.py
# 或者
uvicorn app.main:app --reload
```

## 🔧 配置

环境变量（前缀：`TGDRIVE_`）：

```env
# Telegram API
TGDRIVE_API_ID=your_api_id
TGDRIVE_API_HASH=your_api_hash
TGDRIVE_BOT_TOKEN=your_bot_token

# 安全设置
TGDRIVE_SESSION_SECRET=your_secret_key
TGDRIVE_API_TOKEN=optional_api_token

# 数据库
TGDRIVE_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# 存储
TGDRIVE_STORAGE_CHANNEL_USERNAME=@your_channel
# 或者
TGDRIVE_STORAGE_CHANNEL_ID=-100xxxxxxxxx
```