#!/bin/bash
# 安裝向量檢索依賴
# 處理 PyTorch 在不同平台上的安裝問題

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 取得腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    print_error "虛擬環境不存在，請先執行: make venv"
    exit 1
fi

# 啟動虛擬環境
source .venv/bin/activate

print_header "安裝向量檢索依賴"
echo ""

# 檢測作業系統和架構
OS=$(uname -s)
ARCH=$(uname -m)

print_info "檢測到系統: $OS $ARCH"
echo ""

# 檢查 Python 版本
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_info "Python 版本: $PYTHON_VERSION"

# 檢查 Python 版本是否支援
if [ "$OS" = "Darwin" ] && [ "$ARCH" = "x86_64" ]; then
    # macOS Intel 只支援到 Python 3.12
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -gt 12 ]; then
        print_error "macOS Intel 上的 PyTorch 只支援 Python 3.8-3.12"
        print_error "您的 Python 版本: $PYTHON_VERSION"
        echo ""
        print_info "解決方案："
        echo "  1. 使用 Python 3.12 或更低版本重新建立虛擬環境"
        echo "  2. 或使用 Conda 安裝 PyTorch："
        echo "     conda install pytorch torchvision torchaudio -c pytorch"
        exit 1
    fi
fi

echo ""

# 檢查是否已安裝 PyTorch
if python -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
    print_success "PyTorch 已安裝: $TORCH_VERSION"
else
    print_info "正在安裝 PyTorch..."
    echo ""
    
    # 根據平台選擇安裝方式
    if [ "$OS" = "Darwin" ]; then
        # macOS
        if [ "$ARCH" = "arm64" ]; then
            # Apple Silicon - 使用預設 PyPI
            print_info "檢測到 Apple Silicon，安裝 PyTorch..."
            uv pip install torch torchvision torchaudio
        else
            # Intel Mac - 使用 Conda（PyPI 已不支援）
            print_warning "macOS Intel 需要使用 Conda 安裝 PyTorch"
            echo ""

            # 檢查是否有 conda
            if command -v conda &> /dev/null; then
                print_info "檢測到 Conda，使用 Conda 安裝 PyTorch..."
                conda install -y pytorch torchvision torchaudio -c pytorch
            else
                print_error "未檢測到 Conda"
                echo ""
                print_info "請選擇以下方案之一："
                echo ""
                echo "方案 A：安裝 Miniconda 並使用 Conda 安裝 PyTorch"
                echo "  1. 下載 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
                echo "  2. 安裝後執行: conda install pytorch torchvision torchaudio -c pytorch"
                echo ""
                echo "方案 B：使用 Apple Silicon 版本（透過 Rosetta 2）"
                echo "  1. 安裝 Rosetta 2: softwareupdate --install-rosetta"
                echo "  2. 使用 ARM64 版本的 Python 重新建立虛擬環境"
                echo ""
                echo "方案 C：不使用向量檢索功能（只使用 BM25）"
                echo "  跳過此步驟，系統仍可正常運作"
                exit 1
            fi
        fi
    elif [ "$OS" = "Linux" ]; then
        # Linux - 使用 CPU 版本
        print_info "檢測到 Linux，安裝 PyTorch (CPU)..."
        uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    else
        # Windows or other - 使用 CPU 版本
        print_info "安裝 PyTorch (CPU)..."
        uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
    
    print_success "PyTorch 安裝完成"
fi

echo ""

# 安裝其他向量檢索依賴
print_info "正在安裝 FAISS 和 sentence-transformers..."
echo ""

# NumPy 2.x 現已支援 PyTorch/FAISS (2025+)
uv pip install "numpy>=1.26.0"
uv pip install faiss-cpu>=1.9.0
uv pip install sentence-transformers>=3.3.0

echo ""
print_success "所有向量檢索依賴安裝完成！"
echo ""

# 驗證安裝
print_info "驗證安裝..."
echo ""

if python -c "import torch; import faiss; import sentence_transformers" 2>/dev/null; then
    print_success "所有依賴驗證通過"
    echo ""
    
    # 顯示版本資訊
    print_info "已安裝的版本："
    python -c "
import torch
import faiss
import sentence_transformers
print(f'  - PyTorch: {torch.__version__}')
print(f'  - FAISS: {faiss.__version__}')
print(f'  - sentence-transformers: {sentence_transformers.__version__}')
"
else
    print_error "依賴驗證失敗"
    exit 1
fi

echo ""
print_success "向量檢索功能已啟用！"
echo ""

print_info "下一步："
echo "  1. 為現有專案建立向量索引："
echo "     python retrieval/build_vector_index.py <project_name>"
echo ""
echo "  2. 或使用管理工具："
echo "     bash scripts/manage.sh rebuild <project_name>"
echo ""

