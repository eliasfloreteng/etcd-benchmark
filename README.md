# ETCD Cluster Runner

A simple bash script to run a variable number of etcd nodes using Docker containers.

## Prerequisites

- Docker must be installed and running
- Bash shell
- Internet connection (to pull etcd Docker image if not already available)

## Usage

### Starting a Cluster

```bash
./run-etcd-cluster.sh <number_of_nodes>
```

Examples:

```bash
# Start a single-node cluster
./run-etcd-cluster.sh 1

# Start a 3-node cluster (recommended for production)
./run-etcd-cluster.sh 3

# Start a 5-node cluster
./run-etcd-cluster.sh 5
```

### Cleaning Up

```bash
./run-etcd-cluster.sh cleanup
```

This will stop and remove all etcd containers, remove the Docker network, and clean up data directories.

## Features

- **Dynamic Node Count**: Supports 1-10 etcd nodes
- **Automatic Port Assignment**: Each node gets unique client and peer ports
  - Node 1: Client port 2379, Peer port 2390
  - Node 2: Client port 2380, Peer port 2391
  - Node N: Client port (2378+N), Peer port (2389+N)
- **Docker Network**: Creates isolated network for cluster communication
- **Health Monitoring**: Waits for cluster to be ready and shows status
- **Data Persistence**: Uses bind mounts to `/tmp/etcd-data-N` directories
- **Easy Cleanup**: Single command to remove entire cluster

## Script Details

- **ETCD Version**: v3.6.4
- **Docker Image**: `gcr.io/etcd-development/etcd:v3.6.4`
- **Network Name**: `etcd-network`
- **Cluster Token**: `etcd-cluster-token`

## Testing the Cluster

After starting a cluster, you can test it with these commands:

```bash
# Put a key-value pair
docker exec etcd-node-1 /usr/local/bin/etcdctl put foo bar

# Get the value
docker exec etcd-node-1 /usr/local/bin/etcdctl get foo

# Check cluster health
docker exec etcd-node-1 /usr/local/bin/etcdctl endpoint health --cluster

# List cluster members
docker exec etcd-node-1 /usr/local/bin/etcdctl member list
```

## Port Mapping

The script automatically assigns ports to avoid conflicts:

| Node | Container Name | Client Port | Peer Port |
| ---- | -------------- | ----------- | --------- |
| 1    | etcd-node-1    | 2379        | 2390      |
| 2    | etcd-node-2    | 2380        | 2391      |
| 3    | etcd-node-3    | 2381        | 2392      |
| N    | etcd-node-N    | 2378+N      | 2389+N    |

## Connecting from Host

You can connect to any node from the host machine using the mapped client ports:

```bash
# Connect to node 1
etcdctl --endpoints=http://localhost:2379 put key1 value1

# Connect to node 2
etcdctl --endpoints=http://localhost:2380 put key2 value2

# Connect to multiple nodes
etcdctl --endpoints=http://localhost:2379,http://localhost:2380,http://localhost:2381 endpoint health
```

## Troubleshooting

### Common Issues

1. **Docker not running**: Make sure Docker Desktop is running
2. **Port conflicts**: The script uses ports 2379+ - ensure they're available
3. **Network issues**: Run `./run-etcd-cluster.sh cleanup` if containers fail to start

### Logs

To view logs for a specific node:

```bash
docker logs etcd-node-1
```

To follow logs in real-time:

```bash
docker logs -f etcd-node-1
```

### Manual Cleanup

If the automatic cleanup fails:

```bash
# Stop all etcd containers
docker stop $(docker ps -q --filter "name=etcd-node")

# Remove all etcd containers
docker rm $(docker ps -aq --filter "name=etcd-node")

# Remove network
docker network rm etcd-network

# Clean data directories
rm -rf /tmp/etcd-data-*
```

## Benchmarking the Cluster

### Python Benchmark Script

The repository includes a comprehensive Python benchmark tool:

```bash
# Install Python dependencies first
pip3 install -r requirements.txt

# Run benchmark with auto-detection of cluster nodes
python3 benchmark-etcd-cluster.py

# Run with specific parameters
python3 benchmark-etcd-cluster.py --clients 20 --duration 60 --write-ratio 0.5

# Save results to JSON file
python3 benchmark-etcd-cluster.py --output benchmark-results.json
```

#### Benchmark Features

- **Auto-detection**: Automatically discovers running etcd nodes
- **Multiple Clients**: Concurrent client simulation (configurable)
- **Mixed Workloads**: Configurable read/write ratios
- **Comprehensive Metrics**: Throughput, latency percentiles, error rates
- **Load Distribution**: Shows how requests are distributed across nodes
- **JSON Export**: Save detailed results for analysis

#### Benchmark Options

```bash
# Basic options
--clients, -c          Number of concurrent clients (default: 10)
--duration, -d         Benchmark duration in seconds (default: 30)
--write-ratio, -w      Ratio of write operations 0.0-1.0 (default: 0.3)

# Data size options
--key-size             Key size in bytes (default: 64)
--value-size           Value size in bytes (default: 1024)
--key-prefix           Key prefix for benchmark (default: benchmark)

# Connection options
--endpoints, -e        Specific etcd endpoints (auto-detected if not provided)
--warmup-time          Warmup time in seconds (default: 5)

# Output options
--output, -o           Save results to JSON file
```

#### Example Usage

```bash
# Quick benchmark with default settings
./benchmark-etcd-cluster.py

# Heavy write load test
./benchmark-etcd-cluster.py --clients 50 --write-ratio 0.8 --duration 120

# Large value benchmark
./benchmark-etcd-cluster.py --value-size 4096 --clients 5 --duration 60

# Specific endpoints
./benchmark-etcd-cluster.py --endpoints http://localhost:2379 http://localhost:2380 http://localhost:2381
```

### Prerequisites for Benchmarking

- Python 3.7+
- `etcd3` Python library (`pip3 install -r requirements.txt`)
- Running etcd cluster (use `run-etcd-cluster.sh` to start)

## File Structure

```
.
├── run-etcd-cluster.sh      # Cluster deployment script
├── benchmark-etcd-cluster.py # Python benchmark tool
├── requirements.txt         # Python dependencies
└── README.md               # This documentation
```

## License

This script is provided as-is for educational and development purposes.
