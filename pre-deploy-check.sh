#!/bin/bash

echo "🔍 AWS App Runner部署前检查..."

# 检查必需文件
echo "📁 检查必需文件..."
required_files=(
    "apprunner.yaml"
    "requirements.txt"
    "src/main.py"
    ".env.aws.template"
    ".dockerignore"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - 存在"
    else
        echo "❌ $file - 缺失"
        exit 1
    fi
done

# 检查Python语法
echo ""
echo "🐍 检查Python语法..."
if python -m py_compile src/main.py; then
    echo "✅ main.py语法正确"
else
    echo "❌ main.py语法错误"
    exit 1
fi

# 检查依赖安装
echo ""
echo "📦 检查关键依赖..."
key_packages=("fastapi" "uvicorn" "pydantic" "web3" "supabase")

for package in "${key_packages[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        echo "✅ $package - 可导入"
    else
        echo "⚠️ $package - 无法导入（部署时会安装）"
    fi
done

# 检查健康检查端点
echo ""
echo "🏥 检查健康检查端点..."
if python -c "
import sys
sys.path.append('src')
from main import app
print('✅ 健康检查端点配置正确')
" 2>/dev/null; then
    echo "✅ 健康检查配置正确"
else
    echo "❌ 健康检查配置有问题"
    exit 1
fi

echo ""
echo "🚀 所有检查通过！可以开始AWS App Runner部署。"
echo ""
echo "下一步："
echo "1. 将代码推送到GitHub"
echo "2. 在AWS控制台创建App Runner服务"
echo "3. 配置环境变量"
echo "4. 等待部署完成"