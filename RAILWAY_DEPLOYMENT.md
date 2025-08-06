# Railway 部署指南

本指南将帮助你将Supafund Market Creation Agent从Docker/AWS App Runner架构完全迁移到Railway平台，避免之前遇到的部署问题。

## 准备工作

### 1. 账号准备
- 注册Railway账号: https://railway.app/
- 连接你的GitHub账号

### 2. 代码准备验证
运行验证脚本确保部署准备就绪：
```bash
python validate_railway_deployment.py
```

应该显示所有检查通过：
- ✅ 配置文件完整（railway.toml, nixpacks.toml, Procfile等）
- ✅ 遗留Docker文件已清理
- ✅ 日志系统已更新为Railway
- ✅ Subprocess模块支持Railway环境检测
- ✅ Poetry环境正常
- ✅ 依赖文件无问题依赖

## 部署步骤

### 步骤1: 推送代码到GitHub
```bash
# 最终验证
python validate_railway_deployment.py

# 提交所有Railway相关的修改
git add .
git commit -m "feat: Railway deployment ready - comprehensive adaptation"
git push origin dockerit
```

### 步骤2: 在Railway创建项目
1. 登录 https://railway.app/
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的代码仓库
5. 选择 `dockerit` 分支

### 步骤3: 配置环境变量
在Railway项目面板的 **Variables** 标签页中添加以下环境变量：

**必需的环境变量：**
```bash
# Supabase配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-key

# 区块链配置
OMEN_PRIVATE_KEY=your-ethereum-private-key
GRAPH_API_KEY=your-graph-api-key

# 应用配置（Railway会自动设置这些）
OMEN_SCRIPT_PROJECT_PATH=gnosis_predict_market_tool
POETRY_PATH=poetry
RAILWAY_ENVIRONMENT=production

# 系统配置（Railway会自动设置）
PYTHONPATH=.
PYTHONUNBUFFERED=1
```

**可选的环境变量：**
```bash
# AI服务（如果需要市场解决功能）
XAI_API_KEY=your-grok-api-key
```

### 步骤4: 部署配置
Railway会自动检测项目类型并开始构建。确认配置：

1. **Build System**: Nixpacks (自动检测)
2. **Python Version**: 3.11 (在nixpacks.toml中指定)
3. **Dependencies**: 
   - Main app: `pip install -r requirements.txt`
   - Gnosis tools: `poetry install --only=main --no-dev`
4. **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT --workers 1`
5. **Health Check**: `/health` 端点带完整系统验证

### 步骤5: 监控部署
1. 在Railway面板查看构建日志
2. 等待部署完成（通常需要3-5分钟）
3. 获取分配的域名（如: `https://your-app-name.up.railway.app`）

## 验证部署

### 测试健康检查
```bash
curl https://your-app-name.up.railway.app/health
```

应该返回：
```json
{
  "status": "healthy",
  "timestamp": "2024-xx-xxTxx:xx:xx.xxxZ",
  "service": "Supafund Market Creation Agent",
  "platform": "railway",
  "python_version": "3.11.x",
  "environment": {
    "railway": {
      "is_railway": true,
      "environment": "production",
      "service_name": "supafund-agent",
      "host": "0.0.0.0",
      "port": "xxxx"
    }
  },
  "subprocess_creator": "available",
  "poetry": "available: Poetry (version x.x.x)"
}
```

### 测试API文档
访问: `https://your-app-name.up.railway.app/docs`

## 常见问题排查

### 1. 构建失败
**症状**: Poetry安装超时或依赖冲突
**解决方案**: 
- 检查requirements.txt中是否有中国PyPI镜像源（已移除）
- 验证nixpacks.toml中的Python版本设置
- 查看构建日志中的具体错误信息

### 2. 启动失败
**症状**: 应用启动但无法访问
**解决方案**:
- 确保使用动态 `$PORT` 环境变量
- 检查host绑定到 `0.0.0.0`
- 验证健康检查端点 `/health` 是否响应

### 3. Subprocess调用失败
**症状**: 市场创建或投注失败
**解决方案**:
- 检查Poetry是否在gnosis_predict_market_tool中正确安装
- 验证环境检测逻辑是否正确识别Railway环境
- 查看日志中的subprocess执行输出

### 4. 环境变量问题
**症状**: 配置相关错误
**解决方案**: 
- 检查Railway面板Variables标签页中的所有必需变量
- 验证private key和API key格式正确
- 确保没有包含额外的空格或换行符

### 5. 数据库连接失败
**症状**: Supabase相关操作失败
**解决方案**:
- 验证 `SUPABASE_URL` 和 `SUPABASE_KEY`
- 检查Supabase项目是否处于活跃状态
- 测试数据库连接和表结构

## Railway vs 其他平台对比

| 特性 | Railway | Docker (本地/AWS) | Vercel |
|------|---------|-------------------|--------|
| 环境检测 | `RAILWAY_ENVIRONMENT` | `/app/` 路径检测 | `VERCEL` |
| 端口配置 | 动态 `$PORT` | 固定端口 | 固定端口 |
| 依赖管理 | Poetry + pip | Docker layers | npm/pip |
| 日志输出 | stdout/stderr面板 | Docker logs | Vercel日志 |
| 构建系统 | Nixpacks | Dockerfile | Vercel Build |
| 部署方式 | Git推送自动部署 | Docker构建部署 | Git推送部署 |
| 长运行任务 | ✅ 支持 | ✅ 支持 | ❌ 15s限制 |
| Subprocess调用 | ✅ 完全支持 | ✅ 完全支持 | ❌ 受限 |

## 成本预估

- **Hobby Plan**: $5/月 - 适合开发和轻量级生产
- **Pro Plan**: $20/月 - 适合生产环境，更多资源

## 维护建议

### 日常监控
1. **监控**: 定期检查Railway面板的Metrics和Deployments
2. **日志**: 使用Railway内置日志查看器，注意emoji标识的操作状态
3. **健康检查**: 定期访问 `/health` 端点确认系统状态
4. **性能**: 监控响应时间和subprocess调用成功率

### 更新和维护
1. **代码更新**: Git推送会自动触发重新部署
2. **依赖更新**: 更新requirements.txt和pyproject.toml后重新部署
3. **环境变量**: 通过Railway面板安全地更新配置
4. **备份**: 定期备份环境变量配置和数据库

### 故障排除
1. **查看日志**: Railway面板的Logs标签页
2. **重启服务**: Railway面板的Deployments页面
3. **回滚**: 使用之前的成功部署版本
4. **本地调试**: 运行 `python start_railway.py` 模拟Railway环境

## 生产环境注意事项

1. **安全**: 确保私钥等敏感信息只通过环境变量传递
2. **监控**: 设置uptime监控和告警
3. **域名**: 考虑绑定自定义域名
4. **资源**: 根据使用量调整Railway计划
5. **日志**: 定期导出重要日志数据

## 回滚和应急方案

### 自动回滚
1. Railway面板 → Deployments → 选择之前成功的部署版本
2. 点击 "Redeploy" 即可快速回滚

### 手动修复
1. 本地修复代码问题
2. 运行 `python validate_railway_deployment.py` 确保修复有效
3. 推送修复代码: `git push origin dockerit`
4. Railway自动触发重新部署

### 应急处理
1. **服务暂停**: Railway面板 → Settings → 暂时停止服务
2. **快速诊断**: 检查最近的部署日志和环境变量
3. **联系支持**: Railway Discord社区或GitHub Issues

### 数据恢复
1. **数据库**: Supabase有自动备份，可通过其面板恢复
2. **环境配置**: 建议定期导出环境变量配置到安全位置
3. **代码版本**: Git历史记录提供完整的版本控制

## 支持

遇到问题可以：
1. 查看Railway文档: https://docs.railway.app/
2. 检查项目的GitHub Issues
3. Railway Discord社区支持
4. 运行本地验证脚本: `python validate_railway_deployment.py`

---

💡 **重要提示**: 本指南基于彻底的Docker到Railway迁移，包括完整的环境检测、日志系统和subprocess调用适配，确保避免之前部署中遇到的所有问题。