#!/bin/bash

# etcd Cluster Manager
# Provides easy commands to manage etcd clusters of different sizes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_COMPOSE_FILE="docker-compose-generated.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
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

# Show usage information
show_usage() {
    cat << EOF
etcd Cluster Manager

Usage: $0 <command> [options]

Commands:
    generate <nodes>        Generate cluster configuration for N nodes
    start <nodes>          Generate and start cluster with N nodes
    stop                   Stop the current cluster
    restart <nodes>        Restart cluster with N nodes
    status                 Show cluster status
    clean                  Stop cluster and remove all data
    test                   Test cluster connectivity
    benchmark              Run performance benchmark
    logs [node]            Show logs (all nodes or specific node)
    shell <node>           Open shell in specific node container

Options:
    -f, --file <file>      Use specific compose file (default: $DEFAULT_COMPOSE_FILE)
    -p, --port <port>      Base client port (default: 2379)
    --peer-port <port>     Base peer port (default: 2380)
    -h, --help             Show this help message

Examples:
    $0 start 3             # Start 3-node cluster
    $0 start 5 -p 3379     # Start 5-node cluster on ports 3379+
    $0 status              # Check cluster health
    $0 benchmark           # Run performance test
    $0 clean               # Stop and remove all data

EOF
}

# Generate cluster configuration
generate_cluster() {
    local nodes=$1
    local compose_file=$2
    local base_port=$3
    local peer_port=$4
    
    print_info "Generating $nodes-node etcd cluster configuration..."
    
    local cmd="python3 generate-cluster.py $nodes -o $compose_file"
    
    if [[ -n "$base_port" ]]; then
        cmd="$cmd --base-client-port $base_port"
    fi
    
    if [[ -n "$peer_port" ]]; then
        cmd="$cmd --base-peer-port $peer_port"
    fi
    
    if $cmd; then
        print_success "Configuration generated: $compose_file"
        return 0
    else
        print_error "Failed to generate configuration"
        return 1
    fi
}

# Start cluster
start_cluster() {
    local nodes=$1
    local compose_file=$2
    local base_port=$3
    local peer_port=$4
    
    # Generate configuration if it doesn't exist or nodes changed
    if [[ ! -f "$compose_file" ]] || ! generate_cluster "$nodes" "$compose_file" "$base_port" "$peer_port"; then
        return 1
    fi
    
    print_info "Starting $nodes-node etcd cluster..."
    
    if docker-compose -f "$compose_file" up -d; then
        print_success "Cluster started successfully"
        
        # Wait for cluster to be ready
        print_info "Waiting for cluster to be ready..."
        sleep 5
        
        # Show cluster status
        show_status "$compose_file"
        return 0
    else
        print_error "Failed to start cluster"
        return 1
    fi
}

# Stop cluster
stop_cluster() {
    local compose_file=$1
    
    if [[ ! -f "$compose_file" ]]; then
        print_warning "No compose file found: $compose_file"
        return 0
    fi
    
    print_info "Stopping etcd cluster..."
    
    if docker-compose -f "$compose_file" down; then
        print_success "Cluster stopped successfully"
        return 0
    else
        print_error "Failed to stop cluster"
        return 1
    fi
}

# Clean cluster (stop and remove volumes)
clean_cluster() {
    local compose_file=$1
    
    if [[ ! -f "$compose_file" ]]; then
        print_warning "No compose file found: $compose_file"
        return 0
    fi
    
    print_warning "This will stop the cluster and remove all data. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled"
        return 0
    fi
    
    print_info "Stopping cluster and removing data..."
    
    if docker-compose -f "$compose_file" down -v; then
        print_success "Cluster cleaned successfully"
        return 0
    else
        print_error "Failed to clean cluster"
        return 1
    fi
}

# Show cluster status
show_status() {
    local compose_file=$1
    
    if [[ ! -f "$compose_file" ]]; then
        print_warning "No compose file found: $compose_file"
        return 1
    fi
    
    print_info "Cluster Status:"
    echo
    
    # Show running containers
    docker-compose -f "$compose_file" ps
    echo
    
    # Try to get cluster health from first node
    if docker-compose -f "$compose_file" exec -T etcd-1 etcdctl endpoint health 2>/dev/null; then
        echo
        print_info "Cluster Members:"
        docker-compose -f "$compose_file" exec -T etcd-1 etcdctl member list 2>/dev/null || true
    else
        print_warning "Could not connect to cluster or cluster is not ready"
    fi
}

# Test cluster connectivity
test_cluster() {
    local compose_file=$1
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "No compose file found: $compose_file"
        return 1
    fi
    
    print_info "Testing cluster connectivity..."
    
    # Test basic operations
    local test_key="test-$(date +%s)"
    local test_value="test-value-$(date +%s)"
    
    if docker-compose -f "$compose_file" exec -T etcd-1 etcdctl put "$test_key" "$test_value" >/dev/null 2>&1; then
        if result=$(docker-compose -f "$compose_file" exec -T etcd-1 etcdctl get "$test_key" --print-value-only 2>/dev/null); then
            if [[ "$result" == "$test_value" ]]; then
                print_success "Cluster connectivity test passed"
                
                # Clean up test key
                docker-compose -f "$compose_file" exec -T etcd-1 etcdctl del "$test_key" >/dev/null 2>&1
                return 0
            fi
        fi
    fi
    
    print_error "Cluster connectivity test failed"
    return 1
}

# Run benchmark
run_benchmark() {
    local compose_file=$1
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "No compose file found: $compose_file"
        return 1
    fi
    
    print_info "Running etcd benchmark..."
    print_info "This may take a few minutes..."
    
    # Run benchmark inside container
    docker-compose -f "$compose_file" exec etcd-1 sh -c "
        echo 'Write benchmark (1000 sequential writes):'
        etcdctl check perf --load s --prefix /benchmark/write/
        echo
        echo 'Read benchmark (1000 sequential reads):'
        etcdctl check perf --load r --prefix /benchmark/read/
    "
}

# Show logs
show_logs() {
    local compose_file=$1
    local node=$2
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "No compose file found: $compose_file"
        return 1
    fi
    
    if [[ -n "$node" ]]; then
        print_info "Showing logs for $node..."
        docker-compose -f "$compose_file" logs -f "$node"
    else
        print_info "Showing logs for all nodes..."
        docker-compose -f "$compose_file" logs -f
    fi
}

# Open shell in container
open_shell() {
    local compose_file=$1
    local node=$2
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "No compose file found: $compose_file"
        return 1
    fi
    
    if [[ -z "$node" ]]; then
        print_error "Node name required for shell command"
        return 1
    fi
    
    print_info "Opening shell in $node..."
    docker-compose -f "$compose_file" exec "$node" sh
}

# Parse command line arguments
parse_args() {
    local compose_file="$DEFAULT_COMPOSE_FILE"
    local base_port=""
    local peer_port=""
    local command=""
    local nodes=""
    local node=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                compose_file="$2"
                shift 2
                ;;
            -p|--port)
                base_port="$2"
                shift 2
                ;;
            --peer-port)
                peer_port="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            generate|start|stop|restart|status|clean|test|benchmark|logs|shell)
                command="$1"
                shift
                ;;
            [0-9]*)
                nodes="$1"
                shift
                ;;
            etcd-*)
                node="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Execute command
    case "$command" in
        generate)
            if [[ -z "$nodes" ]]; then
                print_error "Number of nodes required for generate command"
                exit 1
            fi
            generate_cluster "$nodes" "$compose_file" "$base_port" "$peer_port"
            ;;
        start)
            if [[ -z "$nodes" ]]; then
                print_error "Number of nodes required for start command"
                exit 1
            fi
            start_cluster "$nodes" "$compose_file" "$base_port" "$peer_port"
            ;;
        stop)
            stop_cluster "$compose_file"
            ;;
        restart)
            if [[ -z "$nodes" ]]; then
                print_error "Number of nodes required for restart command"
                exit 1
            fi
            stop_cluster "$compose_file"
            start_cluster "$nodes" "$compose_file" "$base_port" "$peer_port"
            ;;
        status)
            show_status "$compose_file"
            ;;
        clean)
            clean_cluster "$compose_file"
            ;;
        test)
            test_cluster "$compose_file"
            ;;
        benchmark)
            run_benchmark "$compose_file"
            ;;
        logs)
            show_logs "$compose_file" "$node"
            ;;
        shell)
            open_shell "$compose_file" "$node"
            ;;
        "")
            print_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command -v docker >/dev/null 2>&1; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps+=("python3")
    fi
    
    if ! python3 -c "import yaml" >/dev/null 2>&1; then
        missing_deps+=("python3-yaml")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
}

# Main function
main() {
    check_dependencies
    
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    parse_args "$@"
}

# Run main function
main "$@"
