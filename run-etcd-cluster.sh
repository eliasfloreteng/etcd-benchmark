#!/bin/bash

# Script to run a variable number of etcd nodes using Docker
# Usage: ./run-etcd-cluster.sh <number_of_nodes>

set -e

ETCD_VER=v3.6.4
ETCD_IMAGE="gcr.io/etcd-development/etcd:${ETCD_VER}"
CLUSTER_TOKEN="etcd-cluster-token"
NETWORK_NAME="etcd-network"

# Function to display usage
usage() {
    echo "Usage: $0 <number_of_nodes>"
    echo "Example: $0 3"
    echo "Creates a cluster with the specified number of etcd nodes"
    exit 1
}

# Function to cleanup existing cluster
cleanup() {
    echo "Cleaning up existing etcd cluster..."
    
    # Stop and remove containers
    for i in $(docker ps -aq --filter "name=etcd-node"); do
        docker stop $i 2>/dev/null || true
        docker rm $i 2>/dev/null || true
    done
    
    # Remove network if it exists
    docker network rm $NETWORK_NAME 2>/dev/null || true
    
    # Remove data directories
    rm -rf /tmp/etcd-data-* 2>/dev/null || true
    
    echo "Cleanup completed."
}

# Function to create Docker network
create_network() {
    echo "Creating Docker network: $NETWORK_NAME"
    docker network create $NETWORK_NAME 2>/dev/null || echo "Network already exists"
}

# Function to build initial cluster string
build_initial_cluster() {
    local num_nodes=$1
    local cluster_string=""
    
    for ((i=1; i<=num_nodes; i++)); do
        if [ $i -gt 1 ]; then
            cluster_string+=","
        fi
        cluster_string+="etcd-node-$i=http://etcd-node-$i:2380"
    done
    
    echo $cluster_string
}

# Function to start etcd nodes
start_etcd_nodes() {
    local num_nodes=$1
    local initial_cluster=$(build_initial_cluster $num_nodes)
    
    echo "Starting $num_nodes etcd nodes..."
    
    for ((i=1; i<=num_nodes; i++)); do
        local node_name="etcd-node-$i"
        local data_dir="/tmp/etcd-data-$i"
        local client_port=$((2378 + i))
        local peer_port=$((2389 + i))
        
        # Create data directory
        mkdir -p $data_dir
        
        echo "Starting $node_name on client port $client_port, peer port $peer_port"
        
        docker run -d \
            --name $node_name \
            --network $NETWORK_NAME \
            -p $client_port:2379 \
            -p $peer_port:2380 \
            --mount type=bind,source=$data_dir,destination=/etcd-data \
            $ETCD_IMAGE \
            /usr/local/bin/etcd \
            --name $node_name \
            --data-dir /etcd-data \
            --listen-client-urls http://0.0.0.0:2379 \
            --advertise-client-urls http://$node_name:2379 \
            --listen-peer-urls http://0.0.0.0:2380 \
            --initial-advertise-peer-urls http://$node_name:2380 \
            --initial-cluster $initial_cluster \
            --initial-cluster-token $CLUSTER_TOKEN \
            --initial-cluster-state new \
            --log-level info \
            --logger zap \
            --log-outputs stderr
        
        # Wait a moment between starting nodes
        sleep 2
    done
}

# Function to display cluster status
show_cluster_status() {
    local num_nodes=$1
    
    echo ""
    echo "=== ETCD Cluster Status ==="
    echo "Cluster Token: $CLUSTER_TOKEN"
    echo "Number of Nodes: $num_nodes"
    echo ""
    
    for ((i=1; i<=num_nodes; i++)); do
        local node_name="etcd-node-$i"
        local client_port=$((2378 + i))
        local peer_port=$((2389 + i))
        
        echo "Node: $node_name"
        echo "  Client URL: http://localhost:$client_port"
        echo "  Peer URL: http://localhost:$peer_port"
        echo "  Container: $node_name"
        echo ""
    done
    
    echo "To test the cluster, try:"
    echo "  docker exec etcd-node-1 /usr/local/bin/etcdctl put foo bar"
    echo "  docker exec etcd-node-1 /usr/local/bin/etcdctl get foo"
    echo ""
    echo "To check cluster health:"
    echo "  docker exec etcd-node-1 /usr/local/bin/etcdctl endpoint health --cluster"
    echo ""
    echo "To stop the cluster:"
    echo "  $0 cleanup"
}

# Function to wait for cluster to be ready
wait_for_cluster() {
    local num_nodes=$1
    echo "Waiting for cluster to be ready..."
    
    local ready_nodes=0
    local max_attempts=30
    local attempt=0
    
    while [ $ready_nodes -lt $num_nodes ] && [ $attempt -lt $max_attempts ]; do
        ready_nodes=0
        
        for ((i=1; i<=num_nodes; i++)); do
            local node_name="etcd-node-$i"
            if docker exec $node_name /usr/local/bin/etcdctl endpoint health --cluster >/dev/null 2>&1; then
                ready_nodes=$((ready_nodes + 1))
            fi
        done
        
        if [ $ready_nodes -lt $num_nodes ]; then
            echo "  $ready_nodes/$num_nodes nodes ready, waiting..."
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $ready_nodes -eq $num_nodes ]; then
        echo "✓ All $num_nodes nodes are ready!"
    else
        echo "⚠ Warning: Only $ready_nodes/$num_nodes nodes are ready after waiting"
    fi
}

# Main script logic
main() {
    # Check if cleanup is requested
    if [ "$1" = "cleanup" ]; then
        cleanup
        exit 0
    fi
    
    # Check arguments
    if [ $# -ne 1 ]; then
        usage
    fi
    
    # Validate number of nodes
    local num_nodes=$1
    if ! [[ "$num_nodes" =~ ^[0-9]+$ ]] || [ "$num_nodes" -lt 1 ] || [ "$num_nodes" -gt 10 ]; then
        echo "Error: Number of nodes must be a positive integer between 1 and 10"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker is not running or not accessible"
        exit 1
    fi
    
    echo "Setting up etcd cluster with $num_nodes nodes..."
    
    # Cleanup any existing cluster
    cleanup
    
    # Create network
    create_network
    
    # Start etcd nodes
    start_etcd_nodes $num_nodes
    
    # Wait for cluster to be ready
    wait_for_cluster $num_nodes
    
    # Show cluster status
    show_cluster_status $num_nodes
}

# Run main function with all arguments
main "$@"
