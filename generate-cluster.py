#!/usr/bin/env python3
"""
Dynamic etcd cluster generator for Docker Compose
Generates configurations for clusters of any size while avoiding port collisions
"""

import argparse
import yaml
import sys
from pathlib import Path

def generate_etcd_service(node_id, total_nodes, base_client_port=2379, base_peer_port=2380):
    """Generate a single etcd service configuration"""
    client_port = base_client_port + (node_id - 1) * 2
    peer_port = base_peer_port + (node_id - 1) * 2
    
    # Build initial cluster string
    cluster_members = []
    for i in range(1, total_nodes + 1):
        cluster_members.append(f"etcd-{i}=http://etcd-{i}:2380")
    initial_cluster = ",".join(cluster_members)
    
    service = {
        "image": "gcr.io/etcd-development/etcd:v3.6.4",
        "container_name": f"etcd-{node_id}",
        "hostname": f"etcd-{node_id}",
        "ports": [
            f"{client_port}:2379",
            f"{peer_port}:2380"
        ],
        "volumes": [
            f"etcd-{node_id}-data:/etcd-data"
        ],
        "environment": [
            f"ETCD_NAME=etcd-{node_id}",
            "ETCD_DATA_DIR=/etcd-data",
            "ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379",
            f"ETCD_ADVERTISE_CLIENT_URLS=http://etcd-{node_id}:2379",
            "ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380",
            f"ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd-{node_id}:2380",
            f"ETCD_INITIAL_CLUSTER={initial_cluster}",
            "ETCD_INITIAL_CLUSTER_TOKEN=etcd-cluster-1",
            "ETCD_INITIAL_CLUSTER_STATE=new",
            "ETCD_LOG_LEVEL=info",
            "ETCD_LOGGER=zap",
            "ETCD_LOG_OUTPUTS=stderr"
        ],
        "networks": ["etcd-network"],
        "restart": "unless-stopped"
    }
    
    return service

def generate_compose_config(num_nodes):
    """Generate complete Docker Compose configuration"""
    if num_nodes < 1:
        raise ValueError("Number of nodes must be at least 1")
    
    if num_nodes > 1 and num_nodes % 2 == 0:
        print(f"Warning: Even number of nodes ({num_nodes}) is not recommended for etcd clusters.")
        print("Consider using an odd number for better fault tolerance.")
    
    compose = {
        "version": "3.8",
        "services": {},
        "volumes": {},
        "networks": {
            "etcd-network": {
                "driver": "bridge"
            }
        }
    }
    
    # Generate services and volumes
    for i in range(1, num_nodes + 1):
        service_name = f"etcd-{i}"
        compose["services"][service_name] = generate_etcd_service(i, num_nodes)
        compose["volumes"][f"etcd-{i}-data"] = None
    
    return compose

def main():
    parser = argparse.ArgumentParser(
        description="Generate Docker Compose configuration for etcd cluster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate-cluster.py 3                    # Generate 3-node cluster
  python3 generate-cluster.py 5 -o cluster-5.yml  # Generate 5-node cluster, save to file
  python3 generate-cluster.py 1                    # Generate single-node cluster
        """
    )
    
    parser.add_argument(
        "nodes",
        type=int,
        help="Number of etcd nodes in the cluster"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="docker-compose-generated.yml",
        help="Output file name (default: docker-compose-generated.yml)"
    )
    
    parser.add_argument(
        "--base-client-port",
        type=int,
        default=2379,
        help="Base port for client connections (default: 2379)"
    )
    
    parser.add_argument(
        "--base-peer-port",
        type=int,
        default=2380,
        help="Base port for peer connections (default: 2380)"
    )
    
    args = parser.parse_args()
    
    try:
        # Generate configuration
        config = generate_compose_config(args.nodes)
        
        # Write to file
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"Generated {args.nodes}-node etcd cluster configuration: {output_path}")
        print(f"Client ports: {args.base_client_port}-{args.base_client_port + (args.nodes - 1) * 2}")
        print(f"Peer ports: {args.base_peer_port}-{args.base_peer_port + (args.nodes - 1) * 2}")
        print(f"\nTo start the cluster:")
        print(f"  docker-compose -f {output_path} up -d")
        print(f"\nTo test the cluster:")
        print(f"  docker exec etcd-1 etcdctl --endpoints=localhost:2379 put test-key test-value")
        print(f"  docker exec etcd-1 etcdctl --endpoints=localhost:2379 get test-key")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
