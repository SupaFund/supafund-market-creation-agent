#!/bin/bash

echo "🚀 Supafund Market Creation Agent - AWS App Runner 部署脚本"
echo "=================================================="

# 运行部署前检查
echo "1️⃣ 运行部署前检查..."
if ! ./pre-deploy-check.sh; then
    echo "❌ 部署前检查失败，请修复问题后重试"
    exit 1
fi

echo ""
echo "2️⃣ 检查Git状态..."
if ! git status > /dev/null 2>&1; then
    echo "❌ 当前目录不是Git仓库"
    exit 1
fi

# 检查是否有未提交的更改
if ! git diff-index --quiet HEAD --; then
    echo "⚠️ 检测到未提交的更改"
    echo "是否要提交并推送到GitHub? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "正在添加文件..."
        git add .
        echo "请输入提交信息:"
        read -r commit_message
        git commit -m "$commit_message"
        echo "推送到GitHub..."
        git push origin main
    else
        echo "⚠️ 请先提交更改后再部署"
        exit 1
    fi
else
    echo "✅ Git状态正常"
    echo "推送最新代码到GitHub..."
    git push origin main
fi

echo ""
echo "3️⃣ 部署准备完成！"
echo ""
echo "下一步请在AWS控制台完成以下操作："
echo ""
echo "🌐 1. 打开AWS App Runner控制台:"
echo "   https://console.aws.amazon.com/apprunner/"
echo ""
echo "➕ 2. 点击 'Create service'"
echo ""
echo "📋 3. 配置信息："
echo "   - Source: GitHub repository"
echo "   - Repository: $(git remote get-url origin)"
echo "   - Branch: main"
echo "   - Configuration file: Use apprunner.yaml"
echo ""
echo "🔧 4. 添加环境变量（参考 ENV_CONFIG_GUIDE.md）："
echo "   - SUPABASE_URL"
echo "   - SUPABASE_KEY"  
echo "   - OMEN_PRIVATE_KEY"
echo "   - GRAPH_API_KEY"
echo "   - PYTHONPATH=/app:/app/gnosis_predict_market_tool"
echo ""
echo "⏱️ 5. 等待部署完成（约5-10分钟）"
echo ""
echo "🏥 6. 测试健康检查："
echo "   curl https://your-app-url.region.awsapprunner.com/health"
echo ""
echo "📖 详细说明请参考："
echo "   - AWS_DEPLOYMENT_GUIDE.md"
echo "   - ENV_CONFIG_GUIDE.md"
echo ""
echo "🎉 祝部署成功！"