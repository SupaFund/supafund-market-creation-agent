# 🚀 AWS App Runner 部署指南

## 前提条件

1. **AWS 账户** - 确保你有AWS账户和适当的权限
2. **GitHub 仓库** - 代码已推送到GitHub
3. **环境变量** - 准备好所有必需的环境变量

## 步骤1: 准备环境变量

从 `.env.aws.template` 复制并准备以下环境变量：

```bash
# 必需的环境变量
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
OMEN_PRIVATE_KEY=0xYourPrivateKey
GRAPH_API_KEY=your_thegraph_api_key

# 系统环境变量（AWS App Runner会自动设置）
PYTHONPATH=/app:/app/gnosis_predict_market_tool
PYTHONUNBUFFERED=1
PORT=8000
```

## 步骤2: 在AWS控制台创建App Runner服务

### 2.1 登录AWS控制台
1. 登录 [AWS Console](https://console.aws.amazon.com/)
2. 搜索并选择 "App Runner"
3. 点击 "Create service"

### 2.2 配置源代码
1. **Source type**: 选择 "Source code repository"
2. **Repository**: 
   - 选择 "GitHub"
   - 连接你的GitHub账户（如果首次使用）
   - 选择你的仓库：`supafund-market-creation-agent`
   - 选择分支：`main`
3. **Deployment trigger**: 选择 "Automatic" (推荐)

### 2.3 配置构建设置
1. **Configuration file**: 选择 "Use a configuration file"
2. 确认 `apprunner.yaml` 文件存在于仓库根目录

### 2.4 配置服务设置
1. **Service name**: `supafund-market-agent`
2. **Virtual CPU**: 1 vCPU (可根据需要调整)
3. **Memory**: 2 GB (推荐)
4. **Environment variables**: 添加上面准备的环境变量

### 2.5 配置网络和安全
1. **Auto scaling**: 
   - Min instances: 1
   - Max instances: 10
2. **Health check**: 
   - Path: `/health`
   - Interval: 30 seconds
   - Timeout: 5 seconds
   - Healthy threshold: 2
   - Unhealthy threshold: 5

### 2.6 审查和创建
1. 审查所有设置
2. 点击 "Create & deploy"
3. 等待服务部署完成（通常需要5-10分钟）

## 步骤3: 验证部署

### 3.1 检查服务状态
1. 在App Runner控制台查看服务状态
2. 等待状态变为 "Running"

### 3.2 测试健康检查
访问健康检查端点：
```bash
curl https://your-app-url.region.awsapprunner.com/health
```

预期响应：
```json
{
  "status": "healthy",
  "timestamp": "2025-01-31T...",
  "service": "Supafund Market Creation Agent",
  "version": "1.0.0",
  "blockchain_module": "available"
}
```

### 3.3 测试API端点
```bash
# 测试根端点
curl https://your-app-url.region.awsapprunner.com/

# 查看API文档
https://your-app-url.region.awsapprunner.com/docs
```

## 步骤4: 配置域名（可选）

1. 在App Runner服务页面，点击 "Custom domains"
2. 添加你的域名
3. 按照指示配置DNS记录

## 故障排除

### 常见问题

**1. 构建失败**
- 检查 `requirements.txt` 是否正确
- 查看构建日志，确认所有依赖都能安装

**2. 服务启动失败**
- 检查健康检查端点 `/health` 是否正常工作
- 确认环境变量设置正确
- 查看应用日志

**3. 区块链功能不工作**
- 确认 `OMEN_PRIVATE_KEY` 和 `GRAPH_API_KEY` 设置正确
- 检查私钥格式（应以0x开头）

### 查看日志
1. 在App Runner控制台，选择你的服务
2. 点击 "Logs" 标签页
3. 查看构建日志和应用日志

## 成本估算

AWS App Runner按使用量计费：
- **vCPU**: $0.064/小时/vCPU
- **内存**: $0.007/小时/GB
- **请求**: $0.0000025/请求

典型使用场景（1 vCPU, 2GB内存）：
- 基础成本：约 $50-100/月
- 根据实际流量调整

## 后续步骤

1. **监控设置**: 配置CloudWatch告警
2. **CI/CD优化**: 设置GitHub Actions自动测试
3. **安全配置**: 配置WAF和其他安全措施
4. **性能优化**: 根据使用情况调整资源配置

## 支持

如果遇到问题，请检查：
1. AWS App Runner [官方文档](https://docs.aws.amazon.com/apprunner/)
2. 应用日志和构建日志
3. 健康检查端点响应