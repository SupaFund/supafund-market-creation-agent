# 🔧 AWS App Runner 环境变量配置指南

## 必需的环境变量

在AWS App Runner控制台中配置以下环境变量：

### 1. Supabase数据库配置

```bash
# Supabase项目URL
SUPABASE_URL=https://your-project-id.supabase.co

# Supabase服务角色密钥（不是匿名密钥！）
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**获取方式：**
1. 登录 [Supabase Dashboard](https://supabase.com/dashboard)
2. 选择你的项目
3. 点击左侧菜单 "Settings" → "API"
4. 复制 "URL" 和 "service_role" 密钥

### 2. 区块链配置

```bash
# 以太坊私钥（必须以0x开头）
OMEN_PRIVATE_KEY=0x1234567890abcdef...

# The Graph API密钥
GRAPH_API_KEY=your-thegraph-api-key
```

**获取The Graph API密钥：**
1. 访问 [The Graph Studio](https://thegraph.com/studio/)
2. 连接钱包并创建API密钥
3. 复制生成的API密钥

### 3. 系统环境变量

```bash
# Python路径配置（AWS App Runner需要）
PYTHONPATH=/app:/app/gnosis_predict_market_tool

# Python缓冲配置
PYTHONUNBUFFERED=1

# 端口配置
PORT=8000

# 并发配置
WEB_CONCURRENCY=1
```

### 4. 可选配置

```bash
# Grok AI API密钥（用于市场解析，可选）
GROK_API_KEY=grok-your-api-key
```

## 在AWS控制台配置步骤

### 方法1：创建服务时配置

1. 在"Configure service"步骤中
2. 展开"Environment variables"部分
3. 点击"Add environment variable"
4. 逐个添加上述变量

### 方法2：服务创建后配置

1. 在AWS App Runner控制台选择你的服务
2. 点击"Configuration"标签页
3. 点击"Configure"按钮
4. 滚动到"Environment variables"部分
5. 点击"Edit"
6. 添加或修改环境变量
7. 点击"Save changes"

## 安全最佳实践

### ✅ 正确做法
- 使用AWS App Runner的环境变量功能
- 私钥以0x开头的完整格式
- 使用Supabase service_role密钥（而不是anon密钥）
- 定期轮换API密钥

### ❌ 避免做法
- 不要在代码中硬编码密钥
- 不要提交.env文件到GitHub
- 不要使用Supabase的匿名密钥作为SUPABASE_KEY
- 不要在日志中打印敏感信息

## 测试环境变量配置

部署完成后，通过健康检查端点验证配置：

```bash
curl https://your-app-url.region.awsapprunner.com/health
```

正确配置的响应应该包含：
```json
{
  "status": "healthy",
  "blockchain_module": "available",
  "environment": {
    "pythonpath_set": true,
    "gnosis_tool_available": true
  }
}
```

## 故障排除

### 问题1：SUPABASE_KEY无效
**症状：** 数据库连接失败
**解决：** 确认使用的是service_role密钥，不是anon密钥

### 问题2：OMEN_PRIVATE_KEY格式错误
**症状：** 区块链操作失败
**解决：** 私钥必须以"0x"开头，完整64位十六进制

### 问题3：模块导入失败
**症状：** "No module named 'xxx'"
**解决：** 确认PYTHONPATH=/app:/app/gnosis_predict_market_tool

### 问题4：健康检查失败
**症状：** 服务无法启动
**解决：** 检查所有必需环境变量是否正确设置