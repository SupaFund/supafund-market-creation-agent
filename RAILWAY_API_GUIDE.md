# Railway 异步区块链 API 调用指南

**基础URL**: `https://supafund-market-creation-agent-production.up.railway.app`

## 🚀 异步区块链端点

### 1. 创建预测市场 (异步)

**端点**: `POST /async/create-market`

**请求示例**:
```bash
curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/create-market" \
-H "Content-Type: application/json" \
-d '{
  "application_id": "your-application-id-here"
}'
```

**响应**:
```json
{
  "status": "accepted",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Market creation task submitted successfully",
  "estimated_completion": "2-5 minutes"
}
```

### 2. 下注 (异步)

**端点**: `POST /async/bet`

**请求示例**:
```bash
curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/bet" \
-H "Content-Type: application/json" \
-d '{
  "market_id": "0x123...",
  "amount_usd": 10.0,
  "outcome": "Yes",
  "from_private_key": "your-private-key"
}'
```

### 3. 提交市场答案 (异步)

**端点**: `POST /async/submit-answer`

**请求示例**:
```bash
curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/submit-answer" \
-H "Content-Type: application/json" \
-d '{
  "market_id": "0x123...",
  "outcome": "Yes",
  "confidence": 0.85,
  "reasoning": "Based on research data...",
  "from_private_key": "your-private-key"
}'
```

### 4. AI研究并提交答案 (异步)

**端点**: `POST /async/research-and-submit`

**请求示例**:
```bash
curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/research-and-submit" \
-H "Content-Type: application/json" \
-d '{
  "market_id": "0x123...",
  "from_private_key": "your-private-key"
}'
```

### 5. 最终化市场解析 (异步)

**端点**: `POST /async/finalize-resolution`

**请求示例**:
```bash
curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/finalize-resolution" \
-H "Content-Type: application/json" \
-d '{
  "market_id": "0x123...",
  "from_private_key": "your-private-key"
}'
```

## 📊 任务状态管理

### 查询任务状态

**端点**: `GET /task-status/{task_id}`

**请求示例**:
```bash
curl "https://supafund-market-creation-agent-production.up.railway.app/task-status/123e4567-e89b-12d3-a456-426614174000"
```

**可能的响应状态**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",     // pending | processing | completed | failed | retrying
  "progress": "Task queued and waiting for processing",
  "created_at": "2025-08-11T18:25:24.331Z",
  "updated_at": "2025-08-11T18:25:24.331Z",
  "retry_count": 0,
  "max_retries": 3
}
```

**成功完成示例**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": "Market created successfully",
  "result": {
    "market_id": "0xD2C37a337b655001aBd18F2aeeeEbf266fa7eC71",
    "question_id": "0xc498bde8867c4fd744f4fc0dfe9fbfb3a728948de901e4cf2d2e6c23bfcb8636",
    "question": "Will project 'Example' be approved?",
    "success": true
  },
  "created_at": "2025-08-11T18:25:24.331Z",
  "updated_at": "2025-08-11T18:28:42.156Z",
  "retry_count": 0,
  "max_retries": 3
}
```

### 查看最近任务

**端点**: `GET /tasks/recent`

**请求示例**:
```bash
curl "https://supafund-market-creation-agent-production.up.railway.app/tasks/recent"
```

### 查看队列状态

**端点**: `GET /tasks/queue-status`

**请求示例**:
```bash
curl "https://supafund-market-creation-agent-production.up.railway.app/tasks/queue-status"
```

**响应示例**:
```json
{
  "queue_status": {
    "pending_tasks": 0,
    "processing_tasks": 1,
    "max_concurrent_tasks": 3,
    "workers_started": true
  },
  "recent_performance": {
    "completed_last_6h": 5,
    "failed_last_6h": 1,
    "success_rate": 83.33
  }
}
```

## 🔄 使用工作流

### 典型的异步调用流程:

1. **提交任务**:
   ```bash
   # 步骤1: 提交市场创建任务
   TASK_RESPONSE=$(curl -X POST "https://supafund-market-creation-agent-production.up.railway.app/async/create-market" \
   -H "Content-Type: application/json" \
   -d '{"application_id": "your-app-id"}')
   
   # 提取task_id
   TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')
   ```

2. **轮询状态**:
   ```bash
   # 步骤2: 轮询任务状态直到完成
   while true; do
     STATUS=$(curl -s "https://supafund-market-creation-agent-production.up.railway.app/task-status/$TASK_ID" | jq -r '.status')
     
     if [ "$STATUS" = "completed" ]; then
       echo "任务完成!"
       break
     elif [ "$STATUS" = "failed" ]; then
       echo "任务失败!"
       break
     fi
     
     echo "当前状态: $STATUS，等待5秒..."
     sleep 5
   done
   ```

### JavaScript 示例:

```javascript
// 异步市场创建
async function createMarketAsync(applicationId) {
  // 1. 提交任务
  const response = await fetch('/async/create-market', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ application_id: applicationId })
  });
  
  const { task_id } = await response.json();
  
  // 2. 轮询状态
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      const statusResponse = await fetch(`/task-status/${task_id}`);
      const status = await statusResponse.json();
      
      if (status.status === 'completed') {
        resolve(status.result);
      } else if (status.status === 'failed') {
        reject(new Error(status.error || 'Task failed'));
      } else {
        // 继续轮询
        setTimeout(checkStatus, 5000);
      }
    };
    
    checkStatus();
  });
}

// 使用示例
createMarketAsync('your-application-id')
  .then(result => console.log('市场创建成功:', result))
  .catch(error => console.error('市场创建失败:', error));
```

## 🏥 健康检查和调试

### 健康检查端点:
```bash
curl "https://supafund-market-creation-agent-production.up.railway.app/health"
```

### 查看API文档:
访问: `https://supafund-market-creation-agent-production.up.railway.app/docs`

## ⚠️ 重要说明

1. **异步处理**: 所有 `/async/*` 端点都会立即返回task_id，实际处理在后台进行
2. **处理时间**: 区块链操作通常需要 2-5 分钟完成
3. **自动重试**: 失败的任务会自动重试最多3次
4. **并发限制**: 同时最多处理3个区块链任务
5. **状态轮询**: 建议每5秒查询一次任务状态

## 🐛 故障排除

如果遇到404错误:
1. 检查URL是否正确
2. 确认使用了正确的HTTP方法 (POST/GET)
3. 查看 `/health` 端点确认服务正常运行
4. 查看 `/docs` 端点确认可用的路由

如果任务长时间处于 `pending` 状态:
1. 检查 `/tasks/queue-status` 查看队列状态
2. 等待当前处理中的任务完成
3. 任务会按照提交顺序依次处理