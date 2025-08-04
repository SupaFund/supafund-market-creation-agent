#!/bin/bash

# Supafund Market Agent - App Runner Service Creation Script
# 用于创建 AWS App Runner 服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量 (根据您的 ECR 仓库信息)
SERVICE_NAME="supafund-market-agent"
AWS_REGION="us-west-2"
IMAGE_URI="${1:-857736875791.dkr.ecr.us-west-2.amazonaws.com/supafund/market-creation-agent:latest}"

echo -e "${BLUE}🚀 Supafund Market Agent - App Runner 服务创建脚本${NC}"
echo "=========================================================="

# 显示将要使用的镜像 URI
echo -e "${BLUE}📋 将使用镜像: ${IMAGE_URI}${NC}"
if [ "$1" != "$IMAGE_URI" ] && [ -n "$1" ]; then
    IMAGE_URI="$1"
    echo -e "${YELLOW}📝 使用命令行提供的镜像: ${IMAGE_URI}${NC}"
fi

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI 未安装。请先安装 AWS CLI。${NC}"
    exit 1
fi

# 检查是否已配置 AWS 凭证
echo -e "${YELLOW}🔍 检查 AWS 凭证...${NC}"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS 凭证未配置。请先运行 'aws configure'。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ AWS 凭证验证成功${NC}"

echo -e "${BLUE}📋 服务信息:${NC}"
echo "  服务名称: ${SERVICE_NAME}"
echo "  区域: ${AWS_REGION}"
echo "  镜像 URI: ${IMAGE_URI}"
echo

# 检查环境变量
echo -e "${YELLOW}⚠️  重要提醒: 请确保以下环境变量已设置:${NC}"
echo "  - SUPABASE_URL"
echo "  - SUPABASE_KEY"
echo "  - OMEN_PRIVATE_KEY"
echo "  - GRAPH_API_KEY"
echo
read -p "是否继续创建服务? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

# 创建服务配置
echo -e "${YELLOW}📝 创建服务配置...${NC}"
cat > /tmp/apprunner-service-config.json << EOF
{
  "ServiceName": "${SERVICE_NAME}",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "${IMAGE_URI}",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PYTHONPATH": "/app:/app/gnosis_predict_market_tool",
          "PYTHONUNBUFFERED": "1",
          "WEB_CONCURRENCY": "1",
          "OMEN_SCRIPT_PROJECT_PATH": "/app/gnosis_predict_market_tool",
          "POETRY_PATH": "poetry"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": false
  },
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 20,
    "Timeout": 5,
    "HealthyThreshold": 2,
    "UnhealthyThreshold": 5
  }
}
EOF

# 创建 App Runner 服务
echo -e "${YELLOW}🏗️  创建 App Runner 服务...${NC}"
SERVICE_ARN=$(aws apprunner create-service \
    --cli-input-json file:///tmp/apprunner-service-config.json \
    --region ${AWS_REGION} \
    --query 'Service.ServiceArn' \
    --output text)

echo -e "${GREEN}✅ App Runner 服务创建成功${NC}"
echo "服务 ARN: ${SERVICE_ARN}"

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动完成...${NC}"
echo "这可能需要几分钟时间..."

while true; do
    STATUS=$(aws apprunner describe-service \
        --service-arn ${SERVICE_ARN} \
        --region ${AWS_REGION} \
        --query 'Service.Status' \
        --output text)
    
    echo -e "${BLUE}当前状态: ${STATUS}${NC}"
    
    if [ "$STATUS" = "RUNNING" ]; then
        break
    elif [ "$STATUS" = "CREATE_FAILED" ] || [ "$STATUS" = "OPERATION_IN_PROGRESS" ]; then
        echo -e "${RED}❌ 服务创建失败或仍在进行中${NC}"
        echo "请检查 App Runner 控制台获取详细信息"
        exit 1
    fi
    
    echo "等待中..."
    sleep 30
done

# 获取服务 URL
SERVICE_URL=$(aws apprunner describe-service \
    --service-arn ${SERVICE_ARN} \
    --region ${AWS_REGION} \
    --query 'Service.ServiceUrl' \
    --output text)

echo
echo -e "${GREEN}🎉 部署完成!${NC}"
echo "=========================================================="
echo -e "${BLUE}📋 服务信息:${NC}"
echo "  服务名称: ${SERVICE_NAME}"
echo "  服务 ARN: ${SERVICE_ARN}"
echo "  服务 URL: https://${SERVICE_URL}"
echo
echo -e "${BLUE}📝 下一步:${NC}"
echo "1. 测试服务健康状态:"
echo "   curl https://${SERVICE_URL}/health"
echo
echo "2. 查看 API 文档:"
echo "   https://${SERVICE_URL}/docs"
echo
echo "3. 设置环境变量 (在 AWS 控制台中):"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_KEY"
echo "   - OMEN_PRIVATE_KEY"
echo "   - GRAPH_API_KEY"
echo
echo "4. 监控服务:"
echo "   aws apprunner describe-service --service-arn ${SERVICE_ARN}"
echo
echo -e "${YELLOW}⚠️  重要: 请记住设置敏感环境变量!${NC}"

# 清理临时文件
rm -f /tmp/apprunner-service-config.json