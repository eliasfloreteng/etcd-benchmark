#!/bin/bash

# etcd Cluster Deployment Setup Script
# Sets up the environment and dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS or Linux
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    print_info "Checking dependencies..."
    
    if ! command -v docker >/dev/null 2>&1; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo
        echo "Please install the missing dependencies:"
        
        local os=$(detect_os)
        if [[ "$os" == "macos" ]]; then
            echo "  brew install docker docker-compose python3"
        elif [[ "$os" == "linux" ]]; then
            echo "  # Ubuntu/Debian:"
            echo "  sudo apt-get update"
            echo "  sudo apt-get install docker.io docker-compose python3 python3-pip"
            echo
            echo "  # CentOS/RHEL:"
            echo "  sudo yum install docker docker-compose python3 python3-pip"
        fi
        
        return 1
    fi
    
    print_success "All dependencies found"
    return 0
}

# Setup Python virtual environment
setup_venv() {
    print_info "Setting up Python virtual environment..."
    
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate and install requirements
    source venv/bin/activate
    
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        pip install PyYAML
        print_success "PyYAML installed"
    fi
}

# Make scripts executable
setup_permissions() {
    print_info "Setting up script permissions..."
    
    chmod +x cluster-manager.sh
    chmod +x generate-cluster.py
    chmod +x benchmark.py
    
    print_success "Script permissions set"
}

# Test basic functionality
test_setup() {
    print_info "Testing setup..."
    
    # Test cluster generation
    source venv/bin/activate
    
    if python3 generate-cluster.py 3 -o test-cluster.yml >/dev/null 2>&1; then
        print_success "Cluster generation test passed"
        rm -f test-cluster.yml
    else
        print_error "Cluster generation test failed"
        return 1
    fi
    
    # Test cluster manager help
    if ./cluster-manager.sh --help >/dev/null 2>&1; then
        print_success "Cluster manager test passed"
    else
        print_error "Cluster manager test failed"
        return 1
    fi
}

# Show usage information
show_usage() {
    cat << EOF
etcd Cluster Deployment Setup

This script sets up the environment for running etcd clusters with Docker.

Usage: $0 [options]

Options:
    --check-only    Only check dependencies, don't install anything
    --help          Show this help message

After setup, you can use:
    ./cluster-manager.sh start 3    # Start 3-node cluster
    ./cluster-manager.sh status     # Check cluster status
    ./cluster-manager.sh benchmark  # Run performance tests

EOF
}

# Main function
main() {
    local check_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --check-only)
                check_only=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "etcd Cluster Deployment Setup"
    echo "============================="
    echo
    
    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi
    
    if [[ "$check_only" == "true" ]]; then
        print_success "Dependency check completed successfully"
        exit 0
    fi
    
    # Setup environment
    setup_venv
    setup_permissions
    
    # Test setup
    if test_setup; then
        echo
        print_success "Setup completed successfully!"
        echo
        echo "You can now use the cluster manager:"
        echo "  ./cluster-manager.sh start 3    # Start 3-node cluster"
        echo "  ./cluster-manager.sh status     # Check cluster status"
        echo "  ./cluster-manager.sh benchmark  # Run performance tests"
        echo
        echo "For more information, see README.md or run:"
        echo "  ./cluster-manager.sh --help"
    else
        print_error "Setup test failed"
        exit 1
    fi
}

# Run main function
main "$@"
