# etcd Cluster Deployment and Benchmarking

A comprehensive Docker-based solution for deploying and benchmarking etcd clusters of various sizes. This project provides tools to easily create, manage, and performance test etcd clusters while avoiding port and volume collisions.

## Features

- **Dynamic Cluster Generation**: Create clusters of any size (1-N nodes)
- **Port Collision Avoidance**: Automatic port assignment prevents conflicts
- **Volume Management**: Isolated data volumes for each node
- **Easy Cluster Management**: Simple commands to start, stop, and manage clusters
- **Comprehensive Benchmarking**: Performance testing across different cluster sizes
- **Health Monitoring**: Cluster status and health checking
- **Flexible Configuration**: Support for custom ports and configurations

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3 with PyYAML (`pip install pyyaml`)
- Bash shell

### Basic Usage

1. **Start a 3-node cluster:**

   ```bash
   ./cluster-manager.sh start 3
   ```

2. **Check cluster status:**

   ```bash
   ./cluster-manager.sh status
   ```

3. **Run performance benchmark:**

   ```bash
   ./cluster-manager.sh benchmark
   ```

4. **Stop and clean up:**
   ```bash
   ./cluster-manager.sh clean
   ```

## Project Structure

```
etcd-deployment/
├── docker-compose.yml              # Static 5-node configuration (with profiles)
├── generate-cluster.py             # Dynamic cluster generator
├── cluster-manager.sh              # Main management script
├── benchmark.py                    # Performance benchmarking tool
├── README.md                       # This documentation
├── examples/                       # Example configurations and scripts
└── docs/                          # Additional documentation
```

## Cluster Management

### Using the Cluster Manager

The `cluster-manager.sh` script provides a unified interface for all cluster operations:

```bash
# Generate cluster configuration
./cluster-manager.sh generate 5

# Start cluster with specific number of nodes
./cluster-manager.sh start 3
./cluster-manager.sh start 5 -p 3379  # Custom port base

# Check cluster status and health
./cluster-manager.sh status

# Test cluster connectivity
./cluster-manager.sh test

# View logs
./cluster-manager.sh logs           # All nodes
./cluster-manager.sh logs etcd-1    # Specific node

# Open shell in container
./cluster-manager.sh shell etcd-1

# Stop cluster
./cluster-manager.sh stop

# Restart with different size
./cluster-manager.sh restart 7

# Clean up (removes all data)
./cluster-manager.sh clean
```

### Port Allocation

Ports are automatically assigned to avoid collisions:

- **Client ports**: Start at 2379, increment by 2 for each node
- **Peer ports**: Start at 2380, increment by 2 for each node

| Node   | Client Port | Peer Port |
| ------ | ----------- | --------- |
| etcd-1 | 2379        | 2380      |
| etcd-2 | 2381        | 2382      |
| etcd-3 | 2383        | 2384      |
| etcd-4 | 2385        | 2386      |
| etcd-5 | 2387        | 2388      |

### Custom Port Configuration

```bash
# Start cluster with custom base ports
./cluster-manager.sh start 3 -p 3379 --peer-port 3380
```

## Dynamic Cluster Generation

### Using the Python Generator

```bash
# Generate 3-node cluster
python3 generate-cluster.py 3

# Generate 7-node cluster with custom output file
python3 generate-cluster.py 7 -o cluster-7.yml

# Generate with custom ports
python3 generate-cluster.py 5 --base-client-port 3379 --base-peer-port 3380
```

### Generated Configuration Features

- Automatic service definitions for each node
- Unique volume assignments
- Proper cluster member discovery
- Network isolation
- Restart policies

## Benchmarking

### Running Benchmarks

The benchmarking tool provides comprehensive performance testing:

```bash
# Full benchmark suite
python3 benchmark.py

# Quick benchmark (reduced test sizes)
python3 benchmark.py --quick

# Benchmark specific cluster
python3 benchmark.py -f cluster-5.yml

# Save results to specific file
python3 benchmark.py -o my-results.json
```

### Benchmark Tests

1. **Sequential Writes**: Measures write throughput and latency
2. **Sequential Reads**: Measures read performance
3. **Concurrent Writes**: Tests performance under concurrent load
4. **Mixed Workload**: Simulates real-world read/write patterns

### Sample Benchmark Output

```
BENCHMARK RESULTS SUMMARY
============================================================
Timestamp: 2024-01-15T10:30:45.123456
Compose file: docker-compose-generated.yml
Quick mode: False

Sequential Writes:
  Operations: 1000/1000
  Throughput: 245.67 ops/sec
  Avg Latency: 4.07 ms

Sequential Reads:
  Operations: 1000/1000
  Throughput: 1234.56 ops/sec
  Avg Latency: 0.81 ms

Concurrent Writes:
  Operations: 1000/1000
  Concurrency: 10 threads
  Throughput: 189.23 ops/sec
  Avg Latency: 5.29 ms

Mixed Workload:
  Duration: 60.0 seconds
  Total Ops: 15432
  Read Ops: 10802 (70.0%)
  Write Ops: 4630
  Total Throughput: 257.20 ops/sec
```

## Performance Comparison

### Comparing Different Cluster Sizes

```bash
# Benchmark different cluster sizes
for nodes in 1 3 5 7; do
    echo "Benchmarking $nodes-node cluster..."
    ./cluster-manager.sh start $nodes
    python3 benchmark.py --quick -o "results-${nodes}nodes.json"
    ./cluster-manager.sh stop
done
```

### Visualizing Results

After collecting benchmark results, use the plotting script to visualize performance across cluster sizes:

```bash
# Install plotting dependencies
source venv/bin/activate && pip install matplotlib numpy

# Generate plots from all result files
python3 plot_results.py

# View only the summary table
python3 plot_results.py --table-only

# Custom output file and show interactive plot
python3 plot_results.py -o my_benchmark.png --show

# Use custom file pattern
python3 plot_results.py --pattern "benchmark_*.json"
```

The plotting script generates:

- **Throughput comparison** across cluster sizes
- **Latency analysis** for different operations
- **Read vs Write performance** breakdown
- **Efficiency metrics** (operations per node)
- **Performance insights** and scaling analysis

Example output:

```
ETCD CLUSTER PERFORMANCE SUMMARY
Nodes  Seq Write    Seq Read     Conc Write   Mixed Total  Write Lat.   Read Lat.
       (ops/s)      (ops/s)      (ops/s)      (ops/s)      (ms)         (ms)
----------------------------------------------------------------------------------------------------
1      23.7         25.7         78.5         14.1         42.2         38.8
3      22.8         24.5         75.2         13.2         44.0         40.9
5      22.0         23.9         76.3         12.3         45.4         41.8
7      21.3         22.8         71.6         11.6         46.9         43.9
----------------------------------------------------------------------------------------------------

PERFORMANCE INSIGHTS:
--------------------------------------------------
Sequential Write Scaling (1 → 7 nodes): 0.90x
Concurrent Write Scaling (1 → 7 nodes): 0.91x
Sequential Write Latency Change: +4.7ms
Efficiency (Concurrent Writes per Node): 1n=78.5 ops/s/node, 7n=10.2 ops/s/node

Plot saved to: benchmark_results.png
```

### Expected Performance Characteristics

- **Single Node**: Highest throughput, no consensus overhead
- **3 Nodes**: Good balance of performance and fault tolerance
- **5 Nodes**: Lower throughput but higher fault tolerance
- **7+ Nodes**: Significant performance impact due to consensus overhead

## Docker Compose Profiles

The static `docker-compose.yml` uses profiles for different cluster sizes:

```bash
# Single node
docker-compose up etcd-1

# 3-node cluster
docker-compose --profile multi-node up

# 5-node cluster
docker-compose --profile large-cluster up
```

## Configuration Options

### Environment Variables

Each etcd node supports standard etcd environment variables:

- `ETCD_NAME`: Node name
- `ETCD_DATA_DIR`: Data directory path
- `ETCD_LISTEN_CLIENT_URLS`: Client listening URLs
- `ETCD_ADVERTISE_CLIENT_URLS`: Client advertise URLs
- `ETCD_LISTEN_PEER_URLS`: Peer listening URLs
- `ETCD_INITIAL_ADVERTISE_PEER_URLS`: Peer advertise URLs
- `ETCD_INITIAL_CLUSTER`: Initial cluster configuration
- `ETCD_INITIAL_CLUSTER_TOKEN`: Cluster token
- `ETCD_INITIAL_CLUSTER_STATE`: Cluster state (new/existing)

### Volume Management

Each node gets its own named volume:

- `etcd-1-data`
- `etcd-2-data`
- `etcd-3-data`
- etc.

Data persists between container restarts but can be removed with the `clean` command.

## Troubleshooting

### Common Issues

1. **Port Already in Use**

   ```bash
   # Use custom ports
   ./cluster-manager.sh start 3 -p 3379
   ```

2. **Cluster Won't Start**

   ```bash
   # Check logs
   ./cluster-manager.sh logs

   # Clean and restart
   ./cluster-manager.sh clean
   ./cluster-manager.sh start 3
   ```

3. **Performance Issues**

   ```bash
   # Check cluster health
   ./cluster-manager.sh status

   # Monitor resource usage
   docker stats
   ```

### Health Checks

```bash
# Manual health check
docker exec etcd-1 etcdctl endpoint health

# Check cluster members
docker exec etcd-1 etcdctl member list

# Test basic operations
docker exec etcd-1 etcdctl put test-key test-value
docker exec etcd-1 etcdctl get test-key
```

## Advanced Usage

### Custom Network Configuration

Modify the network settings in the generated compose files:

```yaml
networks:
  etcd-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### TLS Configuration

For production deployments, consider adding TLS:

```yaml
environment:
  - ETCD_CERT_FILE=/path/to/server.crt
  - ETCD_KEY_FILE=/path/to/server.key
  - ETCD_TRUSTED_CA_FILE=/path/to/ca.crt
  - ETCD_CLIENT_CERT_AUTH=true
```

### Resource Limits

Add resource constraints:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "0.5"
    reservations:
      memory: 256M
      cpus: "0.25"
```

## Best Practices

### Cluster Sizing

- **Development**: 1 node for simplicity
- **Testing**: 3 nodes for basic fault tolerance
- **Production**: 3 or 5 nodes (odd numbers recommended)
- **High Availability**: 5 or 7 nodes maximum

### Performance Optimization

1. Use SSD storage for better performance
2. Ensure adequate memory (2GB+ recommended)
3. Monitor disk I/O and network latency
4. Tune etcd parameters for your workload
5. Use dedicated hosts for production

### Monitoring

- Monitor cluster health regularly
- Track performance metrics
- Set up alerting for failures
- Monitor resource usage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## References

- [etcd Official Documentation](https://etcd.io/docs/)
- [etcd Clustering Guide](https://etcd.io/docs/v3.6/op-guide/clustering/)
- [etcd Performance](https://etcd.io/docs/v3.6/op-guide/performance/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
