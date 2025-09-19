#!/bin/bash

# Example workflow for benchmarking multiple etcd cluster sizes
# This script demonstrates the complete process from setup to visualization

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

# Configuration
CLUSTER_SIZES=(1 3 5 7)
BENCHMARK_MODE="--quick"  # Use --quick for faster testing, remove for full benchmarks
RESULTS_DIR="benchmark_results"

print_info "Starting etcd cluster performance comparison workflow"
echo

# Create results directory
mkdir -p "$RESULTS_DIR"

# Check if cluster manager exists
if [[ ! -f "./cluster-manager.sh" ]]; then
    print_error "cluster-manager.sh not found. Please run this script from the project root."
    exit 1
fi

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    print_warning "Virtual environment not found. Setting up..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

print_info "Running benchmarks for cluster sizes: ${CLUSTER_SIZES[*]}"
echo

# Run benchmarks for each cluster size
for nodes in "${CLUSTER_SIZES[@]}"; do
    print_info "Testing $nodes-node cluster..."
    
    # Start cluster
    print_info "  Starting $nodes-node cluster..."
    if ./cluster-manager.sh start "$nodes" > /dev/null 2>&1; then
        print_success "  Cluster started successfully"
    else
        print_error "  Failed to start cluster"
        continue
    fi
    
    # Wait a moment for cluster to stabilize
    sleep 5
    
    # Check cluster health
    print_info "  Checking cluster health..."
    if ./cluster-manager.sh status > /dev/null 2>&1; then
        print_success "  Cluster is healthy"
    else
        print_warning "  Cluster health check failed, continuing anyway..."
    fi
    
    # Run benchmark
    print_info "  Running benchmark..."
    result_file="$RESULTS_DIR/results-${nodes}nodes.json"
    if python3 benchmark.py $BENCHMARK_MODE -o "$result_file" > /dev/null 2>&1; then
        print_success "  Benchmark completed: $result_file"
    else
        print_error "  Benchmark failed"
    fi
    
    # Stop cluster
    print_info "  Stopping cluster..."
    ./cluster-manager.sh stop > /dev/null 2>&1
    print_success "  Cluster stopped"
    
    echo
done

# Generate plots and analysis
print_info "Generating performance analysis..."

if python3 plot_results.py --pattern "$RESULTS_DIR/results-*nodes*.json" -o "$RESULTS_DIR/performance_comparison.png" 2>/dev/null; then
    print_success "Performance plots generated: $RESULTS_DIR/performance_comparison.png"
else
    print_warning "Plot generation failed, showing table only..."
    python3 plot_results.py --pattern "$RESULTS_DIR/results-*nodes*.json" --table-only
fi

echo
print_info "Workflow completed!"
print_info "Results saved in: $RESULTS_DIR/"

# Show summary
echo
print_info "Summary of collected data:"
for file in "$RESULTS_DIR"/results-*nodes*.json; do
    if [[ -f "$file" ]]; then
        nodes=$(basename "$file" | sed 's/results-\([0-9]*\)nodes.json/\1/')
        timestamp=$(python3 -c "import json; print(json.load(open('$file'))['timestamp'][:19])" 2>/dev/null || echo "Unknown")
        echo "  $nodes nodes: $file (collected at $timestamp)"
    fi
done

echo
print_success "To view detailed analysis, run:"
echo "  python3 plot_results.py --pattern \"$RESULTS_DIR/results-*nodes*.json\""

if [[ -f "$RESULTS_DIR/performance_comparison.png" ]]; then
    echo
    print_success "To view the performance comparison chart:"
    echo "  open $RESULTS_DIR/performance_comparison.png"
fi

echo
print_info "Workflow complete! 🎉"
