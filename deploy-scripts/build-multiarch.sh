#!/bin/bash

# Supafund Market Agent - Multi-Architecture Docker Build and Push Script
# 用于构建 x86_64 架构的 Docker 镜像并推送到 AWS ECR

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量 (根据您的 ECR 仓库信息)
AWS_REGION="us-west-2"
REPOSITORY_NAME="supafund/market-creation-agent"
IMAGE_TAG="${1:-latest}"
ACCOUNT_ID="857736875791"

echo -e "${BLUE}🚀 Supafund Market Agent - 多架构构建脚本${NC}"
echo "======================================================"

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI 未安装。请先安装 AWS CLI。${NC}"
    exit 1
fi

# 检查是否已配置 AWS 凭证
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS 凭证未配置。请先运行 'aws configure'。${NC}"
    exit 1
fi

# ECR 配置 (使用您提供的仓库信息)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URI}/${REPOSITORY_NAME}:${IMAGE_TAG}"

echo -e "${BLUE}📋 构建信息:${NC}"
echo "  AWS 账户 ID: ${ACCOUNT_ID}"
echo "  区域: ${AWS_REGION}"
echo "  仓库: ${REPOSITORY_NAME}"
echo "  镜像标签: ${IMAGE_TAG}"
echo "  完整镜像名: ${FULL_IMAGE_NAME}"
echo "  目标架构: linux/amd64"
echo

# ECR 仓库已存在，跳过创建步骤
echo -e "${GREEN}✅ 使用现有 ECR 仓库: ${REPOSITORY_NAME}${NC}"

# Docker 登录到 ECR
echo -e "${YELLOW}🔐 登录到 ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
echo -e "${GREEN}✅ ECR 登录成功${NC}"

# 创建新的 buildx builder (如果不存在)
echo -e "${YELLOW}🏗️  设置 Docker buildx...${NC}"
if ! docker buildx ls | grep -q "multiarch-builder"; then
    docker buildx create --name multiarch-builder --driver docker-container --bootstrap
    echo -e "${GREEN}✅ 创建了新的 buildx builder${NC}"
else
    echo -e "${GREEN}✅ 使用现有 buildx builder${NC}"
fi

# 使用 buildx builder
docker buildx use multiarch-builder

# 构建并推送 x86_64 架构的镜像
echo -e "${YELLOW}🏗️  构建并推送 x86_64 镜像到 ECR...${NC}"
docker buildx build \
    --platform linux/amd64 \
    --tag ${FULL_IMAGE_NAME} \
    --push \
    .

echo -e "${GREEN}✅ 多架构镜像构建和推送成功${NC}"

# 显示结果
echo
echo -e "${GREEN}🎉 构建和推送完成!${NC}"
echo "======================================================"
echo -e "${BLUE}📋 镜像信息:${NC}"
echo "  镜像 URI: ${FULL_IMAGE_NAME}"
echo "  架构: linux/amd64 (兼容 AWS App Runner)"
echo
echo -e "${BLUE}📝 下一步:${NC}"
echo "1. App Runner 会自动检测新镜像，或者手动更新:"
echo "   aws apprunner start-deployment --service-arn <your-service-arn>"
echo
echo "2. 检查部署状态:"
echo "   aws apprunner describe-service --service-arn <your-service-arn>"
echo
echo "3. 测试服务:"
echo "   curl https://your-service-url.us-west-2.awsapprunner.com/health"